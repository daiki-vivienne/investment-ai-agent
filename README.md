# Investment AI Agent

決算PDFを読み込み、AIで投資家目線の分析レポートをMarkdownとして保存するCLIアプリです。

Ver0.1では、1つのPDFを読み込んでレポートを作成する最小構成にしています。自動売買はまだ実装していません。

## セットアップ手順

1. Python 3.10以上を用意します。

2. このフォルダで仮想環境を作成します。

```powershell
python -m venv .venv
```

3. 仮想環境を有効化します。

```powershell
.venv\Scripts\Activate.ps1
```

4. 必要なライブラリをインストールします。

```powershell
pip install -r requirements.txt
```

## .envの作り方

`.env.example` をコピーして `.env` を作ります。

```powershell
Copy-Item .env.example .env
```

`.env` を開き、`OPENAI_API_KEY` に自分のOpenAI APIキーを設定します。

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

APIキーは秘密情報です。GitHubなどに公開しないでください。

## PDFの置き場所

分析したい決算PDFは、以下のフォルダに置くと管理しやすいです。

```text
data/pdfs/
```

例:

```text
data/pdfs/sample_financial_report.pdf
```

## 実行方法

PDFファイルのパスを指定して実行します。

```powershell
python main.py data/pdfs/sample_financial_report.pdf
```

保存先フォルダを変えたい場合は、`--output-dir` を使います。

```powershell
python main.py data/pdfs/sample_financial_report.pdf --output-dir data/reports
```

## 出力されるレポートの場所

初期設定では、Markdownレポートは以下に保存されます。

```text
data/reports/
```

ファイル名には、元PDF名と作成日時が入ります。

```text
sample_financial_report_analysis_20260604_120000.md
```

## 出力される分析項目

このアプリは単なる要約ではなく、投資家目線で以下の項目を出力します。

- 会社概要
- 業績サマリー
- ポジティブ要因
- リスク要因
- 半導体・AI観点の分析
- 今後注目すべき指標
- 初心者向け解説
- 投資メモ
- AIスコア

AIスコアでは、成長性、収益性、財務健全性、将来性を0〜100点で出し、それぞれの理由も説明します。

## Ver3.0 データ取得調査

投資判断支援に必要なデータをどこから取得できるか、調査結果を以下にまとめています。

[docs/data_source_research.md](C:/Users/draqu/Desktop/vivienne-qa-lab/investment_ai_agent/docs/data_source_research.md)

キオクシア `285A.T` を使ったyfinanceの試作用サンプルは以下で実行できます。

```powershell
python src/yfinance_research_sample.py
```

J-Quants APIの調査結果は以下にまとめています。

[docs/jquants_research.md](C:/Users/draqu/Desktop/vivienne-qa-lab/investment_ai_agent/docs/jquants_research.md)

J-Quantsの調査用サンプルは以下で実行できます。

J-Quants V2を使う場合は、`.env` に `JQUANTS_API_KEY` を設定してください。

```env
JQUANTS_API_KEY=your_api_key_here
```

```powershell
python src/jquants_research_sample.py
```

## Ver3.0 期間整合性チェック

Ver3.0では、PDFから決算期を推測しません。

ユーザーがCLIで指定した決算期を正として扱い、J-Quants APIから同じ期間のstatementを探します。

```powershell
python main.py data/pdfs/kioxia260515_1.pdf --stock-code 285A --period-type FY --fiscal-year-end 2026-03-31
```

期間が一致した場合のみ、J-Quants由来の売上、営業利益、純利益、EPSを正式データ候補として表示します。

期間が一致しない場合は、APIデータが取れていても「参考データ」として表示し、分析やPER計算には使いません。

PER分析では、yfinanceの現在株価と、ユーザー指定期間に一致したJ-Quants正式EPSだけを使います。J-Quants正式EPSが未取得の場合、PERは計算しません。

表示名は「現在株価ベースの実績PER」とします。株価は現在時点、EPSは指定決算期の実績値であり、同じ日付同士の比較ではないためです。

無料プランや契約プランの取得可能期間外とJ-Quantsが返した場合は、Markdownの「期間整合性チェック」セクションに表示します。

API正式データが未取得の場合、AI本文でも売上・利益・EPSを正式データとして断定せず、AIスコアも点数ではなく「未取得」として扱います。

また、PDF上に「過去最高」「大幅増加」などの表現があっても、API正式データが未取得の場合は、本文の分析根拠には使いません。PDF上の記述は参考情報として分けて表示します。

Ver3.0では、API正式データが未取得の場合、AI本文にPDF内の具体的な数値を転記しません。AIがPDF内の数値対応を読み間違える可能性があるためです。

API正式業績サマリーはAIに書かせず、J-Quants正式データからコードで機械的に生成します。AI本文では売上、営業利益、純利益、EPSを再解釈しません。

さらに、AI本文にPDF由来の定量評価表現が混ざった場合に備えて、出力後の安全フィルタで該当セクションを保守的な固定文へ差し替えます。

### Ver3.0のスコープ

- yfinanceで取得できるデータの調査
- J-Quants V2 `/v2/fins/summary` の調査
- J-Quants無料プランの取得可能期間制限の確認
- ユーザー指定の決算期でAPIデータを検索
- PDFとAPIの期間が一致しない場合は、正式分析に使わない

### なぜ期間一致を必須にするのか

PDFが通期決算なのに、API側が3Q累計のデータだと、売上・利益・EPSの比較がズレます。

投資判断支援ツールでは、数字が取れることよりも「同じ期間の数字か」を確認することが重要です。

## 将来拡張できるポイント

- 株価取得: 証券コードを入力し、現在株価や過去チャートを取得する
- ニュース取得: 決算後のニュースや市場反応を取得する
- スコアリング強化: AIスコアだけでなく、財務指標を使ったルールベースの点数も追加する
- Discord通知: 作成したレポートや重要イベントをDiscordへ送る
- 複数PDF対応: フォルダ内のPDFをまとめて分析する
- 分割要約: 長いPDFをページごとに要約してから全体分析する
- 半自動売買/自動売買: 十分に検証してから、別モジュールとして慎重に追加する

## 注意点

このアプリが作る内容は、投資助言ではなく学習・調査用の分析メモです。実際の投資判断は、自分で追加調査をしたうえで行ってください。
