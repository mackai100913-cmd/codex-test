"""料理コンセプトから「完全なレシピ」を生成する。

- GEMINI_API_KEY があれば Gemini テキストモデルでレシピ全体を生成。
- 無ければ content_themes.yaml の sample_recipes を使う（高品質に動作確認できる）。
返す Recipe は表紙・レシピカード・キャプションすべての元データになる。
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from . import config


@dataclass
class Ingredient:
    name: str
    amount: str


@dataclass
class Step:
    title: str       # 例: 焼く
    detail: str      # 例: フライパンに油を熱し…


@dataclass
class Point:
    headline: str    # 例: せせりは焼きすぎない
    detail: str      # 例: ぷりっとした食感を残すのがコツ！


@dataclass
class Recipe:
    title_top: str            # 金色サブタイトル（例: せせりとアスパラの）
    title_main: str           # 白い料理名（例: レモン炒め）
    intro: str                # 導入文（決めワードを含む一文）
    intro_highlight: str      # 赤で強調する決めワード（例: やみつき確定）
    description: str          # 説明文
    servings: str             # 例: 2人前
    time: str                 # 例: 約20分
    cost: str                 # 例: 約500円
    difficulty: int           # 1〜5（★の数）
    difficulty_label: str     # 例: やさしい
    ingredients: list[Ingredient]
    steps: list[Step]
    points: list[Point]
    extra_tip: str
    hashtags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ハッシュタグ
# ---------------------------------------------------------------------------

def _build_hashtags(seed: str) -> list[str]:
    cfg = config.persona()["hashtags"]
    tags = list(cfg["always"])
    rng = random.Random(seed)
    tags += rng.sample(cfg["rotating_broad"], k=min(3, len(cfg["rotating_broad"])))
    seen: list[str] = []
    for t in tags:
        if t not in seen:
            seen.append(t)
    return seen[: cfg.get("count", 8)]


# ---------------------------------------------------------------------------
# フォールバック（サンプルレシピ）
# ---------------------------------------------------------------------------

def _recipe_from_dict(data: dict, seed: str) -> Recipe:
    return Recipe(
        title_top=data["title_top"],
        title_main=data["title_main"],
        intro=data["intro"],
        intro_highlight=data.get("intro_highlight", ""),
        description=data["description"],
        servings=data.get("servings", "2人前"),
        time=data.get("time", "約20分"),
        cost=data.get("cost", "約500円"),
        difficulty=int(data.get("difficulty", 2)),
        difficulty_label=data.get("difficulty_label", "やさしい"),
        ingredients=[Ingredient(**i) for i in data["ingredients"]],
        steps=[Step(**s) for s in data["steps"]],
        points=[Point(**p) for p in data["points"]],
        extra_tip=data.get("extra_tip", ""),
        hashtags=_build_hashtags(seed),
    )


def _sample_recipe(dish_idea: str, seed: str) -> Recipe:
    samples = config.themes().get("sample_recipes", [])
    rng = random.Random(seed)
    data = rng.choice(samples) if samples else None
    if data is None:
        raise RuntimeError("sample_recipes が空です。content_themes.yaml を確認してください。")
    return _recipe_from_dict(data, seed)


# ---------------------------------------------------------------------------
# Gemini によるレシピ生成
# ---------------------------------------------------------------------------

def _gemini_recipe(dish_idea: str, seed: str) -> Recipe | None:
    api_key = config.gemini_api_key()
    if not api_key:
        return None
    try:
        from google import genai
    except Exception:
        return None

    n_steps = config.step_count()
    prompt = f"""あなたは日本の人気レシピTikTokの料理家兼コピーライターです。
お題「{dish_idea}」について、家庭で作れる本格的で美味しいレシピを作ってください。
分量・手順は実際に作れる現実的な内容にしてください。

# 出力（必ず JSON のみ。前後に説明文やマークダウン記号を付けない）
{{
  "title_top": "金色サブタイトル(主役食材など・例: せせりとアスパラの)",
  "title_main": "白い大きな料理名(短く・例: レモン炒め)",
  "intro": "導入の一文(決めワードを含む・40文字程度)",
  "intro_highlight": "introの中で赤強調する決めワード(例: やみつき確定)",
  "description": "味の魅力を伝える説明(60文字程度)",
  "servings": "2人前",
  "time": "約NN分",
  "cost": "約NNN円",
  "difficulty": 2,
  "difficulty_label": "やさしい",
  "ingredients": [{{"name":"材料名","amount":"分量"}}],
  "steps": [{{"title":"工程名(短い)","detail":"手順の説明"}}],
  "points": [{{"headline":"コツの見出し","detail":"補足"}}],
  "extra_tip": "ひと工夫でさらに美味しくする一言"
}}
# 制約
- ingredients は 8〜13 個
- steps はちょうど {n_steps} 個
- points は 4〜5 個
- difficulty は 1〜5 の整数
"""
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=config.text_model(),
            contents=prompt,
        )
        text = (resp.text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{"): text.rfind("}") + 1]
        data = json.loads(text)
        return _recipe_from_dict(data, seed)
    except Exception:
        return None


def generate_recipe(dish_idea: str, seed: str) -> Recipe:
    """お題から完全なレシピを生成。Gemini → 失敗時サンプル。"""
    return _gemini_recipe(dish_idea, seed) or _sample_recipe(dish_idea, seed)
