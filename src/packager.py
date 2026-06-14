"""アップロード用パッケージを書き出す。

各投稿ごとに output/<post_id>/ を作り、
- 画像スライド（slide_*.jpg）
- caption.txt（本文＋ハッシュタグ ＝ コピペでそのまま投稿可）
- post.json（メタ情報）
- README.txt（アップロード手順）
を生成する。スマホで開いて1タップ投稿できる状態にするのが目的。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import config
from .content_planner import PostPlan
from .copywriter import Copy
from .image_generator import generate_images


def _caption_text(copy: Copy) -> str:
    tags = " ".join(copy.hashtags)
    return f"{copy.caption}\n\n{tags}\n"


def build_package(plan: PostPlan, copy: Copy, root: Path | None = None) -> Path:
    root = root or config.OUTPUT_DIR
    post_dir = root / plan.post_id
    post_dir.mkdir(parents=True, exist_ok=True)

    images = generate_images(plan, copy, post_dir)

    (post_dir / "caption.txt").write_text(_caption_text(copy), encoding="utf-8")

    meta = {
        "post_id": plan.post_id,
        "angle": plan.angle_label,
        "dish": plan.dish,
        "area": plan.area,
        "price_band": plan.price_band,
        "scheduled_time_jst": plan.scheduled_time_jst,
        "title": copy.title,
        "hashtags": copy.hashtags,
        "images": [p.name for p in images],
        "slide_count": len(images),
    }
    (post_dir / "post.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    instructions = (
        f"=== {plan.post_id} アップロード手順 ===\n\n"
        f"投稿推奨時刻(JST): {plan.scheduled_time_jst}\n\n"
        "1. TikTokアプリ → ＋ → 「写真」を選択\n"
        f"2. このフォルダの slide_01〜slide_{len(images):02d} を順番に追加\n"
        "3. caption.txt の中身を本文にコピペ（ハッシュタグ込み）\n"
        "4. カバーは slide_01 を選択\n"
        "5. 推奨時刻に投稿（または予約投稿）\n"
    )
    (post_dir / "README.txt").write_text(instructions, encoding="utf-8")
    return post_dir


def write_calendar(plans: list[PostPlan], copies: list[Copy], target_date: date,
                   root: Path | None = None) -> Path:
    """その日の投稿一覧（カレンダー）を Markdown で書き出す。"""
    root = root or config.OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    lines = [f"# 投稿カレンダー {target_date.isoformat()}", ""]
    for plan, copy in zip(plans, copies):
        lines += [
            f"## {plan.scheduled_time_jst}  {copy.title}",
            f"- フォルダ: `output/{plan.post_id}/`",
            f"- 切り口: {plan.angle_label} / 料理: {plan.dish} / エリア: {plan.area}",
            f"- タグ: {' '.join(copy.hashtags)}",
            "",
        ]
    path = root / f"calendar_{target_date.isoformat()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
