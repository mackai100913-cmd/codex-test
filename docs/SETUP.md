# セットアップ手順（5分・あなたの作業はほぼゼロ）

このシステムは **APIキーが無くてもデモ画像で動作確認できます**。
実際の料理写真を生成するには Gemini のキー（無料枠あり）だけ取得してください。

## 1. Gemini APIキーを取得（無料）

1. https://aistudio.google.com/apikey にアクセス（Googleアカウントでログイン）
2. **「Create API key」** をクリック
3. 表示されたキー（`AIza...`）をコピー

> これがあなたが行う唯一の必須作業です。あとは全自動。

## 2. キーを設定

```bash
cp .env.example .env
# .env を開いて GEMINI_API_KEY=コピーしたキー を貼り付け
```

## 3. 依存をインストール

```bash
pip install -r requirements.txt
```

## 4. 実行（投稿パッケージ生成）

```bash
python run.py            # 今日の投稿を自動生成
python run.py --count 3  # 3件生成
```

`output/<日付_番号>/` に以下が出力されます：

- `slide_01〜05.jpg` … 文字焼き込み済みの投稿画像
- `caption.txt` … 本文＋ハッシュタグ（コピペで完成）
- `README.txt` … TikTokへのアップロード手順
- `post.json` … メタ情報

## 5. TikTokへ投稿

スマホに `output/<該当フォルダ>` を送り、`README.txt` の通り
画像を順に選んで `caption.txt` を貼るだけ（1〜2分）。

> 完全な自動アップロード（TikTok Content Posting API）は、TikTok側の
> アプリ審査とアクセストークン取得が必要です。希望があれば次段階として
> 実装できます（`docs/STRATEGY.md` 参照）。

## 料金の目安（Gemini 3 Pro Image / Nano Banana Pro）

- 1K〜2K画像: 約 $0.13 / 枚、4K: 約 $0.24 / 枚
- 1投稿5枚 × 1日2投稿 = 約 $1.3/日（1K〜2K時）
- コストを抑えたい場合は `.env` の `GEMINI_IMAGE_MODEL` を
  `gemini-2.5-flash-image-preview` に変更
