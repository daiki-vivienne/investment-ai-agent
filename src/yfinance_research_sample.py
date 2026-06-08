# このファイルの役割:
# yfinanceで取得できる投資指標を、キオクシア(285A.T)を例に確認するための試作用コードです。
#
# 注意:
# このファイルはVer3.0の調査用サンプルです。
# 既存のPDF/API/AI分離設計を壊さないよう、メインアプリには組み込まず、単体で実行できる形にしています。

from datetime import datetime
from typing import Any


NOT_ACQUIRED = "未取得"
STATUS_ACQUIRED = "取得済み"
STATUS_NOT_ACQUIRED = "未取得"
SOURCE_NAME = "yfinance"


# この関数の役割:
# 取得できた値とメタ情報を1つの辞書にまとめます。
# なぜ必要か:
# 数字だけだと「いつ時点か」「単位は何か」「どのAPI項目から来たか」が分からず、投資判断に使うには危険なためです。
def create_data_item(
    value: Any,
    unit: str,
    as_of_date: str,
    raw_field_name: str,
    note: str,
    status: str = STATUS_ACQUIRED,
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "as_of_date": as_of_date,
        "source": SOURCE_NAME,
        "raw_field_name": raw_field_name,
        "status": status,
        "note": note,
    }


# この関数の役割:
# 未取得の項目を、理由つきのメタ情報として作ります。
def create_not_acquired_item(raw_field_name: str, note: str) -> dict[str, Any]:
    return create_data_item(
        value=NOT_ACQUIRED,
        unit="-",
        as_of_date="-",
        raw_field_name=raw_field_name,
        note=note,
        status=STATUS_NOT_ACQUIRED,
    )


# この関数の役割:
# yfinanceの値が取得できたかを判定します。
def is_acquired(value: Any) -> bool:
    if value is None:
        return False

    if value == "":
        return False

    return True


# この関数の役割:
# 金額を「約xx億円」のように読みやすく変換します。
# なぜ必要か:
# yfinanceは円単位の大きな数値を返すため、そのままだと人間が規模感をつかみにくいためです。
def format_yen_to_oku_yen(value: Any) -> str:
    if not is_acquired(value):
        return NOT_ACQUIRED

    value_as_float = float(value)
    oku_yen = value_as_float / 100000000

    return f"約{oku_yen:,.0f}億円"


# この関数の役割:
# 株価やEPSなど、円単位の数値を読みやすく表示します。
def format_yen(value: Any) -> str:
    if not is_acquired(value):
        return NOT_ACQUIRED

    return f"{float(value):,.2f}"


# この関数の役割:
# 0.519 のような小数を 51.9% のように表示します。
def format_ratio_as_percent(value: Any) -> str:
    if not is_acquired(value):
        return NOT_ACQUIRED

    return f"{float(value) * 100:.1f}%"


# この関数の役割:
# 倍率系の数値を読みやすく表示します。
def format_multiple(value: Any) -> str:
    if not is_acquired(value):
        return NOT_ACQUIRED

    return f"{float(value):.2f}"


# この関数の役割:
# DataFrameの最新列の日付を取り出します。
# なぜ必要か:
# 売上やCFなどの財務データが、どの決算期の列から取れたかを表示するためです。
def get_latest_statement_date(statement_table: Any) -> str:
    if statement_table is None:
        return "-"

    if getattr(statement_table, "empty", True):
        return "-"

    latest_column = statement_table.columns[0]

    if hasattr(latest_column, "date"):
        return str(latest_column.date())

    return str(latest_column)


# この関数の役割:
# 財務諸表DataFrameから、指定した行名の最新値と取得元行名を取り出します。
def get_latest_statement_value(statement_table: Any, possible_row_names: list[str]) -> tuple[Any, str, str]:
    if statement_table is None:
        return NOT_ACQUIRED, "-", "-"

    if getattr(statement_table, "empty", True):
        return NOT_ACQUIRED, "-", "-"

    latest_statement_date = get_latest_statement_date(statement_table)

    for row_name in possible_row_names:
        if row_name not in statement_table.index:
            continue

        row_values = statement_table.loc[row_name].dropna()

        if row_values.empty:
            return NOT_ACQUIRED, row_name, latest_statement_date

        return row_values.iloc[0], row_name, latest_statement_date

    return NOT_ACQUIRED, "/".join(possible_row_names), latest_statement_date


# この関数の役割:
# info辞書から値を取り出し、取得できない場合は未取得アイテムを作ります。
def create_info_item(
    info_dictionary: dict[str, Any],
    raw_field_name: str,
    unit: str,
    as_of_date: str,
    note: str,
    formatter,
) -> dict[str, Any]:
    raw_value = info_dictionary.get(raw_field_name)

    if not is_acquired(raw_value):
        return create_not_acquired_item(
            raw_field_name=raw_field_name,
            note=f"yfinanceで該当フィールドが取得できない、APIレスポンスに存在しない、または日本株では提供されない可能性があります。{note}",
        )

    return create_data_item(
        value=formatter(raw_value),
        unit=unit,
        as_of_date=as_of_date,
        raw_field_name=raw_field_name,
        note=note,
    )


