# Data Source Research for Ver3.0

Ver3.0では、投資判断支援に必要なデータをどこから取得すべきかを整理します。

この調査の目的は、いきなり大きく実装することではなく、PER、予想PER、同業比較、市場規模分析、シナリオ分析に必要なデータ取得元を明確にすることです。

## 基本方針

- PDFは定性情報の確認に使う。
- 投資指標や財務数値はAPI由来データを正式データとして扱う。
- yfinanceは試作用として使う。
- 日本株の正式データ取得は、将来的にJ-Quants APIを優先候補にする。
- 取得できない項目は推測せず `未取得` と表示する。
- 投資判断や自動売買はまだ実装しない。

## yfinanceで確認するサンプル銘柄

キオクシアを例にします。

```text
証券コード: 285A
yfinance ticker: 285A.T
```

サンプルコードは以下です。

```powershell
python src/yfinance_research_sample.py
```

## 取得可否の整理

| 項目 | yfinanceでの試作取得 | 主な取得場所 | J-Quantsで取得すべきか | 方針 |
| --- | --- | --- | --- | --- |
| 現在株価 | 取得候補 | `Ticker.info.currentPrice` / `history()` | はい | yfinanceで試作。正式にはJ-Quantsの日次株価を検討 |
| EPS | 取得候補 | `Ticker.info.trailingEps` | はい | yfinance値は試作用。正式には財務API由来を優先 |
| 予想EPS | 取得候補 | `Ticker.info.forwardEps` / `get_earnings_estimate()` | 要調査 | J-Quantsで取得できない場合は別データソース検討 |
| PER | 取得候補 | `Ticker.info.trailingPE` | 計算で対応 | 正式にはAPI由来株価 ÷ API由来EPSで計算 |
| 予想PER | 取得候補 | `Ticker.info.forwardPE` | 要調査 | API由来株価 ÷ 予想EPSで計算 |
| PBR | 取得候補 | `Ticker.info.priceToBook` | 計算で対応 | 正式にはAPI由来株価 ÷ API由来BPSで計算 |
| 時価総額 | 取得候補 | `Ticker.info.marketCap` | 計算で対応 | 正式にはAPI由来株価 × 発行済株式数で計算 |
| 売上 | 取得候補 | `Ticker.financials` | はい | 正式にはJ-Quants財務情報を優先 |
| 営業利益 | 取得候補 | `Ticker.financials` | はい | 正式にはJ-Quants財務情報を優先 |
| 純利益 | 取得候補 | `Ticker.financials` | はい | 正式にはJ-Quants財務情報を優先 |
| ROE | 取得候補 | `Ticker.info.returnOnEquity` | 計算で対応 | 正式には純利益 ÷ 自己資本で計算 |
| 自己資本比率 | 計算候補 | `Ticker.balance_sheet` | はい | 正式には自己資本 ÷ 総資産で計算 |
| 営業CF | 取得候補 | `Ticker.cashflow` | はい | 正式にはJ-Quants財務諸表データを優先 |
| フリーCF | 取得候補 | `Ticker.cashflow` | 要調査 | J-Quantsで直接無い場合は営業CFと投資CFから計算 |
| アナリスト目標株価 | 取得候補 | `Ticker.info.targetMeanPrice` / `analyst_price_targets` | いいえ | J-Quantsより金融情報ベンダー向き |
| レーティング | 取得候補 | `Ticker.info.recommendationKey` | いいえ | 証券会社レポートや金融情報ベンダー向き |
| 同業他社比較に使える指標 | 一部取得候補 | `sector` / `industry` / 各種指標 | はい | 同業銘柄リストを別途作り、同じ指標で比較 |

## yfinanceの注意点

yfinanceは試作には便利ですが、正式な投資判断データとしては注意が必要です。

- 銘柄によって取得できる項目が異なる。
- 日本株では項目が `未取得` になることがある。
- 財務データの会計基準、期間、通貨、更新タイミングを確認する必要がある。
- 目標株価やレーティングは取得できても、情報源や更新日を確認しづらい。
- 正式データとして使う前に、J-Quantsや企業開示データとの突合が必要。

## 285A.Tのサンプル実行結果メモ

ユーザー環境で `python src/yfinance_research_sample.py` を実行したところ、以下のような結果が得られました。

この表は、値が取れたかどうかの整理です。実際の採用前には、メタ情報付きの出力で時点・単位・元フィールド・注意点を確認します。

