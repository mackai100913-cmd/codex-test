# 🍳 グルメ（レシピ）TikTok 完全自動コンテンツ生成パイプライン

ロールモデル [`@buzz_meshi`](https://www.tiktok.com/@buzz_meshi) 系の
**バズるレシピ投稿**を、企画から画像・文言まで全自動生成します。
あなたの作業は「生成された画像と本文をTikTokに貼るだけ」。

> **ゴール: グルメTikTokアカウントのフォロワー 20万人**

## 投稿フォーマット（実際のバズ投稿を分析して再現）

- **1枚目＝表紙**: 暗背景の料理写真＋金色サブタイトル＋白い大きな料理名（明朝）＋
  決めワードを赤で強調した導入文
- **2枚目＝レシピカード**: ヒーロー写真＋調理時間/費用/難易度＋材料＋
  美味しく作るポイント＋手順01〜06（各工程写真付き）
- **本文**: 材料・手順を全文掲載＋レシピ系ハッシュタグ（保存されやすい型）

## できること

- 🧠 **企画自動生成** … 料理コンセプトを日替わりで選定
- 📝 **レシピ自動生成** … 材料・手順・コツ・調理時間/費用/難易度を生成（Gemini or 内蔵サンプル）
- 🎨 **画像自動生成** … **Gemini 3 Pro Image（Nano Banana Pro）** でリアルな料理写真
- 🖼️ **TikTok仕様に合成** … 9:16の表紙・レシピカードを自動レイアウト
- ✍️ **本文自動生成** … レシピ全文＋ハッシュタグ
- 📦 **アップロード用パッケージ化** … 画像＋`caption.txt`＋手順を1フォルダに
- 🗓️ **毎日自動実行** … GitHub Actions で日次生成

## クイックスタート

```bash
pip install -r requirements.txt
sudo apt-get install -y fonts-ipafont-gothic fonts-ipafont-mincho  # 日本語フォント
python run.py            # 投稿パッケージを生成
```

### 画像の2モード
- **モードB（無料・現在の設定）**: 料理写真は **Geminiアプリ**（Pro契約の範囲・API課金なし）で
  あなたが作成 → システムが表紙・レシピカードに自動合成。
  各フォルダの `画像作成ガイド.txt` のプロンプトをアプリに貼って画像を作り、
  `素材` フォルダに入れて `python run.py --build` を実行するだけ。
- **モードA（全自動）**: Gemini APIで料理写真も自動生成（要 請求の有効化）。
  `.env` の `GEMINI_IMAGE_ENABLED=true` で切替。

→ 詳しい手順は [`docs/SETUP.md`](docs/SETUP.md)

### 🧑‍⚖️ デザイン責任者（画像の品質審査）
AIが料理写真を採点し、合格ライン（既定70点）と要望（指定の料理か・本物感・シズル感・
暗背景の世界観・文字無し）を満たすか審査します。不合格なら改善要望と
「作り直し用プロンプト」を返すので、品質を一定以上に保てます。

```bash
python run.py --review            # 素材の hero 写真を審査
python run.py --review 2026-06-15_01   # 投稿を指定して審査
```
`python run.py --build` 時にも自動で審査し、結果を各フォルダの
`審査結果.txt` に保存します。合格ラインは `config/persona.yaml` の
`quality.pass_score` で調整できます。

## 出力イメージ

```
output/
├── 2026-06-14_01/
│   ├── slide_01_cover.jpg    # 表紙
│   ├── slide_02_recipe.jpg   # レシピカード
│   ├── caption.txt           # 本文（材料・手順全文＋ハッシュタグ）
│   ├── post.json             # メタ情報
│   └── README.txt            # アップロード手順
└── calendar_2026-06-14.md    # その日の投稿一覧
```

## カスタマイズ

| 編集ファイル | 内容 |
|---|---|
| `config/persona.yaml` | アカウント名・世界観・配色・ハッシュタグ・投稿時間 |
| `config/content_themes.yaml` | 料理コンセプト・フォールバック用サンプルレシピ |
| `.env` | APIキー・使用モデル・1日の投稿数 |

## 構成

```
run.py                         # CLIエントリ
src/
├── config.py                  # 設定・環境変数の読み込み
├── content_planner.py         # 企画（料理コンセプトの選定）
├── recipe_generator.py        # レシピ生成（Gemini or サンプル）
├── image_generator.py         # 画像生成＋表紙・レシピカード合成
├── caption.py                 # 本文生成
├── packager.py                # アップロード用パッケージ化
└── pipeline.py                # 全体オーケストレーション
.github/workflows/daily-content.yml  # 毎日自動生成
docs/SETUP.md                  # セットアップ
docs/STRATEGY.md               # 20万フォロワー戦略
```

## 戦略

ロールモデルから抽出した「勝ちパターン」と成長ロードマップ、
そして「AIっぽさを避けてリアルに見せる」重要性は
[`docs/STRATEGY.md`](docs/STRATEGY.md) を参照。

---
※ 完全自動アップロード（TikTok API連携）や動画化は次段階の拡張として実装可能です。