# この関数の役割:
# 財務諸表DataFrameから取得した値をメタ情報付きにします。
def create_statement_item(
    statement_table: Any,
    possible_row_names: list[str],
    unit: str,
    note: str,
    formatter,
) -> dict[str, Any]:
    raw_value, raw_field_name, statement_date = get_latest_statement_value(
        statement_table=statement_table,
        possible_row_names=possible_row_names,
    )

    if not is_acquired(raw_value) or raw_value == NOT_ACQUIRED:
        return create_not_acquired_item(
            raw_field_name=raw_field_name,
            note=f"yfinanceの財務諸表テーブルで該当行が取得できませんでした。{note}",
        )

    return create_data_item(
        value=formatter(raw_value),
        unit=unit,
        as_of_date=f"latest_fiscal_year: {statement_date}",
        raw_field_name=raw_field_name,
        note=note,
    )


# この関数の役割:
# yfinanceから取得した値を、メタ情報つきの辞書にまとめます。
def fetch_yfinance_research_data(ticker_symbol: str = "285A.T") -> dict[str, dict[str, Any]]:
    try:
        import yfinance as yf
    except ModuleNotFoundError:
        return {
            "error": create_not_acquired_item(
                raw_field_name="yfinance",
                note="yfinanceがインストールされていません。pip install -r requirements.txt を実行してください。",
            ),
        }

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stock_ticker = yf.Ticker(ticker_symbol)

    # infoは株価、PER、PBR、時価総額などの基本情報が入ることがあります。
    # ただし、Yahoo Finance側のデータ状況に依存するため、必ず取れるとは限りません。
    info_dictionary = stock_ticker.info

    # financials / cashflow / balance_sheet はDataFrameとして返ります。
    # 行名は英語で、銘柄や会計基準によって存在しない場合があります。
    financials_table = stock_ticker.financials
    cashflow_table = stock_ticker.cashflow
    balance_sheet_table = stock_ticker.balance_sheet

    total_equity, total_equity_field, equity_statement_date = get_latest_statement_value(
        balance_sheet_table,
        ["Stockholders Equity", "Total Equity Gross Minority Interest"],
    )
    total_assets, total_assets_field, assets_statement_date = get_latest_statement_value(
        balance_sheet_table,
        ["Total Assets"],
    )

    equity_ratio_item = create_not_acquired_item(
        raw_field_name=f"{total_equity_field} / {total_assets_field}",
        note="自己資本または総資産が取得できないため、自己資本比率を計算できません。",
    )

    if is_acquired(total_equity) and is_acquired(total_assets) and total_equity != NOT_ACQUIRED and total_assets != NOT_ACQUIRED and total_assets != 0:
        equity_ratio = float(total_equity) / float(total_assets)
        equity_ratio_item = create_data_item(
            value=format_ratio_as_percent(equity_ratio),
            unit="%",
            as_of_date=f"latest_fiscal_year: {equity_statement_date or assets_statement_date}",
            raw_field_name=f"{total_equity_field} / {total_assets_field}",
            note="yfinanceの貸借対照表から自己資本 ÷ 総資産で計算しています。会計基準や期間は確認が必要です。",
        )

    return {
        "ticker": create_data_item(
            value=ticker_symbol,
            unit="-",
            as_of_date=f"取得日時: {fetched_at}",
            raw_field_name="input ticker",
            note="調査対象のyfinance tickerです。",
        ),
        "current_price": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="currentPrice",
            unit="円",
            as_of_date=f"取得日時: {fetched_at}",
            note="yfinance上の現在価格です。リアルタイムではなく遅延価格または直近価格の可能性があります。",
            formatter=format_yen,
        ),
        "eps": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="trailingEps",
            unit="円",
            as_of_date="trailing_12_months または yfinance定義の直近実績",
            note="PDFのNon-GAAP EPSとは異なる可能性があります。",
            formatter=format_yen,
        ),
        "forecast_eps": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="forwardEps",
            unit="円",
            as_of_date="forecast",
            note="日本株では提供されない可能性があります。",
            formatter=format_yen,
        ),
        "per": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="trailingPE",
            unit="倍",
            as_of_date="trailing_12_months または yfinance定義の直近実績",
            note="yfinance算出値です。正式採用前に株価とEPSの定義確認が必要です。",
            formatter=format_multiple,
        ),
        "forecast_per": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="forwardPE",
            unit="倍",
            as_of_date="forecast",
            note="日本株では提供されない可能性があります。",
            formatter=format_multiple,
        ),
        "pbr": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="priceToBook",
            unit="倍",
            as_of_date="yfinance定義の直近データ",
            note="正式にはAPI由来株価 ÷ API由来BPSで再計算する方針です。",
            formatter=format_multiple,
        ),
        "market_cap": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="marketCap",
            unit="円",
            as_of_date=f"取得日時: {fetched_at}",
            note="yfinance上の時価総額です。株価や株式数の更新タイミング確認が必要です。",
            formatter=format_yen_to_oku_yen,
        ),
        "sales": create_statement_item(
            statement_table=financials_table,
            possible_row_names=["Total Revenue", "Operating Revenue"],
            unit="円",
            note="決算PDFのFY2025とは異なる可能性があるため、決算期の確認が必要です。",
            formatter=format_yen_to_oku_yen,
        ),
        "operating_profit": create_statement_item(
            statement_table=financials_table,
            possible_row_names=["Operating Income"],
            unit="円",
            note="IFRS/Non-GAAPの違いに注意が必要です。",
            formatter=format_yen_to_oku_yen,
        ),
        "net_income": create_statement_item(
            statement_table=financials_table,
            possible_row_names=["Net Income", "Net Income Common Stockholders"],
            unit="円",
            note="親会社帰属利益かどうか、会計基準の確認が必要です。",
            formatter=format_yen_to_oku_yen,
        ),
        "roe": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="returnOnEquity",
            unit="%",
            as_of_date="yfinance定義の直近データ",
            note="yfinance算出値です。正式には純利益 ÷ 自己資本で再計算する方針です。",
            formatter=format_ratio_as_percent,
        ),
        "equity_ratio": equity_ratio_item,
        "operating_cash_flow": create_statement_item(
            statement_table=cashflow_table,
            possible_row_names=["Operating Cash Flow", "Total Cash From Operating Activities"],
            unit="円",
            note="キャッシュフロー計算書の最新列から取得しています。",
            formatter=format_yen_to_oku_yen,
        ),
        "free_cash_flow": create_statement_item(
            statement_table=cashflow_table,
            possible_row_names=["Free Cash Flow"],
            unit="円",
            note="yfinanceにFree Cash Flow行がある場合のみ取得します。正式には営業CFと投資CFから計算する方針も検討します。",
            formatter=format_yen_to_oku_yen,
        ),
        "analyst_target_price": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="targetMeanPrice",
            unit="円",
            as_of_date="yfinance定義のアナリストデータ",
            note="情報源、対象アナリスト、更新日の確認が必要です。",
            formatter=format_yen,
        ),
        "rating": create_info_item(
            info_dictionary=info_dictionary,
            raw_field_name="recommendationKey",
            unit="-",
            as_of_date="yfinance定義のアナリストデータ",
            note="レーティングの基準や更新日の確認が必要です。",
            formatter=lambda value: value,
        ),
        "peer_comparison_metrics": create_data_item(
            value=f"industry={info_dictionary.get('industry', NOT_ACQUIRED)}, sector={info_dictionary.get('sector', NOT_ACQUIRED)}",
            unit="-",
            as_of_date=f"取得日時: {fetched_at}",
            raw_field_name="industry / sector",
            note="同業比較そのものはyfinance単体では未取得。業種・セクターを使って比較対象候補を作る設計が必要です。",
        ),
    }


