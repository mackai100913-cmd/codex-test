"""パイプライン全体のオーケストレーション。

企画 → 文言 → 画像生成＋焼き込み → パッケージ化 → カレンダー出力。
"""

from __future__ import annotations

from datetime import date, datetime

from . import config
from .content_planner import plan_posts
from .copywriter import write_copy
from .packager import build_package, write_calendar


def run(n: int | None = None, target_date: date | None = None) -> list[str]:
    target_date = target_date or datetime.now().date()
    plans = plan_posts(n=n, target_date=target_date)

    copies = []
    dirs = []
    for plan in plans:
        copy = write_copy(plan)
        copies.append(copy)
        post_dir = build_package(plan, copy)
        dirs.append(str(post_dir))
        print(f"✅ {plan.post_id} | {plan.scheduled_time_jst} | {copy.title}")
        print(f"   → {post_dir}")

    cal = write_calendar(plans, copies, target_date)
    print(f"\n🗓  カレンダー: {cal}")

    using_gemini = bool(config.gemini_api_key())
    mode = "Gemini実画像" if using_gemini else "DEMO（ダミー画像）"
    print(f"\n画像モード: {mode}  / モデル: {config.image_model()}")
    if not using_gemini:
        print("※ 実画像にするには .env に GEMINI_API_KEY を設定してください（docs/SETUP.md）")
    return dirs
