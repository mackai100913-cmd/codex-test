"""画像生成（Gemini 3 Pro Image / Nano Banana Pro）と文字焼き込み。

- GEMINI_API_KEY があれば実画像を生成。
- 無ければ PIL でダミー画像を生成（パイプライン全体を無料で動作確認できる）。
生成後、各スライドの headline / sub を画像に焼き込んでTikTok映え仕様にする。
"""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config
from .content_planner import PostPlan
from .copywriter import Copy, SlideText

# TikTok縦型
WIDTH, HEIGHT = 1080, 1920


def _image_prompt(plan: PostPlan, slide: SlideText) -> str:
    """Gemini に渡す画像生成プロンプト（料理写真のシズル感重視）。"""
    base = (
        f"プロのフードフォトグラファーが撮影した、{plan.dish}の超高画質な写真。"
        "湯気・照り・みずみずしさ（シズル感）を強調。"
        "美味しそうに見えるライティング、浅い被写界深度、9:16の縦構図、"
        "食欲をそそる暖色系、余白は上下に確保（後から文字を載せるため）。"
        "実在の店名ロゴや人物の顔は写さない。"
    )
    if slide.role == "info":
        base += " テーブルに料理が並ぶ俯瞰の引き画。情報テロップを載せやすい構図。"
    elif "断面" in (slide.headline + slide.sub):
        base += f" {plan.dish}の断面が見えるアップ。"
    return base


# ---------------------------------------------------------------------------
# 背景画像の取得（Gemini or ダミー）
# ---------------------------------------------------------------------------

def _gemini_image(prompt: str) -> Image.Image | None:
    api_key = config.gemini_api_key()
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=config.image_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        for part in resp.candidates[0].content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                img = Image.open(io.BytesIO(inline.data)).convert("RGB")
                return _cover_resize(img, WIDTH, HEIGHT)
    except Exception:
        return None
    return None


def _cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    """アスペクト比を保ったまま中央クロップで w x h に合わせる。"""
    src_ratio = img.width / img.height
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        new_h = h
        new_w = int(h * src_ratio)
    else:
        new_w = w
        new_h = int(w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _placeholder_image(plan: PostPlan, slide: SlideText) -> Image.Image:
    """APIキー無し用ダミー背景（グラデーション）。"""
    persona = config.persona()
    base_hex = persona["design"]["primary_color"].lstrip("#")
    r, g, b = (int(base_hex[i: i + 2], 16) for i in (0, 2, 4))
    img = Image.new("RGB", (WIDTH, HEIGHT))
    px = img.load()
    for y in range(HEIGHT):
        f = y / HEIGHT
        px_row = (
            int(r * (1 - f) + 30 * f),
            int(g * (1 - f) + 30 * f),
            int(b * (1 - f) + 30 * f),
        )
        for x in range(WIDTH):
            px[x, y] = px_row
    d = ImageDraw.Draw(img)
    small = _load_font(28)
    d.text((40, 40), "DEMO背景 / GEMINI_API_KEY 未設定", fill="#FFFFFF", font=small)
    d.text((40, 84), "本番では実際の料理写真が生成されます", fill="#FFFFFF", font=small)
    return img


# ---------------------------------------------------------------------------
# 文字焼き込み
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """日本語が出るフォントを探す。無ければデフォルト。"""
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_text_block(
    img: Image.Image,
    text: str,
    *,
    y: int,
    font_size: int,
    fill: str,
    stroke: str,
    wrap: int = 12,
) -> int:
    """中央寄せで太字＋フチ付きテキストを描画。次の y を返す。"""
    if not text:
        return y
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size)
    lines = textwrap.wrap(text, width=wrap) or [text]
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (WIDTH - tw) // 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=max(3, font_size // 12),
            stroke_fill=stroke,
        )
        y += int(font_size * 1.25)
    return y


def _scrim(img: Image.Image, top: bool) -> None:
    """文字の可読性を上げる半透明の帯を載せる。"""
    overlay = Image.new("RGBA", (WIDTH, 520), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(520):
        alpha = int(150 * (1 - i / 520)) if top else int(150 * (i / 520))
        od.line([(0, i), (WIDTH, i)], fill=(0, 0, 0, alpha))
    img.paste(overlay, (0, 0 if top else HEIGHT - 520), overlay)


def render_slide(plan: PostPlan, slide: SlideText, copy: Copy) -> Image.Image:
    bg = _gemini_image(_image_prompt(plan, slide)) or _placeholder_image(plan, slide)
    img = bg.convert("RGBA")
    design = config.persona()["design"]

    if slide.role == "cover":
        _scrim(img, top=True)
        y = _draw_text_block(
            img, slide.headline, y=120, font_size=96,
            fill=design["accent_color"], stroke=design["text_stroke_color"], wrap=10,
        )
        _draw_text_block(
            img, slide.sub, y=y + 20, font_size=52,
            fill=design["text_color"], stroke=design["text_stroke_color"], wrap=16,
        )
    else:
        _scrim(img, top=False)
        base_y = HEIGHT - 460
        y = _draw_text_block(
            img, slide.headline, y=base_y, font_size=80,
            fill=design["accent_color"], stroke=design["text_stroke_color"], wrap=12,
        )
        _draw_text_block(
            img, slide.sub, y=y + 16, font_size=48,
            fill=design["text_color"], stroke=design["text_stroke_color"], wrap=18,
        )
    return img.convert("RGB")


def generate_images(plan: PostPlan, copy: Copy, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for idx, slide in enumerate(copy.slides, start=1):
        img = render_slide(plan, slide, copy)
        p = out_dir / f"slide_{idx:02d}_{slide.role}.jpg"
        img.save(p, quality=92)
        paths.append(p)
    return paths
