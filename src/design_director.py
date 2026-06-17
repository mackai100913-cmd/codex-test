"""表紙のデザイン責任者（画像の品質審査）。

Geminiのビジョン（画像理解）で、料理写真／表紙がロールモデルの要件と
合格ラインを満たすかを採点する。合格したものだけを通すことで品質を担保する。

- 画像生成は無料枠で不可だが、画像の「採点・講評」はテキスト系モデルで可能。
- APIが使えない場合は簡易ヒューリスティック（明るさ・縦横比など）で代替判定する。
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from . import config
from .recipe_generator import Recipe

# 審査の観点（ロールモデル＝暗背景の本格レシピ写真／"AIっぽさ"を最も嫌う）
RUBRIC = [
    ("realistic", "本物感（AIっぽくない）", "実際に撮影した本物の料理に見えるか。CG・作り物っぽさが無いか。", 30),
    ("appetizing", "シズル感・美味しそう", "照り・湯気・みずみずしさがあり食欲をそそるか。", 20),
    ("mood", "世界観（暗背景・高級感）", "暗い背景でドラマチック、ブランドの世界観に合うか。", 15),
    ("composition", "構図", "主役の料理が中央〜下部に大きく、縦長(9:16)に向くか。", 15),
    ("match", "要望との一致", "指定した料理そのものに見えるか。", 15),
    ("clean", "文字・ロゴ無し", "写真内に文字やロゴ・透かしが入っていないか(表紙文字は後で載せる)。", 5),
]


@dataclass
class ReviewResult:
    passed: bool
    total: int
    pass_score: int
    scores: dict = field(default_factory=dict)   # key -> {"score":int,"comment":str}
    summary: str = ""
    requests: list[str] = field(default_factory=list)   # 改善要望
    regenerate_prompt: str = ""                          # 作り直し用プロンプト案
    engine: str = ""                                     # gemini / heuristic

    def report(self, title: str = "") -> str:
        mark = "✅ 合格" if self.passed else "❌ 不合格"
        lines = [
            "==============================",
            f"  表紙デザイン審査 {(': ' + title) if title else ''}",
            "==============================",
            f"判定: {mark}   総合: {self.total}/100 （合格ライン {self.pass_score}）",
            f"審査エンジン: {self.engine}",
            "",
            "【項目別】",
        ]
        for key, label, _desc, weight in RUBRIC:
            s = self.scores.get(key, {})
            lines.append(f"  ・{label}: {s.get('score', '-')}/{weight}  {s.get('comment', '')}")
        lines += ["", "【講評】", self.summary or "-"]
        if self.requests:
            lines += ["", "【改善要望】"] + [f"  - {r}" for r in self.requests]
        if not self.passed and self.regenerate_prompt:
            lines += ["", "【作り直し用プロンプト案（Geminiアプリに貼る）】", self.regenerate_prompt]
        return "\n".join(lines)


def _pass_score() -> int:
    q = config.persona().get("quality", {})
    return int(q.get("pass_score", 70))


def review_model() -> str:
    return config.env("GEMINI_REVIEW_MODEL", "gemini-flash-latest")


def _review_models() -> list[str]:
    """審査に使うモデル候補（先頭から試し、503等なら次へ）。"""
    primary = review_model()
    fallbacks = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest"]
    out = [primary] + [m for m in fallbacks if m != primary]
    return out


def _generate_with_retry(client, models: list[str], contents, attempts: int = 3):
    """503/UNAVAILABLE等は短い指数バックオフで再試行し、ダメなら次モデルへ。"""
    import time

    last = None
    for model in models:
        for i in range(attempts):
            try:
                return client.models.generate_content(model=model, contents=contents), model
            except Exception as e:  # noqa: BLE001
                last = e
                msg = str(e)
                if any(x in msg for x in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                    time.sleep(1.5 * (2 ** i))
                    continue
                break  # それ以外のエラーは次モデルへ
    if last:
        raise last
    raise RuntimeError("no model available")


# ---------------------------------------------------------------------------
# Gemini ビジョンによる審査
# ---------------------------------------------------------------------------

def _gemini_review(image_path: Path, recipe: Recipe,
                   kind: str = "hero", aspect: str = "9:16") -> ReviewResult | None:
    api_key = config.gemini_api_key()
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None

    dish = f"{recipe.title_top}{recipe.title_main}"
    if kind == "step":
        subject = (f"これは料理「{recipe.title_main}」の【調理工程】を写した写真のはずです。"
                   "完成品ではなく、鍋・フライパン・まな板など調理中の様子が、"
                   "ヒーロー写真と同じ世界観・色味で撮れているかを見てください。")
        comp = f"主役(調理中の中身)が画面の中央に大きく写り、正方形({aspect})に向く構図か。"
    else:
        subject = f"これは完成した料理「{dish}」の【表紙メイン写真】のはずです。"
        comp = f"主役の料理が画面の中央に大きく写り、縦長({aspect})に向く構図か。"
    rubric_txt = "\n".join(
        f'- {k}（{label}・{w}点満点）: {(comp if k == "composition" else desc)}'
        for k, label, desc, w in RUBRIC
    )
    prompt = f"""あなたは人気グルメ系レシピTikTokの「デザイン責任者」です。
