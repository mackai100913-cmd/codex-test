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
        "guide": "減点項目を厳格に: ①プラスチック/ワックス/3DCG的な質感→大減点 ②ピントが甘い・全面パンフォーカスで立体感が無い→減点 ③過度なHDR・過彩度・不自然なシャープ→減点 ④ノイズ・破綻したディテール→減点。プロの料理写真集を90点とし、満たない要素ごとに引く。",
    },
    {
        "key": "styling", "name": "🍳 フードスタイリスト", "area": "シズル感・盛り付け",
        "intent": "思わず生唾を飲むシズル感を最優先。湯気・照り・みずみずしさ・焼き色で食欲を最大化。具材は皿いっぱいに立体的に山高く、量感を出して美しく盛れ。",
        "guide": "減点項目: ①湯気・照り・シズルが弱い/無い→大減点 ②盛りが平坦・量感不足・皿がスカスカ→減点 ③人工的なベタついた光沢・作り物の照り→減点 ④あしらいが過剰/雑/不自然→減点。広告写真レベルの食欲喚起を90点基準とする。",
    },
    {
        "key": "art", "name": "🎨 アートディレクター", "area": "世界観・ブランド統一",
        "intent": "暗い木目＋黒背景、上後方からの暖色スポット光で参考の世界観に統一せよ。窓や雑多な小物を写すな。色味とライティングのブレを許すな。",
        "guide": "減点項目: ①色温度のブレ・色味が参考と不一致→減点 ②余計な小物/布/窓が写る→大減点 ③背景が明るすぎ/漆黒に落ちていない→減点 ④木目が安っぽい/質感が雑→減点。",
    },
    {
        "key": "composition", "name": "📐 構図ディレクター", "area": "構図・レイアウト",
        "intent": "主役を画面中央〜やや下に大きく、皿のフチまで入れて指定アスペクト比に最適化せよ。アングル・余白・視線誘導を設計せよ。",
        "guide": "減点項目: ①主役が小さい/余白過多→大減点 ②余白不足で窮屈→減点 ③水平の傾き・歪み→減点 ④皿が切れすぎ/中心がずれる→減点。指定アスペクト比に最適化されているか。",
    },
    {
        "key": "proof", "name": "🔍 校閲ディレクター", "area": "要望一致・器・透かし",
        "intent": "指定の料理であること、写真内に文字/ロゴ/透かし/ウォーターマーク(キラ✦含む)が無いこと、完成料理が黒い和皿に盛られていること(フライパン提供はNG)を厳格に確認せよ。",
        "guide": "減点項目: ①文字/ロゴ/透かし/✦が1つでも見える→20点以下 ②完成写真の器が黒い和皿でない(フライパン/鍋等)→大減点 ③指定の料理に見えない→大減点。",
    },
]


def ceo_brief() -> str:
    """社長が各責任者へデザインの目的と意図を共有する『指示書』テキスト。"""
    lines = ["【社長から各責任者へ：デザイン意図の共有】",
             f"◆デザインの目的: {DESIGN_PURPOSE}", "◆各責任者への意図:"]
    for d in DIRECTORS:
        lines.append(f"  {d['name']}〔{d['area']}〕→ {d['intent']}")
    return "\n".join(lines)


def _coerce_score(value) -> tuple[int, str]:
    """1責任者分のスコア表現を (score, comment) に正規化する。

    モデルの出力ゆれに強くする。次のいずれの形も受け付ける:
      - {"score": 85, "comment": "..."}（英語キー）
      - {"点数": 85, "コメント": "..."} / {"点": 85, "所見": "..."}（日本語キー）
      - 85 / "85"（数値そのもの）
    """
    comment = ""
    raw = value
    if isinstance(value, dict):
        for k in ("score", "点数", "点", "score_100", "value"):
            if k in value:
                raw = value[k]
                break
        else:
            raw = 0
        for k in ("comment", "コメント", "所見", "理由", "reason"):
            if value.get(k):
                comment = str(value[k])
                break
    try:
        score = int(round(float(raw)))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score)), comment


def _director_verdicts(scores: dict, pass_score: int) -> list[dict]:
    """各責任者の100点満点スコアから合否・コメントを構成する。"""
    scores = scores or {}
    out = []
    for d in DIRECTORS:
        # キーは英語(photo等)が基本だが、責任者名や領域名で返ることもあるため広く探す。
        raw = scores.get(d["key"])
        if raw is None:
            for alt in (d["name"], d["area"]):
                if alt in scores:
                    raw = scores[alt]
                    break
        score, comment = _coerce_score(raw if raw is not None else {})
        passed = score >= pass_score
        out.append({"key": d["key"], "name": d["name"], "area": d["area"],
                    "score": score, "passed": passed, "comment": comment})
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

