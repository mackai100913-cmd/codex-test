"""文言（タイトル・各スライドの焼き込み文字・キャプション・ハッシュタグ）を自動生成。

- GEMINI_API_KEY があれば Gemini テキストモデルでリッチに生成。
- 無ければテンプレートエンジンで生成（オフライン・無料で完結）。
どちらでも同じ Copy データ構造を返すので後段は共通。
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from . import config
from .content_planner import PostPlan


@dataclass
class SlideText:
    role: str          # cover / dish / info / cta
    headline: str      # 画像に焼き込む大きな文字
    sub: str = ""      # 補足の小さい文字


@dataclass
class Copy:
    title: str                 # フック（表紙の主役コピー）
    slides: list[SlideText]
    caption: str               # 投稿本文
    hashtags: list[str] = field(default_factory=list)


def _build_hashtags(plan: PostPlan) -> list[str]:
    persona = config.persona()
    tags_cfg = persona["hashtags"]
    tags = list(tags_cfg["always"])

    rng = random.Random(plan.post_id)
    rotating = rng.sample(
        tags_cfg["rotating_broad"],
        k=min(3, len(tags_cfg["rotating_broad"])),
    )
    # エリア・料理から動的タグも生成
    dynamic = [f"#{plan.area}グルメ", f"#{plan.dish}"]
    tags += rotating + dynamic

    # 重複除去しつつ件数を調整
    seen: list[str] = []
    for t in tags:
        if t not in seen:
            seen.append(t)
    return seen[: tags_cfg.get("count", 8)]


# ---------------------------------------------------------------------------
# テンプレートエンジン（フォールバック・APIキー不要）
# ---------------------------------------------------------------------------

def _template_copy(plan: PostPlan) -> Copy:
    title = plan.hook_template.format(
        dish=plan.dish, n=plan.extras.get("limited_count", 20)
    )

    slides = [
        SlideText(
            role="cover",
            headline=title,
            sub=f"{plan.area} / {plan.price_band}",
        ),
        SlideText(
            role="dish",
            headline="まずはこのビジュアル",
            sub=f"湯気と照りがやばい{plan.dish}",
        ),
        SlideText(
            role="dish",
            headline="断面で優勝",
            sub="この瞬間のために来てほしい",
        ),
        SlideText(
            role="dish",
            headline=f"{plan.angle_label}の理由",
            sub=f"{plan.price_band}でこの満足度",
        ),
        SlideText(
            role="info",
            headline="店舗INFO",
            sub=f"エリア: {plan.area}｜目安: {plan.price_band}",
        ),
    ]

    caption = (
        f"【{plan.area}】{title}\n\n"
        f"{plan.angle_label}の{plan.dish}を発見。\n"
        f"目安は{plan.price_band}。\n"
        "気になった人は「保存」して後で行ってね📌\n"
        "保存数が伸びると次のお店探しの励みになります🙏"
    )

    return Copy(
        title=title,
        slides=slides,
        caption=caption,
        hashtags=_build_hashtags(plan),
    )


# ---------------------------------------------------------------------------
# Gemini テキスト生成（任意・APIキーがある場合）
# ---------------------------------------------------------------------------

def _gemini_copy(plan: PostPlan) -> Copy | None:
    api_key = config.gemini_api_key()
    if not api_key:
        return None
    try:
        from google import genai
    except Exception:
        return None

    persona = config.persona()
    brand = persona["brand"]
    prompt = f"""あなたは日本のバズるグルメTikTok運用のプロです。
以下の条件で、画像カルーセル投稿の文言を作ってください。

# ブランドの世界観
- トーン: {brand['tone']}
- 型: {"; ".join(brand['signature_style'])}

# 今回のネタ
- 切り口: {plan.angle_label}
- 料理: {plan.dish}
- エリア: {plan.area}
- 価格帯: {plan.price_band}
- 参考フック: {plan.hook_template.format(dish=plan.dish, n=plan.extras.get('limited_count', 20))}

# 出力（必ず JSON のみ。前後に説明文を付けない）
{{
  "title": "表紙の主役コピー(20文字以内・強いフック)",
  "slides": [
    {{"role":"cover","headline":"...","sub":"..."}},
    {{"role":"dish","headline":"...","sub":"..."}},
    {{"role":"dish","headline":"...","sub":"..."}},
    {{"role":"dish","headline":"...","sub":"..."}},
    {{"role":"info","headline":"店舗INFO","sub":"エリアや価格など"}}
  ],
  "caption": "投稿本文(改行可・最後に保存導線)"
}}
"""
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=config.text_model(),
            contents=prompt,
        )
        text = (resp.text or "").strip()
        # ```json ... ``` で囲まれている場合に備えて剥がす
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{"): text.rfind("}") + 1]
        data = json.loads(text)
        slides = [
            SlideText(
                role=s.get("role", "dish"),
                headline=s.get("headline", ""),
                sub=s.get("sub", ""),
            )
            for s in data["slides"]
        ]
        return Copy(
            title=data["title"],
            slides=slides,
            caption=data["caption"],
            hashtags=_build_hashtags(plan),
        )
    except Exception:
        # 失敗時はテンプレにフォールバック
        return None


def write_copy(plan: PostPlan) -> Copy:
    """企画から文言一式を生成する。Gemini → 失敗時テンプレ。"""
    return _gemini_copy(plan) or _template_copy(plan)
