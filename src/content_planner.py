"""投稿の企画（どの料理を・いつ出すか）を自動生成する。

content_themes.yaml の dish_ideas から、日付シードで日替わりに選ぶ。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime

from . import config


@dataclass
class PostPlan:
    post_id: str
    dish_idea: str
    scheduled_time_jst: str
    seed: str


def plan_posts(n: int | None = None, target_date: date | None = None) -> list[PostPlan]:
    persona = config.persona()
    themes = config.themes()

    n = n or config.posts_per_run()
    target_date = target_date or datetime.now().date()

    dish_ideas = themes["dish_ideas"]
    best_times = persona["schedule"]["best_times_jst"]

    # その日のお題を重複なく選ぶ
    day_rng = random.Random(target_date.isoformat())
    chosen = day_rng.sample(dish_ideas, k=min(n, len(dish_ideas)))

    plans: list[PostPlan] = []
    for i, dish in enumerate(chosen):
        plans.append(
            PostPlan(
                post_id=f"{target_date.isoformat()}_{i + 1:02d}",
                dish_idea=dish,
                scheduled_time_jst=best_times[i % len(best_times)],
                seed=f"{target_date.isoformat()}::{i}::{dish}",
            )
        )
    return plans
