"""投稿ネタ（コンテンツプラン）を自動生成する。

content_themes.yaml の「切り口 × 料理 × エリア × 価格帯」を組み合わせ、
重複しにくいように日付シードでローテーションさせる。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from . import config


@dataclass
class PostPlan:
    """1投稿分の企画。copywriter / image_generator の入力になる。"""

    post_id: str
    angle_id: str
    angle_label: str
    hook_template: str
    dish: str
    area: str
    price_band: str
    scheduled_time_jst: str
    extras: dict[str, Any] = field(default_factory=dict)


def _seeded_rng(seed_key: str) -> random.Random:
    return random.Random(seed_key)


def plan_posts(
    n: int | None = None,
    target_date: date | None = None,
) -> list[PostPlan]:
    """指定日に投稿する n 件の企画を返す。"""
    persona = config.persona()
    themes = config.themes()

    n = n or config.posts_per_run()
    target_date = target_date or datetime.now().date()

    angles = themes["angles"]
    dishes = themes["dishes"]
    areas = themes["areas"]
    price_bands = themes["price_bands"]
    best_times = persona["schedule"]["best_times_jst"]

    plans: list[PostPlan] = []
    for i in range(n):
        # 日付＋連番でシードし、毎日違う組み合わせになるようにする
        rng = _seeded_rng(f"{target_date.isoformat()}::{i}")
        angle = rng.choice(angles)
        dish = rng.choice(dishes)
        area = rng.choice(areas)
        price = rng.choice(price_bands)
        hook = rng.choice(angle["hook_templates"])
        slot = best_times[i % len(best_times)]

        plans.append(
            PostPlan(
                post_id=f"{target_date.isoformat()}_{i + 1:02d}",
                angle_id=angle["id"],
                angle_label=angle["label"],
                hook_template=hook,
                dish=dish,
                area=area,
                price_band=price,
                scheduled_time_jst=slot,
                extras={"limited_count": rng.choice([10, 20, 30, 50])},
            )
        )
    return plans