# この関数の役割:
# 取得結果を初心者にも見やすいMarkdown表として表示します。
def print_research_result_as_markdown(research_data: dict[str, dict[str, Any]]) -> None:
    if "error" in research_data:
        print(research_data["error"]["note"])
        return

    print("# yfinance サンプル取得結果")
    print("")
    print("| 項目 | 値 | 単位 | 時点 | データ元 | 元フィールド | 状態 | 補足 |")
    print("| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |")

    for key, item in research_data.items():
        print(
            "| "
            f"{key} | "
            f"{item['value']} | "
            f"{item['unit']} | "
            f"{item['as_of_date']} | "
            f"{item['source']} | "
            f"{item['raw_field_name']} | "
            f"{item['status']} | "
            f"{item['note']} |"
        )

    print("")
    print("## API由来データの注意点")
    print("")
    print("- yfinanceは試作用データソースです。")
    print("- データ時点や会計基準が企業IR資料と一致しない可能性があります。")
    print("- 投資判断に使う場合はJ-Quantsや公式資料との照合が必要です。")
    print("- 未取得の項目は推測せず、未取得のまま扱います。")


# この処理の役割:
# python src/yfinance_research_sample.py と実行した時だけサンプル取得を行います。
if __name__ == "__main__":
    result = fetch_yfinance_research_data("285A.T")
    print_research_result_as_markdown(result)
