# 🍜 グルメTikTok 完全自動コンテンツ生成パイプライン

ロールモデル [`@buzz_meshi`](https://www.tiktok.com/@buzz_meshi) のような
**バズ飯系グルメ投稿**を、企画から画像・文言まで全自動生成します。
あなたの作業は「生成された画像と本文をTikTokに貼るだけ」。

> **ゴール: グルメTikTokアカウントのフォロワー 20万人**

## できること

- 🧠 **企画自動生成** … 「切り口 × 料理 × エリア × 価格帯」を日替わりで生成
- ✍️ **文言自動生成** … フック・各スライドの焼き込み文字・本文・ハッシュタグ
- 🎨 **画像自動生成** … **Gemini 3 Pro Image（Nano Banana Pro）** でシズル感のある料理画像
- 🖼️ **TikTok仕様に加工** … 9:16・極太フチ文字を自動で焼き込み
- 📦 **アップロード用パッケージ化** … 画像＋`caption.txt`＋手順を1フォルダに
- 🗓️ **毎日自動実行** … GitHub Actions で日次生成（`output/` を受け取るだけ）

## クイックスタート

```bash
pip install -r requirements.txt
python run.py            # APIキー無しでもデモ画像で動作確認できます
```

実際の料理写真を生成するには **Gemini APIキー（無料）** を取得して `.env` に設定するだけ。
→ 手順は [`docs/SETUP.md`](docs/SETUP.md)

## 出力イメージ

```
output/
├── 2026-06-14_01/
│   ├── slide_01_cover.jpg   # 表紙（強いフック）
│   ├── slide_02_dish.jpg    # 料理ビジュアル
│   ├── slide_03_dish.jpg    # 断面
│   ├── slide_04_dish.jpg    # 推しポイント
│   ├── slide_05_info.jpg    # 店舗INFO
│   ├── caption.txt          # 本文＋ハッシュタグ（コピペ用）
│   ├── post.json            # メタ情報
│   └── README.txt           # アップロード手順
└── calendar_2026-06-14.md   # その日の投稿一覧
```

## カスタマイズ

| 編集ファイル | 内容 |
|---|---|
| `config/persona.yaml` | アカウント名・世界観・配色・ハッシュタグ・投稿時間 |
| `config/content_themes.yaml` | ネタの切り口・料理ジャンル・エリア・価格帯 |
| `.env` | APIキー・使用モデル・1日の投稿数 |

## 構成

```
run.py                         # CLIエントリ
src/
├── config.py                  # 設定・環境変数の読み込み
├── content_planner.py         # 企画生成
├── copywriter.py              # 文言生成（Gemini or テンプレ）
├── image_generator.py         # 画像生成＋文字焼き込み
├── packager.py                # アップロード用パッケージ化
└── pipeline.py                # 全体オーケストレーション
.github/workflows/daily-content.yml  # 毎日自動生成
docs/SETUP.md                  # セットアップ
docs/STRATEGY.md               # 20万フォロワー戦略
```

## 戦略

ロールモデルから抽出した「伸びる型」と成長ロードマップは
[`docs/STRATEGY.md`](docs/STRATEGY.md) を参照。

---
※ 完全自動アップロード（TikTok API連携）や動画化は次段階の拡張として実装可能です。
