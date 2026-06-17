"""デザイン品質の審査（経営体制つき）。

経営体制:
  会長(ユーザー) ─ 社長(このシステム) ─ 各責任者(専門家)
  - 会長はビジョンの所有者。会長と直接話すのは社長だけ。
  - 社長は会長のビジョンを「デザインの目的(DESIGN_PURPOSE)」へ翻訳し、
    各責任者へ意図(intent)を伝え、品質結果に責任を持つ。
  - 各責任者は担当領域を【100点満点】で審査する。構図は独立責任者。
    📷撮影 / 🍳フードスタイリスト / 🎨アート / 📐構図 / 🔍校閲

Geminiのビジョン（画像理解）で1回の解析を行い、各責任者のスコアを得る。
全責任者が合格ラインを満たした画像だけを通すことで品質を担保する。
APIが使えない場合は簡易ヒューリスティック（明るさ・縦横比など）で代替判定する。
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from . import config
from .recipe_generator import Recipe

# =============================================================================
# 経営体制
#   会長（ユーザー）   … 最終ビジョンの所有者。会長と直接話すのは社長だけ。
#   社長（このシステム）… 会長のビジョンを「デザインの目的」に翻訳し、各責任者へ
#                         意図(intent)を伝え、品質の結果に責任を持つ統括役。
#   各責任者           … 担当領域の専門家。社長の意図に沿って自領域を100点満点で評価。
# =============================================================================

# 社長が掲げるデザインの目的（会長のビジョンを社長が翻訳したもの）
DESIGN_PURPOSE = (
    "暗背景で高級感のある“本物の家庭料理写真”でグルメTikTokの素材を作る。"
    "スクロールの手を止めさせ「美味しそう・作りたい」と思わせるのが目的。"
    "完成料理は必ず黒マットの和皿に盛り付け（フライパン提供はNG）、料理を皿いっぱい照り良く、"
    "画面中央〜やや下に大きく。暗い木目＋黒背景＋暖色スポット光で全投稿を統一。"
    "AIっぽさ・文字・ロゴ・透かし(キラ✦含む)を徹底排除する。"
)

# デザイン品質フローの工程ごとの責任者。構図は独立責任者。各自100点満点で評価する。
# intent = 社長が各責任者へ伝える意図 / guide = 審査の着眼点
DIRECTORS = [
    {
        "key": "photo", "name": "📷 撮影ディレクター", "area": "写真のリアルさ・画質",
        "intent": "一眼レフで撮った実写に見せること。CG/イラスト/作り物っぽさは即不合格。8K級の解像感とピント、自然な質感を担保せよ。",
        "guide": "実際に撮影した本物の料理写真に見えるか。CG・AI・作り物っぽさが無いか。解像感・ピント・質感。",
    },
    {
        "key": "styling", "name": "🍳 フードスタイリスト", "area": "シズル感・盛り付け",
        "intent": "思わず生唾を飲むシズル感を最優先。湯気・照り・みずみずしさ・焼き色で食欲を最大化。具材は皿いっぱいに立体的に山高く、量感を出して美しく盛れ。",
        "guide": "照り・湯気・みずみずしさ・焼き色があり食欲をそそるか。具材が皿いっぱいに立体的・豊かに盛られ、美しいか。",
    },
    {
        "key": "art", "name": "🎨 アートディレクター", "area": "世界観・ブランド統一",
        "intent": "暗い木目＋黒背景、上後方からの暖色スポット光で参考の世界観に統一せよ。窓や雑多な小物を写すな。色味とライティングのブレを許すな。",
        "guide": "暗い木目＋黒背景＋暖色スポット光の参考世界観に一致するか。余計な小物/窓が無く、色味が統一されているか。",
    },
    {
        "key": "composition", "name": "📐 構図ディレクター", "area": "構図・レイアウト",
        "intent": "主役を画面中央〜やや下に大きく、皿のフチまで入れて指定アスペクト比に最適化せよ。アングル・余白・視線誘導を設計せよ。",
        "guide": "主役が画面中央〜やや下に大きく、皿のフチまで収まり、指定アスペクト比に最適な構図か。余白・バランス。",
    },
    {
        "key": "proof", "name": "🔍 校閲ディレクター", "area": "要望一致・器・透かし",
        "intent": "指定の料理であること、写真内に文字/ロゴ/透かし/ウォーターマーク(キラ✦含む)が無いこと、完成料理が黒い和皿に盛られていること(フライパン提供はNG)を厳格に確認せよ。",
        "guide": "指定した料理そのものに見えるか。写真内に文字・ロゴ・透かし・ウォーターマーク(キラ✦等)が無いか。",
    },
]


def ceo_brief() -> str:
    """社長が各責任者へデザインの目的と意図を共有する『指示書』テキスト。"""
    lines = ["【社長から各責任者へ：デザイン意図の共有】",
             f"◆デザインの目的: {DESIGN_PURPOSE}", "◆各責任者への意図:"]
    for d in DIRECTORS:
        lines.append(f"  {d['name']}〔{d['area']}〕→ {d['intent']}")
    return "\n".join(lines)


def _director_verdicts(scores: dict, pass_score: int) -> list[dict]:
    """各責任者の100点満点スコアから合否・コメントを構成する。"""
    out = []
    for d in DIRECTORS:
        s = scores.get(d["key"], {})
        score = int(s.get("score", 0))
        passed = score >= pass_score
        out.append({"key": d["key"], "name": d["name"], "area": d["area"],
                    "score": score, "passed": passed,
                    "comment": s.get("comment", "")})
    return out


@dataclass
class ReviewResult:
    passed: bool                                  # 全責任者が合格したか
    total: int                                    # 全責任者の平均点(0-100)
    pass_score: int                               # 各責任者の合格ライン(100点満点中)
    scores: dict = field(default_factory=dict)    # key -> {"score":0-100,"comment":str}
    summary: str = ""
    requests: list[str] = field(default_factory=list)   # 改善要望(責任者名付き)
    regenerate_prompt: str = ""                          # 作り直し用プロンプト案
    engine: str = ""                                     # gemini / heuristic
    directors: list = field(default_factory=list)        # 責任者ごとの合否(各100点)

    def failed_directors(self) -> list[str]:
        return [d["name"] for d in self.directors if not d["passed"]]

    def report(self, title: str = "") -> str:
        mark = "✅ 合格" if self.passed else "❌ 不合格"
        lines = [
            "============================================",
            f"  デザイン品質審査 {(': ' + title) if title else ''}",
            "============================================",
            "経営体制: 会長(オーナー) ─ 社長(統括/意図伝達) ─ 各責任者(100点満点で審査)",
            f"判定: {mark}   平均: {self.total}/100   各責任者の合格ライン: {self.pass_score}",
            f"審査エンジン: {self.engine}",
        ]
        if self.directors:
            ng = self.failed_directors()
            lines += ["",
                      f"■責任者別の判定（問題の所在: {('、'.join(ng) if ng else 'なし＝全員合格')}）"]
            for d in self.directors:
                dm = "✅" if d["passed"] else "❌"
                lines.append(f"  {dm} {d['name']}〔{d['area']}〕 {d['score']}/100")
                if d["comment"]:
                    lines.append(f"        所見: {d['comment']}")
        lines += ["", "【総評（社長まとめ）】", self.summary or "-"]
        if self.requests:
            lines += ["", "【改善要望（担当責任者別）】"] + [f"  - {r}" for r in self.requests]
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
        subject = (f"この画像は料理「{recipe.title_main}」の【調理工程】写真のはずです。"
                   "完成品ではなく、鍋・フライパン・まな板など調理中の様子が、"
                   "ヒーロー写真と同じ世界観・色味で撮れているか。")
        comp_extra = f"正方形({aspect})に最適化されているか。"
        proof_extra = ""  # 工程はフライパン・鍋OK
    else:
        subject = f"この画像は完成した料理「{dish}」の【表紙メイン写真】のはずです。"
        comp_extra = f"縦長({aspect})に最適化されているか。"
        proof_extra = "【重要】完成料理はフライパン・スキレット・鍋ではなく、黒いマットの和皿に盛られているか（皿でなければ大きく減点）。"

    # 社長が各責任者に伝える意図＋着眼点（構図/校閲には種類別の追加観点を明示）
    _extra = {"composition": comp_extra, "proof": proof_extra}
    dir_lines = []
    for d in DIRECTORS:
        guide = d["guide"] + (f" {_extra[d['key']]}" if _extra.get(d["key"]) else "")
        dir_lines.append(f'- {d["key"]}（{d["name"]}・{d["area"]}）\n'
                         f'    社長の意図: {d["intent"]}\n'
                         f'    着眼点: {guide}')
    directors_txt = "\n".join(dir_lines)
    json_keys = ", ".join(f'"{d["key"]}": {{"score":0,"comment":"..."}}' for d in DIRECTORS)

    prompt = f"""あなたはグルメ系レシピTikTok制作会社の「社長」です。会社の経営体制は次の通り:
- 会長(オーナー)のビジョンを、社長であるあなたが「デザインの目的」に翻訳して各責任者へ意図を伝える。
- 各責任者は専門領域のプロで、社長の意図に沿って自分の領域だけを【100点満点】で厳しく採点する。

# デザインの目的（社長が会長のビジョンを翻訳したもの）
{DESIGN_PURPOSE}

# 審査対象
{subject}
妥協せず辛口に。最重要は「AIっぽくない本物感」。

# 各責任者（それぞれ自領域を0〜100点で採点。commentは具体的な指摘を1文）
{directors_txt}

# 出力（必ずJSONのみ。前後に文章やマークダウン記号を付けない）
{{
  "scores": {{ {json_keys} }},
  "summary": "社長としての総評(80文字程度)",
  "regenerate_prompt": "改善のためGeminiアプリへ貼る画像生成プロンプト(日本語・具体的)"
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
        ps = _pass_score()
        verdicts = _director_verdicts(scores, ps)
        total = round(sum(v["score"] for v in verdicts) / len(verdicts)) if verdicts else 0
        # 改善要望を「どの責任者の指摘か」付きで構成
        reqs = [f"【{v['name']}】{v['comment']}" for v in verdicts if not v["passed"] and v["comment"]]
        return ReviewResult(
            passed=all(v["passed"] for v in verdicts),
            total=total,
            pass_score=ps,
            scores=scores,
            summary=d.get("summary", ""),
            requests=reqs,
            regenerate_prompt=d.get("regenerate_prompt", ""),
            engine=f"Gemini Vision ({used_model})",
            directors=verdicts,
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

    # 各責任者を100点満点で簡易採点（目視できない領域は控えめに）
    comp_ok = vertical and enough_res
    scores = {
        "photo": {"score": 60 if has_content else 20,
                  "comment": "自動目視では本物感を断定不可（API審査推奨）。"},
        "styling": {"score": 55 if has_content else 20,
                    "comment": "色味あり" if has_content else "情報量が少ない"},
        "art": {"score": 80 if dark_mood else 45,
                "comment": "暗背景で世界観OK" if dark_mood else "明るすぎ。背景を暗く"},
        "composition": {"score": 80 if comp_ok else 40,
                        "comment": (f"アスペクト/解像度OK" if comp_ok
                                    else f"アスペクト比({aspect})・解像度({w}x{h})要改善")},
        "proof": {"score": 60, "comment": "料理一致・文字有無は目視不可（API審査推奨）。"},
    }
    verdicts = _director_verdicts(scores, ps)
    total = round(sum(v["score"] for v in verdicts) / len(verdicts)) if verdicts else 0
    reqs = [f"【{v['name']}】{v['comment']}" for v in verdicts if not v["passed"] and v["comment"]]
    return ReviewResult(
        passed=all(v["passed"] for v in verdicts),
        total=total,
        pass_score=ps,
        scores=scores,
        summary="簡易判定（明るさ・縦横比・解像度のみ）。本格審査はGemini APIキー設定時に有効。",
        requests=reqs,
        engine="heuristic（APIなし簡易判定）",
        directors=verdicts,
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
