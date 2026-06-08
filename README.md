# Investment AI Agent

決算PDFとAPI由来データを使い、投資判断材料を整理するMarkdownレポートを保存するCLIアプリです。

Ver0.2では「決算書の定性分析」を中心にしつつ、株価、EPS、PER、PBR、時価総額などの投資指標はAPIから取得する設計にしています。自動売買はまだ実装していません。

## 設計思想

PDFから売上やEPSを無理に抽出すると、脚注や予想レンジを拾って誤検知するリスクがあります。

そのため、このアプリでは以下のように役割を分けます。

```text
PDF
  ↓
定性情報の抽出とAI要約

API
  ↓
株価、EPS、PER、PBR、時価総額などの数値取得

Markdown
  ↓
PDF由来 / API由来 / AI要約 を分けて出力
```

PDFから機械的に抽出した売上・利益・EPSは、正式データとして表示しません。PER計算などにも使いません。

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

## 実行方法

PDFファイルだけでも実行できます。

```powershell
python main.py data/pdfs/sample_financial_report.pdf
```

証券コードを指定すると、yfinanceでAPI由来データを取得します。

```powershell
python main.py data/pdfs/kioxia260515_1.pdf --ticker 285A
```

日本株の場合、内部では自動で `.T` を付けます。

```text
285A → 285A.T
```

保存先フォルダを変えたい場合は、`--output-dir` を使います。

```powershell
python main.py data/pdfs/sample_financial_report.pdf --output-dir data/reports
```

## 出力されるレポート

初期設定では、Markdownレポートは以下に保存されます。

```text
data/reports/
```

レポート内では、情報源を分けて表示します。

- PDF由来の参考情報
- API由来データ
- AI要約
- 投資判断支援セクション

## PDF由来の参考情報

PDF由来セクションでは、PDFを定性情報の確認に使うことを明記します。

売上、営業利益、純利益、EPSなどは誤検知の可能性があるため、PDFから機械抽出して正式データとして表示しません。

## API由来データ

試作用として、現在は `yfinance` を使います。

取得対象の例です。

現在取得できている主な項目：
- 現在株価
- EPS
- PBR
- 時価総額

今後API拡張で取得したい項目：
- 売上
- 営業利益
- 純利益
- ROE
- 自己資本比率

PERは以下の式で計算します。

```text
実績PER = API由来の現在株価 ÷ API由来のEPS
```

API由来EPSが未取得の場合、PERは計算せず `未取得` と表示します。

現時点のyfinanceでは売上、営業利益、純利益が未取得になる場合があります。将来J-Quants APIへ差し替えることで、これらもAPI由来の正式データとして扱う想定です。

## yfinanceとJ-Quants API

株価取得処理は [src/market_data_client.py] に分離しています。

現在は試作用としてyfinanceを使っていますが、将来的にはこのファイルをJ-Quants API実装へ差し替える想定です。

## AI要約

AIはPDFから以下のような定性情報を整理します。

- 会社概要
- 主力事業
- ポジティブ要因
- リスク要因
- 半導体・AI観点の分析
- 今後注目すべき指標
- 初心者向け解説
- 投資メモ

AIには株価、EPS、PER、PBR、時価総額を推測させません。

AIには売上、営業利益、純利益、EPSをPDFから抜き出して断定させません。正式データはAPI由来データだけです。

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

## PDF由来の定量表現を断定しない理由

決算PDFには、通期、四半期、Non-GAAP、IFRS、業績予想、注記、前年比など、さまざまな数字が混ざっています。

AIがPDFを読むだけで「営業利益が過去最高」「前年比約2倍」「利益率が改善」と断定すると、どの基準の数字なのか分からず、誤解を招く可能性があります。

そのため、API由来データで未取得の項目については、AI要約で定量評価を断定しません。

PDF内の定量的な記述に触れる場合は、以下のように表現します。

```text
PDF上の記述では、営業利益が改善したとされています。
```

一方で、以下のようには書きません。

```text
営業利益が過去最高です。
前年比で約2倍です。
利益率が改善しています。
```

業績サマリーでは、API未取得の項目は `API未取得` と表示し、PDF上の記述は別枠の `PDF上の主な記述` に分けます。

## データ取得元候補

将来的には、以下のようなデータ取得元との連携を検討できます。

- 株価データ: yfinance、J-Quants API、Yahoo Finance、Alpha Vantage、証券会社API
- 財務データ: J-Quants API、EDINET、TDnet、企業IR、決算短信、有価証券報告書
- アナリスト目標株価: 証券会社レポート、金融情報端末、公開ニュース
- 市場規模データ: 調査会社レポート、業界団体レポート、企業IR資料
- ニュースデータ: Google News、News API、各種メディア

## 将来の拡張計画

- yfinanceで試作した市場データ取得をJ-Quants APIへ差し替える
- API由来のEPS、BPS、自己資本、発行済株式数を使ってPER/PBRを安定計算する
- 市場規模データを取り込み、3年後、5年後、10年後の見通しを比較する
- 同業他社データを取り込み、自社スコアの相対評価を出す
- Discord通知で重要な分析結果を送る
- 十分な検証後に、半自動売買や自動売買の別モジュールを検討する

## 注意点

このアプリが作る内容は、投資助言ではなく学習・調査用の分析メモです。実際の投資判断は、自分で追加調査をしたうえで行ってください。
