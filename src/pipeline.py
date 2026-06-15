"""パイプライン全体のオーケストレーション。

企画 → レシピ生成 → 画像生成（表紙＋レシピカード）→ キャプション →
パッケージ化 → カレンダー出力。
"""

from __future__ import annotations

from datetime import date, datetime

from . import config
from .content_planner import plan_posts
from .packager import build_package, write_calendar
from .recipe_generator import generate_recipe


def run(n: int | None = None, target_date: date | None = None) -> list[str]:
    target_date = target_date or datetime.now().date()
    plans = plan_posts(n=n, target_date=target_date)

    recipes = []
    dirs = []
    for plan in plans:
        recipe = generate_recipe(plan.dish_idea, plan.seed)
        recipes.append(recipe)
        post_dir = build_package(plan, recipe)
        dirs.append(str(post_dir))
        title = f"{recipe.title_top}{recipe.title_main}"
        print(f"✅ {plan.post_id} | {plan.scheduled_time_jst} | {title}")
        print(f"   → {post_dir}")

    cal = write_calendar(plans, recipes, target_date)
    print(f"\n🗓  カレンダー: {cal}")

    using_gemini = bool(config.gemini_api_key())
    mode = "Gemini実画像" if using_gemini else "DEMO（ダミー画像）"
    print(f"\n画像モード: {mode}  / モデル: {config.image_model()}")
    if not using_gemini:
        print("※ 実画像にするには .env に GEMINI_API_KEY を設定してください（docs/SETUP.md）")
    return dirs
