"""画像生成（Gemini 3 Pro Image / Nano Banana Pro）と、表紙・レシピカードの合成。

生成物は2枚:
  1. 表紙        … 暗背景の料理写真＋金/白タイトル＋導入文（決めワード赤）＋説明
  2. レシピカード … ヒーロー写真＋調理時間/費用/難易度＋材料＋ポイント＋手順01〜06

GEMINI_API_KEY が無い場合は PIL のダミー画像で全工程を確認できる。
AIっぽさを避けるため、画像プロンプトは「本物の家庭料理に見えるリアルな写真」を指示する。
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config
from .content_planner import PostPlan
from .recipe_generator import Recipe

W, H = 1080, 1920

# --- フォント -------------------------------------------------------------

_GOTHIC = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]
_MINCHO = [
    "/usr/share/fonts/opentype/ipafont-mincho/ipamp.ttf",
    "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-mincho.ttf",
]


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def gothic(size: int) -> ImageFont.FreeTypeFont:
    return _font(_GOTHIC, size)


def mincho(size: int) -> ImageFont.FreeTypeFont:
    return _font(_MINCHO, size)


# --- 画像取得（Gemini or ダミー） -----------------------------------------

def _gemini_image(prompt: str, aspect: str) -> Image.Image | None:
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
        cfg = types.GenerateContentConfig(response_modalities=["IMAGE"])
        # 対応バージョンならアスペクト比も指定
        try:
            cfg.image_config = types.ImageConfig(aspect_ratio=aspect)
        except Exception:
            pass
        resp = client.models.generate_content(
            model=config.image_model(),
            contents=f"{prompt}\nアスペクト比は{aspect}。",
            config=cfg,
        )
        for part in resp.candidates[0].content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return Image.open(io.BytesIO(inline.data)).convert("RGB")
    except Exception:
        return None
    return None


def _cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    sr, dr = img.width / img.height, w / h
    if sr > dr:
        nw, nh = int(h * sr), h
    else:
        nw, nh = w, int(w / sr)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _dummy_food(w: int, h: int, label: str) -> Image.Image:
    """APIキー無し用のダミー料理写真（暗いラジアルグラデ＋皿）。"""
    img = Image.new("RGB", (w, h), (13, 13, 13))
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.62)
    r = int(min(w, h) * 0.42)
    for i in range(r, 0, -2):
        t = i / r
        col = (int(60 * (1 - t) + 13 * t), int(40 * (1 - t) + 13 * t), int(30 * (1 - t) + 13 * t))
        d.ellipse([cx - i, cy - i, cx + i, cy + i], fill=col)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(90, 70, 50), width=4)
    f = gothic(34)
    tb = d.textbbox((0, 0), label, font=f)
    d.text((cx - (tb[2] - tb[0]) // 2, cy - 18), label, font=f, fill=(180, 170, 160))
    f2 = gothic(22)
    note = "DEMO（GEMINI_API_KEY未設定）"
    nb = d.textbbox((0, 0), note, font=f2)
    d.text((cx - (nb[2] - nb[0]) // 2, h - 60), note, font=f2, fill=(120, 120, 120))
    return img


def hero_image(recipe: Recipe) -> Image.Image:
    dish = f"{recipe.title_top}{recipe.title_main}"
    prompt = (
        f"プロのフードフォトグラファーが実際に撮影した「{dish}」の写真。"
        "黒い和食器に盛り付け、暗い木のテーブル、背景は黒。立ち上る湯気、"
        "照り・シズル感、暖色のライティング、浅い被写界深度。"
        "作り物やCGに見えない、本物の家庭料理のリアルな質感と自然な盛り付け。"
        "文字やロゴは入れない。"
    )
    img = _gemini_image(prompt, "9:16") or _dummy_food(W, H, recipe.title_main)
    return _cover_resize(img, W, H)


def step_image(recipe: Recipe, step_title: str, detail: str) -> Image.Image:
    prompt = (
        f"料理「{recipe.title_main}」の調理工程「{step_title}」の写真。{detail} "
        "フライパンや鍋・まな板など調理中のリアルな様子。暗いキッチンの俯瞰、"
        "本物の家庭料理に見える自然な写真。文字は入れない。正方形。"
    )
    img = _gemini_image(prompt, "1:1") or _dummy_food(400, 400, step_title)
    return _cover_resize(img, 400, 400)


# --- 描画ヘルパー ---------------------------------------------------------

def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        t = cur + ch
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def _text(draw, xy, s, font, fill, stroke=0, stroke_fill="#000000", anchor=None):
    draw.text(xy, s, font=font, fill=fill, stroke_width=stroke,
              stroke_fill=stroke_fill, anchor=anchor)


def _rich_wrapped(draw, segments, x, y, max_w, font, lh, stroke=0):
    """[(text,color)] を折り返しつつ描画。決めワードだけ色を変える用途。"""
    cx = x
    for text, color in segments:
        for ch in text:
            w = draw.textlength(ch, font=font)
            if ch == "\n" or cx + w > x + max_w:
                y += lh
                cx = x
                if ch == "\n":
                    continue
            _text(draw, (cx, y), ch, font, color, stroke=stroke)
            cx += w
    return y + lh


def _spaced_center(draw, s, cy_x_center, y, font, fill, spacing, stroke=0, stroke_fill="#000"):
    widths = [draw.textlength(c, font=font) + spacing for c in s]
    total = sum(widths) - spacing
    x = cy_x_center - total / 2
    for c, w in zip(s, widths):
        _text(draw, (x, y), c, font, fill, stroke=stroke, stroke_fill=stroke_fill)
        x += w


def _top_scrim(img, height, alpha=180):
    ov = Image.new("RGBA", (W, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for i in range(height):
        od.line([(0, i), (W, i)], fill=(0, 0, 0, int(alpha * (1 - i / height))))
    img.paste(ov, (0, 0), ov)


def _check(draw, x, y, size, color="#3DC06C"):
    draw.rounded_rectangle([x, y, x + size, y + size], radius=5, fill=color)
    draw.line([(x + size * 0.22, y + size * 0.55),
               (x + size * 0.43, y + size * 0.76),
               (x + size * 0.80, y + size * 0.28)],
              fill="#FFFFFF", width=max(3, size // 7), joint="curve")


# --- 表紙の合成 -----------------------------------------------------------

def render_cover(recipe: Recipe, hero: Image.Image) -> Image.Image:
    d_cfg = config.design()
    img = hero.convert("RGBA")
    _top_scrim(img, 980, alpha=200)
    draw = ImageDraw.Draw(img)

    mx = 70
    y = 150

    # 導入文（決めワードを赤に）
    intro_font = gothic(38)
    hi = recipe.intro_highlight
    if hi and hi in recipe.intro:
        a, b = recipe.intro.split(hi, 1)
        segs = [(a, d_cfg["body_text"]), (hi, d_cfg["highlight_red"]), (b, d_cfg["body_text"])]
    else:
        segs = [(recipe.intro, d_cfg["body_text"])]
    y = _rich_wrapped(draw, segs, mx, y, W - mx * 2, intro_font, 52, stroke=2)
    y += 24

    # 金色サブタイトル
    sub_font = gothic(70)
    for line in _wrap(draw, recipe.title_top, sub_font, W - mx * 2):
        _text(draw, (mx, y), line, sub_font, d_cfg["title_gold"], stroke=3)
        y += 84

    # 料理名（明朝・字間広め）
    main_font = mincho(132)
    _spaced_center(draw, recipe.title_main, W // 2, y, main_font,
                   d_cfg["title_white"], spacing=14, stroke=4, stroke_fill="#000")
    y += 168
    # 金のアクセント線
    lw = min(W - mx * 2, len(recipe.title_main) * 150)
    draw.line([(W // 2 - lw // 2, y), (W // 2 + lw // 2, y)], fill=d_cfg["title_gold"], width=4)
    y += 36

    # 説明文
    desc_font = gothic(36)
    for line in _wrap(draw, recipe.description, desc_font, W - mx * 2):
        _text(draw, (mx, y), line, desc_font, d_cfg["body_text"], stroke=2)
        y += 50

    return img.convert("RGB")


# --- レシピカードの合成 ----------------------------------------------------

def _panel(draw, box, fill, outline=None, width=2, radius=14):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def render_card(recipe: Recipe, hero: Image.Image, steps: list[Image.Image]) -> Image.Image:
    c = config.design()
    img = Image.new("RGB", (W, H), c["bg_color"])

    # 上部: ヒーロー写真＋タイトル
    top_h = 540
    img.paste(_cover_resize(hero, W, top_h), (0, 0))
    draw = ImageDraw.Draw(img)
    sc = Image.new("RGBA", (W, top_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sc)
    for i in range(top_h):
        sd.line([(0, i), (W, i)], fill=(0, 0, 0, int(150 * (1 - i / top_h))))
    img.paste(sc, (0, 0), sc)
    draw = ImageDraw.Draw(img)
    _text(draw, (60, 60), recipe.title_top, gothic(56), c["title_gold"], stroke=3)
    _spaced_center(draw, recipe.title_main, W // 2, 130, mincho(104),
                   c["title_white"], spacing=10, stroke=4)

    y = top_h + 30

    # メトリクス行
    mh = 130
    _panel(draw, [40, y, W - 40, y + mh], c["card_panel"], outline=c["accent_line"], width=2)
    cells = [("調理時間", recipe.time, None),
             ("費用目安", recipe.cost, f"（{recipe.servings}）"),
             ("難易度", "★" * recipe.difficulty + "☆" * (5 - recipe.difficulty),
              f"（{recipe.difficulty_label}）")]
    cw = (W - 80) / 3
    for i, (label, value, sub) in enumerate(cells):
        cxc = 40 + cw * i + cw / 2
        if i > 0:
            draw.line([(40 + cw * i, y + 20), (40 + cw * i, y + mh - 20)], fill=c["accent_line"], width=1)
        _text(draw, (cxc, y + 22), label, gothic(28), c["title_gold"], anchor="ma")
        _text(draw, (cxc, y + 58), value, gothic(38), c["title_white"], anchor="ma")
        if sub:
            _text(draw, (cxc, y + 100), sub, gothic(22), c["body_text"], anchor="ma")
    y += mh + 26

    col_top = y
    left_x, left_w = 50, 470
    right_x, right_w = 560, 480

    # 左: 材料
    ly = col_top
    _text(draw, (left_x, ly), f"材料（{recipe.servings}）", gothic(40), c["title_gold"])
    ly += 50
    draw.line([(left_x, ly), (left_x + left_w, ly)], fill=c["accent_line"], width=2)
    ly += 14
    ing_f = gothic(28)
    for ing in recipe.ingredients:
        _text(draw, (left_x, ly), f"・{ing.name}", ing_f, c["body_text"])
        _text(draw, (left_x + left_w, ly), ing.amount, ing_f, c["title_white"], anchor="ra")
        ly += 38

    # 左: ポイント
    ly += 18
    _text(draw, (left_x, ly), "美味しく作るポイント", gothic(36), c["title_gold"])
    ly += 48
    pt_h = gothic(28)
    pt_d = gothic(24)
    for p in recipe.points:
        _check(draw, left_x, ly + 4, 28)
        _text(draw, (left_x + 42, ly), p.headline, pt_h, c["title_white"])
        ly += 38
        for line in _wrap(draw, p.detail, pt_d, left_w - 42):
            _text(draw, (left_x + 42, ly), line, pt_d, c["body_text"])
            ly += 32
        ly += 8

    # 右: 作り方（手順＋工程写真）
    ry = col_top
    _text(draw, (right_x, ry), "作り方", gothic(40), c["title_gold"])
    ry += 50
    draw.line([(right_x, ry), (right_x + right_w, ry)], fill=c["accent_line"], width=2)
    ry += 16
    thumb = 132
    num_f = gothic(34)
    st_title_f = gothic(28)
    st_detail_f = gothic(23)
    text_w = right_w - thumb - 16
    for i, (st, im) in enumerate(zip(recipe.steps, steps), start=1):
        row_y = ry
        img.paste(im.resize((thumb, thumb)), (right_x + right_w - thumb, row_y))
        _text(draw, (right_x, row_y), f"{i:02d}", num_f, c["title_gold"])
        _text(draw, (right_x + 56, row_y + 4), st.title, st_title_f, c["title_white"])
        ty = row_y + 42
        for line in _wrap(draw, st.detail, st_detail_f, text_w):
            _text(draw, (right_x, ty), line, st_detail_f, c["body_text"])
            ty += 30
        ry = max(ty, row_y + thumb) + 16

    # 下: ひと工夫
    if recipe.extra_tip:
        ty = max(ly, ry) + 6
        if ty < H - 150:
            box_b = min(H - 30, ty + 130)
            _panel(draw, [40, ty, W - 40, box_b], c["card_panel"], outline=c["accent_line"], width=2)
            _text(draw, (62, ty + 18), "＋ ひと工夫でさらに美味しく！", gothic(30), c["title_gold"])
            tipy = ty + 60
            for line in _wrap(draw, recipe.extra_tip, gothic(26), W - 140):
                _text(draw, (62, tipy), line, gothic(26), c["body_text"])
                tipy += 34

    return img


# --- まとめ ---------------------------------------------------------------

def generate_post_images(plan: PostPlan, recipe: Recipe, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    hero = hero_image(recipe)
    steps = [step_image(recipe, s.title, s.detail) for s in recipe.steps]

    cover = render_cover(recipe, hero)
    card = render_card(recipe, hero, steps)

    p1 = out_dir / "slide_01_cover.jpg"
    p2 = out_dir / "slide_02_recipe.jpg"
    cover.save(p1, quality=92)
    card.save(p2, quality=92)
    return [p1, p2]
