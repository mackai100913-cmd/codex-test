#!/usr/bin/env python3
"""グルメTikTok 自動投稿パッケージ生成 CLI。

使い方:
    python run.py                # 今日の投稿を設定数だけ生成
    python run.py --count 3      # 件数指定
    python run.py --date 2026-06-20
"""

from __future__ import annotations

import argparse
from datetime import date

from src.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="グルメTikTok自動コンテンツ生成")
    parser.add_argument("--count", type=int, default=None, help="生成する投稿数")
    parser.add_argument("--date", type=str, default=None, help="対象日 YYYY-MM-DD")
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else None
    run(n=args.count, target_date=target)


if __name__ == "__main__":
    main()
