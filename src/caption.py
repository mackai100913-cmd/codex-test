"""レシピから投稿本文（キャプション）を組み立てる。

材料・手順・ポイントを全文掲載し、最後にハッシュタグを付ける。
（保存されやすいよう本文にレシピ全文を載せるのが伸びる型）
"""

from __future__ import annotations

from .recipe_generator import Recipe


def build_caption(recipe: Recipe) -> str:
    lines: list[str] = []
    lines.append(f"{recipe.title_top}{recipe.title_main}")
    lines.append("")
    lines.append(recipe.description)
    lines.append("")

    lines.append(f"材料（{recipe.servings}）")
    for ing in recipe.ingredients:
        lines.append(f"{ing.name} … {ing.amount}")
    lines.append("")

    lines.append("作り方")
    for i, st in enumerate(recipe.steps, start=1):
        lines.append(f"{i:02d} {st.title}")
        lines.append(st.detail)
    lines.append("")

    if recipe.points:
        lines.append("美味しく作るポイント")
        for p in recipe.points:
            lines.append(f"✅ {p.headline}")
            lines.append(p.detail)
        lines.append("")

    if recipe.extra_tip:
        lines.append(f"＋ひと工夫: {recipe.extra_tip}")
        lines.append("")

    lines.append("作ったら「保存」して、ぜひ作ってみてね📌")
    lines.append("")
    lines.append(" ".join(recipe.hashtags))

    return "\n".join(lines) + "\n"