_WARNED = False


def _warn_once(msg: str) -> None:
    global _WARNED
    if not _WARNED:
        print(msg)
        _WARNED = True


def build_review_prompt(recipe: Recipe, kind: str = "hero", aspect: str = "9:16") -> str:
    """各責任者の厳格ルーブリックを盛り込んだ審査プロンプトを構築する。

    API審査(_gemini_review)とブラウザ審査(auto_gemini)で共用する。
    """
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

# 採点の絶対基準（甘い採点を厳禁する）
- 90-100: 一流の料理写真集・広告レベル。文句なし。
- 75-89 : プロ水準だが、参考世界観との差分が指摘できる(光・照り・盛り・色のどれか)。
- 60-74 : 素人〜中級。SNSで止まるが高級感に届かない。
- 0-59  : AIっぽさ/破綻/要望違反のいずれかが明確にある。
まず「プロの参考品質(90点)を頭に置き、対象に足りない点を具体的に1つ以上挙げてから」採点せよ。
中庸な点(70前後)に逃げず、欠点が見えるなら必ず75未満に落とすこと。全項目が80超えは本当に優秀な時だけ。
最重要は「AIっぽくない本物感」。1つでも文字・ロゴ・透かし・✦が見えたら校閲(proof)は20点以下にせよ。

# 各責任者（それぞれ自領域を0〜100点で採点。commentは"参考品質との差分"を具体的に1文）
{directors_txt}

# 出力（必ずJSONのみ。前後に文章やマークダウン記号を付けない）
{{
  "scores": {{ {json_keys} }},
  "summary": "社長としての総評(80文字程度)。最も足を引っ張った領域を名指しで。",
  "regenerate_prompt": "改善のためGeminiアプリへ貼る画像生成プロンプト(日本語・具体的)"
}}
"""
    return prompt


def parse_review_text(text: str, engine: str) -> ReviewResult:
    """審査の応答テキスト(JSON)を ReviewResult に変換する。

    API応答・ブラウザ応答の双方で共用。前後にプロンプト文やマークダウン記号が
    混ざっていても、最初の '{' から最後の '}' までを取り出してパースする。
    JSONとして解釈できない場合は例外を送出する（呼び出し側でフォールバック）。
    """
    text = (text or "").strip()
    if "```" in text:
        text = text.replace("```json", "```").strip("`")
    if "{" in text and "}" in text:
        text = text[text.find("{"): text.rfind("}") + 1]
    d = json.loads(text)
    scores = d.get("scores") or d.get("評価") or {}
    ps = _pass_score()
    verdicts = _director_verdicts(scores, ps)
    # "scores"ラッパが無く、責任者キーが直下に並ぶ形にも対応（全0なら直下を再探索）。
    if not any(v["score"] for v in verdicts):
        alt = _director_verdicts(d, ps)
        if any(v["score"] for v in alt):
            verdicts = alt
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
        engine=engine,
        directors=verdicts,
    )


def _gemini_review(image_path: Path, recipe: Recipe,
                   kind: str = "hero", aspect: str = "9:16") -> ReviewResult | None:
    api_key = config.usable_gemini_api_key()
    if not api_key:
        if (config.gemini_api_key() or "").startswith("AQ."):
            _warn_once("⚠ AQ.形式のキーはGoogle側の不具合でAPI審査に使えません。"
                       "API審査をスキップします（ブラウザ審査か簡易判定になります）。")
        else:
            _warn_once("⚠ GEMINI_API_KEY が未設定のため、API審査は使えません（ブラウザ審査か簡易判定になります）。")
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:
        _warn_once("⚠ google-genai 未導入のため簡易判定になります（pip install google-genai）。")
        return None

    prompt = build_review_prompt(recipe, kind, aspect)
    try:
        data = image_path.read_bytes()
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        client = genai.Client(api_key=api_key)
        r, used_model = _generate_with_retry(
            client, _review_models(),
            [types.Part.from_bytes(data=data, mime_type=mime), prompt],
        )
        return parse_review_text(r.text or "", f"Gemini Vision ({used_model})")
    except Exception as e:  # noqa: BLE001
        _warn_once(f"⚠ Vision審査の呼び出しに失敗したため簡易判定に切替: {type(e).__name__}: {e}\n"
                   "   （APIキーが無効/期限切れ、課金未設定、モデル名誤りの可能性。新しいキーを .env に設定してください）")
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