| 項目 | 取得状況 | サンプル値 | 注意点 |
| --- | --- | --- | --- |
| 現在株価 | 取得済み | 71,880円 | 取得日時、リアルタイム/遅延/直近価格の確認が必要 |
| EPS | 取得済み | 1,008.01円 | trailingEps。PDFのNon-GAAP EPSとは異なる可能性あり |
| 予想EPS | 未取得 | 未取得 | forwardEpsが日本株では提供されない可能性あり |
| PER | 取得済み | 71.31倍 | trailingPE。正式にはAPI由来株価 ÷ API由来EPSで再計算したい |
| 予想PER | 未取得 | 未取得 | forwardPEが日本株では提供されない可能性あり |
| PBR | 取得済み | 28.06倍 | priceToBook。BPSの根拠確認が必要 |
| 時価総額 | 取得済み | 約392,527億円 | marketCap。発行済株式数と株価の更新タイミング確認が必要 |
| 売上 | 取得済み | 約17,065億円 | financials由来。決算PDFのFY2025とは異なるため時点確認が必要 |
| 営業利益 | 取得済み | 約4,517億円 | financials由来。IFRS/Non-GAAPの違いに注意 |
| 純利益 | 取得済み | 約2,723億円 | financials由来。親会社帰属利益か確認が必要 |
| ROE | 取得済み | 51.9% | returnOnEquity。算出定義の確認が必要 |
| 自己資本比率 | 計算済み | 72.3% | balance_sheetから自己資本 ÷ 総資産で計算 |
| 営業CF | 取得済み | 約4,764億円 | cashflow由来。決算期確認が必要 |
| フリーCF | 取得済み | 約2,508億円 | Free Cash Flow行の定義確認が必要 |
| アナリスト目標株価 | 取得済み | 86,250円 | 情報源、対象アナリスト、更新日の確認が必要 |
| レーティング | 取得済み | buy | レーティング定義と更新日の確認が必要 |
| 同業比較候補 | 一部取得済み | Semiconductors / Technology | 同業比較そのものは未取得。同業銘柄リスト設計が必要 |

## メタ情報付き出力の方針

今後は、取得した値をそのまま表示せず、以下の情報をセットで持たせます。

| メタ情報 | 意味 |
| --- | --- |
| value | 表示用に整えた値 |
| unit | 円、億円、%、倍など |
| as_of_date | 取得日時、決算期、TTM、latest_fiscal_yearなど |
| source | yfinance、J-Quantsなど |
| raw_field_name | yfinance上の元フィールド名や財務諸表の行名 |
| status | 取得済み / 未取得 |
| note | 注意点、未取得理由、正式採用前の確認事項 |

## API由来データの注意点

- yfinanceは試作用データソース。
- データ時点や会計基準が企業IR資料と一致しない可能性がある。
- 投資判断に使う場合はJ-Quantsや公式資料との照合が必要。
- `forecast_eps` や `forecast_per` は日本株では取得できない可能性がある。
- 財務データは `latest_fiscal_year` なのか `trailing_12_months` なのか確認が必要。

## J-Quants APIで優先的に調べる項目

J-Quants APIはJPX系のデータサービスで、日本株の株価や財務情報を取得する候補です。

公式ドキュメントでは、株価四本値 `/prices/daily_quotes`、上場銘柄一覧 `/listed/info`、財務情報 `/fins/statements`、財務諸表 `/fins/fs_details` などが案内されています。

優先的に調べる項目です。

- 日次株価
- 銘柄情報
- 売上
- 営業利益
- 純利益
- EPS
- BPS
- 総資産
- 自己資本
- 営業CF
- 投資CF
- 財務CF
- 発行済株式数

## 友達の要望との対応

| 要望 | 必要データ | 優先データソース | 備考 |
| --- | --- | --- | --- |
| PER分析 | 現在株価、EPS | J-Quants / yfinance試作 | API由来データだけで計算 |
| 予想PER | 現在株価、予想EPS | yfinance試作 / 追加API要調査 | 予想EPSの信頼性確認が必要 |
| 同業比較 | 同業銘柄リスト、PER、PBR、ROE、時価総額など | J-Quants + 独自同業リスト | yfinanceのsector/industryは補助情報 |
| 市場規模分析 | 市場レポート、業界統計 | 調査会社、業界団体、企業IR | yfinance/J-Quantsだけでは不足 |
| シナリオ分析 | 株価、EPS、予想EPS、想定PER、成長率 | J-Quants + 予想データAPI | 未取得ならシナリオ値は作らない |

## 参考リンク

- [yfinance Ticker API](https://ericpien.github.io/yfinance/reference/api/yfinance.Ticker.html)
- [yfinance fast_info](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.fast_info.html)
- [J-Quants API仕様](https://jpx.gitbook.io/j-quants-ja/api-reference)
- [J-Quants 株価四本値 /prices/daily_quotes](https://jpx.gitbook.io/j-quants-ja/api-reference/daily_quotes)
- [J-Quants Pro 財務情報 /fins/statements](https://jpx.gitbook.io/j-quants-pro-ja/api-reference/statements)
- [J-Quants Pro 財務諸表 /fins/fs_details](https://jpx.gitbook.io/j-quants-pro/api-reference/statements_details)

## 次の実装候補

1. `market_data_client.py` とは別に `financial_data_client.py` を作る。
2. yfinance試作用クライアントとJ-Quants本番候補クライアントを分ける。
3. API由来データを `data_models.py` で型定義する。
4. 取得できない項目は `未取得` のままMarkdownへ出す。
5. PDF由来の定量情報は正式データとして使わない方針を維持する。
