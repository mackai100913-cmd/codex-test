"""アップロード用パッケージを書き出す。

各投稿ごとに output/<post_id>/ を作り、
- 表紙画像 / レシピカード画像
- caption.txt（材料・手順・ハッシュタグの全文 ＝ コピペでそのまま投稿）
- post.json（メタ情報）
- README.txt（アップロード手順）
を生成する。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from . import config
from .caption import build_caption
from .content_planner import PostPlan
from .image_generator import generate_post_images
from .recipe_generator import Recipe


def build_package(plan: PostPlan, recipe: Recipe, root: Path | None = None) -> Path:
    root = root or config.OUTPUT_DIR
    post_dir = root / plan.post_id
    post_dir.mkdir(parents=True, exist_ok=True)

    images = generate_post_images(plan, recipe, post_dir)

    (post_dir / "caption.txt").write_text(build_caption(recipe), encoding="utf-8")

    meta = {
        "post_id": plan.post_id,
        "dish": f"{recipe.title_top}{recipe.title_main}",
        "scheduled_time_jst": plan.scheduled_time_jst,
        "time": recipe.time,
        "cost": recipe.cost,
        "difficulty": recipe.difficulty,
        "hashtags": recipe.hashtags,
        "images": [p.name for p in images],
    }
    (post_dir / "post.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    instructions = (
        f"=== {plan.post_id} アップロード手順 ===\n\n"
        f"投稿推奨時刻(JST): {plan.scheduled_time_jst}\n\n"
        "1. TikTokアプリ → ＋ → 「写真」を選択\n"
        "2. slide_01_cover（表紙）→ slide_02_recipe（レシピ）の順で追加\n"
        "3. caption.txt の中身を本文にコピペ（ハッシュタグ込み）\n"
        "4. カバーは slide_01 を選択\n"
        "5. 推奨時刻に投稿（または予約投稿）\n"
    )
    (post_dir / "README.txt").write_text(instructions, encoding="utf-8")
    return post_dir


def write_calendar(plans: list[PostPlan], recipes: list[Recipe], target_date: date,
                   root: Path | None = None) -> Path:
    root = root or config.OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    lines = [f"# 投稿カレンダー {target_date.isoformat()}", ""]
    for plan, recipe in zip(plans, recipes):
        lines += [
            f"## {plan.scheduled_time_jst}  {recipe.title_top}{recipe.title_main}",
            f"- フォルダ: `output/{plan.post_id}/`",
            f"- 調理時間: {recipe.time} / 費用: {recipe.cost} / 難易度: {recipe.difficulty}",
            f"- タグ: {' '.join(recipe.hashtags)}",
            "",
        ]
    path = root / f"calendar_{target_date.isoformat()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
