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
    # Linux (IPA / Noto)
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    # macOS
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    # Windows
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]
_MINCHO = [
    # Linux (IPA)
    "/usr/share/fonts/opentype/ipafont-mincho/ipamp.ttf",
    "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-mincho.ttf",
    # macOS
    "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
    "/System/Library/Fonts/Hiragino Mincho ProN.ttc",
    # Windows
    "C:/Windows/Fonts/yumin.ttf",
    "C:/Windows/Fonts/msmincho.ttc",
    "C:/Windows/Fonts/MSMINCHO.TTC",
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
    # 明朝が見つからない環境ではゴシックで代用（豆腐文字を避ける）
    return _font(_MINCHO + _GOTHIC, size)


# --- 画像取得（Gemini or ダミー） -----------------------------------------

def _gemini_image(prompt: str, aspect: str) -> Image.Image | None:
    if not config.image_api_enabled():
        return None
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


# --- 画像生成プロンプト（Geminiアプリにそのまま貼れる） -------------------

# 参考画像に忠実な、全画像共通のブランド世界観（社長が会長のビジョンを翻訳した基準）。
BRAND_WORLD = (
    "【世界観】艶を抑えた濃い焦げ茶のオーク無垢材テーブル。背景は#0D0D0D相当の漆黒へ自然にフォールオフ。"
    "余計な小物・布・窓・他の食器・調味料は一切写さない。"
    "【ライティング】キーライトは被写体の右後方45度・やや高所からの暖色(色温度3200K前後)スポット光（バックライト気味）で"
    "湯気と食材の輪郭・照りを浮かび上がらせる。手前は黒のネガティブフィルで締め、"
    "陰影のコントラストを深く、背景はほぼ黒へ落とす。やわらかいスペキュラ・ハイライトを食材表面に乗せる。"
    "【レンズ／カメラ】フルサイズ一眼＋90〜100mmマクロ相当、絞りf/2.8〜f/4の浅い被写界深度。"
    "ピントは主役の手前エッジに置き、奥はクリーミーにボケる。ISOは低くノイズレス。"
    "自然な発色とマイクロコントラスト、フィルムライクで誇張のない色再現。"
    "【質感】料理は実写・本物の家庭料理。照りは油や煮汁由来の自然なもので人工的なテカリにしない。"
    "CG・3DCG・イラスト・レンダリング・プラスチック感・過度なHDR・過彩度は禁止。"
    "【厳禁】写真内に文字・ロゴ・透かし・ウォーターマーク・キラキラ記号(✦★等)・ボーダー・フレーム・人物・手・指を一切入れない。"
)

_APPETIZING = (
    "とにかく食欲をそそる、思わず生唾を飲むほど美味しそうに。"
    "できたての熱々感、ふわりと立ち上る湯気の筋、油・タレ・煮汁のとろみと照り(グレーズ)、"
    "断面や表面のみずみずしさ、こんがりしたメイラード由来の焼き色・焦げ目、"
    "ソースのとろみが垂れる瞬間、つやのある粒立ち——シズル感を最大限に。"
    "ただし照りは自然由来に留め、ベタついた人工的な光沢にはしない。"
)


def brand_brief() -> str:
    """生成前にGeminiへ世界観を共有し合意を取る『すり合わせメッセージ』。"""
    return (
        "これから複数の料理写真を順番に作ります。まず全画像で必ず守ってほしい"
        "『ブランドの世界観』を共有します。以後の画像は毎回これを厳守してください。\n"
        f"{BRAND_WORLD}\n"
        "【完成料理（メイン写真）】浅く平たい黒マット(無釉・マットブラック)の和食器に美しく盛る。"
        "縁の立ち上がりが低い丸皿または小判皿。器の縁・質感までシャープに見せる。"
        "フライパン・スキレット・鍋・カトラリー・箸置きは写さない。"
        "料理は皿の8割を占めるボリュームで、高低差をつけ立体的に盛る（天盛り・あしらいで頂点を作る）。"
        "皿のフチまで画面に入れ、主役を中央〜やや下に大きく。カメラは斜め30〜45度のアイレベル寄り。縦長9:16。\n"
        "【調理工程】鍋・フライパン・まな板の中身を画面中央に大きく、真俯瞰(90度)または斜め俯瞰(45度)。"
        "湯気・炒める動き・煮立ちなど臨場感を出す。背景・木目・色温度はメイン写真と完全に統一。正方形1:1。\n"
        "この方針を理解したら『了解しました』とだけ短く返答してください。まだ画像は作らないでください。"
    )


def hero_prompt(recipe: Recipe) -> str:
    dish = f"{recipe.title_top}{recipe.title_main}"
    return (
        f"共有済みのブランド世界観を厳守して「{dish}」の完成写真を作る。"
        "【器】浅く平たい黒マット(無釉マットブラック)の丸い和食器。縁の質感まで見せる。"
        "フライパン・スキレット・鍋・スプーン・フォーク・箸は絶対に写さない（完成した一皿のみ）。"
        "【盛り付け】主役の具材を皿の8割に、照り(グレーズ)とツヤを強調して高低差をつけ立体的に山高く。"
        "天盛りのあしらい(青ねぎ・白ごま・糸唐辛子・木の芽等、料理に合うもの)で頂点と色のアクセントを一点だけ添える。"
        "【ライティング】右後方からの暖色スポットで湯気と照りを逆光気味に立たせ、手前は黒で締める。"
        "【構図】料理を中央〜やや下に大きく、皿のフチまで。90〜100mmマクロ相当・f/2.8〜4の浅い被写界深度で背景を漆黒にボカす。斜め30〜45度。"
        f"{_APPETIZING}"
        f"{BRAND_WORLD}"
        "縦長(9:16)。最後にもう一度: 文字・ロゴ・透かし・人物・手・フレーム・CG感は一切無し。"
    )


def step_prompt(recipe: Recipe, step_title: str, detail: str) -> str:
    return (
        f"共有済みのブランド世界観を厳守して、料理「{recipe.title_main}」の"
        f"調理工程「{step_title}」の写真を作る。{detail} "
        "【構図】調理中の鍋・フライパン・まな板の中身を画面中央に大きく。"
        "真俯瞰(90度)または斜め俯瞰(45度)で、炒める・煮立つ・和える等の今まさに調理している臨場感を出す。"
        "【ライティング・色】メイン写真と同一の暖色スポット光・漆黒背景・濃い焦げ茶の木目で色温度まで完全統一。"
        "湯気や食材の照りを逆光気味に立たせる。"
        f"{_APPETIZING}"
        f"{BRAND_WORLD}"
        "正方形(1:1)。文字・ロゴ・透かし・人物の顔は写さない（手元が必要な場合も顔は入れない）。"
    )


def steps_grid_prompt(recipe: Recipe) -> str:
    """6つの調理工程を「1枚の画像」に格子状(縦3段×横2列)でまとめて作るプロンプト。

    会長要望: 工程は6枚バラではなく1枚にまとめる。文字は入れず(あとでPythonが
    綺麗に重ねる)、6コマの写真だけを整然と並べる。
    """
    steps = recipe.steps[:6]
    items = "／".join(f"{i}.{s.title}（{s.detail}）" for i, s in enumerate(steps, start=1))
    n = len(steps)
    return (
        f"共有済みのブランド世界観を厳守して、料理「{recipe.title_main}」の調理工程を"
        f"【1枚の画像】にまとめて作る。縦3段×横2列の整然とした格子状に{n}コマを並べる。"
        "並び順は必ず左上から右へ、上段→中段→下段（1,2／3,4／5,6）。"
        "各コマは均等な大きさで、コマ間にごく細い余白(黒)を入れて区切る。"
        f"各コマの内容（この順番で）: {items}。"
        "各コマは鍋・フライパン・まな板の中身を真俯瞰(90度)または斜め俯瞰(45度)で大きく写し、"
        "炒める・煮立つ・和える等の調理中の臨場感を出す。"
        "全コマで暗背景・暖色スポット光・濃い焦げ茶の木目・色温度を完全に統一する。"
        f"{_APPETIZING}"
        f"{BRAND_WORLD}"
        "【最重要】コマの中にも外にも、番号・文字・ロゴ・枠線・キラキラ記号は一切入れない"
        "（写真を格子に並べるだけ）。全体は縦長(3:4)。"
    )


def _slice_grid(img: Image.Image, rows: int = 3, cols: int = 2, n: int | None = None) -> list[Image.Image]:
    """グリッド画像を rows×cols のセルに等分し、左上→右の読み順で返す。"""
    w, h = img.size
    cw, ch = w // cols, h // rows
    cells: list[Image.Image] = []
    for r in range(rows):
        for c in range(cols):
            cells.append(img.crop((c * cw, r * ch, c * cw + cw, r * ch + ch)))
    return cells if n is None else cells[:n]



# --- 素材（ユーザー提供画像）の読み込み -----------------------------------

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _find_asset(assets_dir: Path | None, *basenames: str) -> Image.Image | None:
    """assets_dir から basename(拡張子なし)に一致する画像を探して読む。

    二重拡張子(hero.jpg.png 等)や大文字拡張子にも対応するため、
    完全一致 → base.* のglob、の順で探す。
    """
    if not assets_dir or not assets_dir.exists():
        return None
    # 1) 完全一致（拡張子あり/なし問わず）
    for base in basenames:
        for ext in ("",) + _IMG_EXTS:
            p = assets_dir / f"{base}{ext}"
            if p.exists() and p.is_file():
                img = _try_open(p)
                if img:
                    return img
    # 2) base で始まるファイル（hero.jpg.png や HERO.JPG なども拾う）
    for base in basenames:
        for p in sorted(assets_dir.glob(f"{base}.*")) + sorted(assets_dir.glob(f"{base.upper()}.*")):
            if p.is_file():
                img = _try_open(p)
                if img:
                    return img
    return None


def _try_open(p: Path) -> Image.Image | None:
    try:
        return Image.open(p).convert("RGB")
    except Exception:
        return None


def hero_image(recipe: Recipe, assets_dir: Path | None = None) -> Image.Image:
    img = (_find_asset(assets_dir, "hero", "hero1", "01_hero")
           or _gemini_image(hero_prompt(recipe), "9:16")
           or _dummy_food(W, H, recipe.title_main))
    return _cover_resize(img, W, H)


def step_image(recipe: Recipe, idx: int, step_title: str, detail: str,
               assets_dir: Path | None = None) -> Image.Image:
    img = (_find_asset(assets_dir, f"step_{idx}", f"step{idx}", f"{idx:02d}_step", f"{idx:02d}")
           or _gemini_image(step_prompt(recipe, step_title, detail), "1:1")
           or _dummy_food(400, 400, step_title))
    return _cover_resize(img, 400, 400)


def steps_grid_raw(recipe: Recipe, assets_dir: Path | None = None) -> Image.Image | None:
    """6工程を1枚にまとめたグリッド画像を取得（素材 or Gemini）。無ければ None。"""
    return (_find_asset(assets_dir, "steps", "steps_grid", "grid", "工程")
            or _gemini_image(steps_grid_prompt(recipe), "3:4"))


def step_images(recipe: Recipe, assets_dir: Path | None = None) -> list[Image.Image]:
    """レシピカード用の工程サムネ6枚を返す。

    優先順位:
      1) 1枚にまとめたグリッド画像(素材steps.* / Gemini) → 6分割して使用（会長方式）
      2) 個別の step_1〜6（素材 / Gemini / ダミー）→ 後方互換
    """
    n = len(recipe.steps)
    grid = steps_grid_raw(recipe, assets_dir)
    if grid is not None:
        rows = (n + 1) // 2 if n else 3
        cells = _slice_grid(grid, rows=max(rows, 1), cols=2, n=n)
        return [_cover_resize(c, 400, 400) for c in cells]
    return [step_image(recipe, i, s.title, s.detail, assets_dir)
            for i, s in enumerate(recipe.steps, start=1)]


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

def _cover_badge(img, draw, y, recipe, cfg):
    """表紙に『調理時間・人数・難易度』の情報バッジを上品に置く（保存率UPの数字訴求）。"""
    font = gothic(32)
    segs = [f"調理 {recipe.time}",
            f"{recipe.servings}",
            f"難易度 {'★' * recipe.difficulty}{'☆' * (5 - recipe.difficulty)}"]
    pad_x, pad_y, gap = 34, 16, 36
    widths = [draw.textlength(s, font=font) for s in segs]
    inner = sum(widths) + gap * (len(segs) - 1)
    box_w = int(inner + pad_x * 2)
    box_h = int(font.size + pad_y * 2)
    x0 = (W - box_w) // 2

    ov = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=box_h // 2,
                         fill=(0, 0, 0, 150), outline=cfg["title_gold"], width=2)
    img.paste(ov, (x0, int(y)), ov)

    tx = x0 + pad_x
    ty = y + pad_y
    for i, (s, w) in enumerate(zip(segs, widths)):
        if i > 0:
            dvx = tx - gap / 2
            draw.line([(dvx, y + 12), (dvx, y + box_h - 12)], fill=cfg["title_gold"], width=1)
        _text(draw, (tx, ty), s, font, cfg["title_white"], stroke=2)
        tx += w + gap
    return y + box_h


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
    # 金の二重ヘアライン（細・極細）で高級感を底上げ
    lw = min(W - mx * 2, len(recipe.title_main) * 150)
    x0, x1 = W // 2 - lw // 2, W // 2 + lw // 2
    draw.line([(x0, y), (x1, y)], fill=d_cfg["title_gold"], width=3)
    draw.line([(x0, y + 9), (x1, y + 9)], fill=d_cfg["title_gold"], width=1)
    y += 40

    # 説明文
    desc_font = gothic(36)
    for line in _wrap(draw, recipe.description, desc_font, W - mx * 2):
        _text(draw, (mx, y), line, desc_font, d_cfg["body_text"], stroke=2)
        y += 50

    # 情報バッジ（調理時間・人数・難易度）— 1枚目で『作れそう』を即訴求し保存を促す
    _cover_badge(img, draw, y + 16, recipe, d_cfg)

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

    # ヒーロー写真と情報パートを分ける金のセパレータ
    draw.line([(0, top_h), (W, top_h)], fill=c["title_gold"], width=2)

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

def generate_post_images(plan: PostPlan, recipe: Recipe, out_dir: Path,
                         assets_dir: Path | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    hero = hero_image(recipe, assets_dir)
    steps = step_images(recipe, assets_dir)

    cover = render_cover(recipe, hero)
    card = render_card(recipe, hero, steps)

    p1 = out_dir / "slide_01_cover.jpg"
    p2 = out_dir / "slide_02_recipe.jpg"
    # 黒背景のグラデーションでバンディング(縞)が出にくいよう高品質・サブサンプリング無効で保存
    cover.save(p1, quality=95, subsampling=0)
    card.save(p2, quality=95, subsampling=0)
    return [p1, p2]