提供された料理写真が、投稿素材として合格ラインかを厳しく審査してください。
{subject}
ロールモデルは暗背景の本格的な料理写真で、最も重視するのは「AIっぽくない本物感」、
次に「シズル感（美味しそう）」と「世界観・構図の統一」です。妥協せず辛口に採点すること。

# 採点項目（各満点）
{rubric_txt}

# 出力（必ずJSONのみ。前後に文章やマークダウン記号を付けない）
{{
  "scores": {{ "realistic": {{"score": 0, "comment": "..."}}, "appetizing": {{"score":0,"comment":"..."}}, "mood": {{"score":0,"comment":"..."}}, "composition": {{"score":0,"comment":"..."}}, "match": {{"score":0,"comment":"..."}}, "clean": {{"score":0,"comment":"..."}} }},
  "summary": "総評(80文字程度)",
  "requests": ["改善要望を具体的に2〜4個"],
  "regenerate_prompt": "もっと良くするためにGeminiアプリへ貼る画像生成プロンプト(日本語)"
}}
"""
    try:
        data = image_path.read_bytes()
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        client = genai.Client(api_key=api_key)
        r, used_model = _generate_with_retry(
            client, _review_models(),
            [types.Part.from_bytes(data=data, mime_type=mime), prompt],
        )
        text = (r.text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{"): text.rfind("}") + 1]
        d = json.loads(text)
        scores = d.get("scores", {})
        total = sum(int(scores.get(k, {}).get("score", 0)) for k, *_ in RUBRIC)
        ps = _pass_score()
        return ReviewResult(
            passed=total >= ps,
            total=total,
            pass_score=ps,
            scores=scores,
            summary=d.get("summary", ""),
            requests=d.get("requests", []),
            regenerate_prompt=d.get("regenerate_prompt", ""),
            engine=f"Gemini Vision ({used_model})",
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# フォールバック（簡易ヒューリスティック）
# ---------------------------------------------------------------------------

def _heuristic_review(image_path: Path, recipe: Recipe,
                      kind: str = "hero", aspect: str = "9:16") -> ReviewResult:
    ps = _pass_score()
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception:
        return ReviewResult(False, 0, ps, summary="画像を開けませんでした。", engine="heuristic")

    w, h = img.size
    small = img.resize((64, 64))
    px = list(small.getdata())
    brightness = sum(sum(p) for p in px) / (len(px) * 3)
    # 縦長(表紙)か / 正方形(工程)か。種類に応じて期待アスペクトを判定。
    if kind == "step":
        vertical = 0.8 <= (w / h) <= 1.25   # ほぼ正方形ならOK扱い
    else:
        vertical = h >= w
    # 真っ黒/真っ白でないか（被写体がありそうか）
    has_content = 20 < brightness < 220
    # 暗めの世界観か
    dark_mood = brightness < 130
    # サイズが十分か
    enough_res = min(w, h) >= 600

    scores = {
        "realistic": {"score": 18 if has_content else 5, "comment": "自動目視は不可。内容のみ確認。"},
        "appetizing": {"score": 12 if has_content else 4, "comment": "色味あり" if has_content else "情報量少"},
        "mood": {"score": 13 if dark_mood else 7, "comment": "暗め" if dark_mood else "明るめ(世界観要確認)"},
        "composition": {"score": 12 if vertical else 6, "comment": "縦長OK" if vertical else "縦長推奨"},
        "match": {"score": 8, "comment": "要望一致は目視不可(API推奨)"},
        "clean": {"score": 4, "comment": "文字有無は目視不可"},
    }
    if not enough_res:
        scores["composition"]["score"] = 4
        scores["composition"]["comment"] = f"解像度低 {w}x{h}"
    total = sum(s["score"] for s in scores.values())
    return ReviewResult(
        passed=total >= ps,
        total=total,
        pass_score=ps,
        scores=scores,
        summary="簡易判定（明るさ・縦横比・解像度）。本格審査はGemini APIキー設定時に有効。",
        requests=([] if has_content else ["被写体がはっきり写った写真にしてください。"])
                 + ([] if vertical else [f"指定のアスペクト比({aspect})に合う写真にしてください。"])
                 + ([] if dark_mood else ["背景を暗くして高級感を出すと世界観に合います。"]),
        engine="heuristic（APIなし簡易判定）",
    )


def review_image(image_path: Path, recipe: Recipe,
                 kind: str = "hero", aspect: str = "9:16") -> ReviewResult:
    """料理写真を審査して合否・点数・講評を返す。Gemini → 失敗時ヒューリスティック。

    kind: "hero"(表紙メイン写真) / "step"(調理工程写真)
    aspect: 期待するアスペクト比（"9:16" / "1:1"）
    """
    if not image_path.exists():
        return ReviewResult(False, 0, _pass_score(),
                            summary=f"画像が見つかりません: {image_path}", engine="-")
    return (_gemini_review(image_path, recipe, kind, aspect)
            or _heuristic_review(image_path, recipe, kind, aspect))
