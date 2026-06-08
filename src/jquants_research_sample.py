# このファイルの役割:
# J-Quants APIでキオクシア(285A)の財務データを取得できるか調査するための試作用コードです。
#
# 注意:
# このファイルはVer3.0の調査用サンプルです。
# 既存のPDF/API/AI分離設計には組み込まず、J-Quantsを正式データソース候補にできるか確認するためだけに使います。

import argparse
from datetime import datetime
import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NOT_ACQUIRED = "未取得"
STATUS_ACQUIRED = "取得済み"
STATUS_NOT_ACQUIRED = "未取得"
STATUS_ERROR = "エラー"
JQUANTS_V1_BASE_URL = "https://api.jquants.com/v1"
JQUANTS_V2_BASE_URL = "https://api.jquants.com/v2"
SALES_FIELD_CANDIDATES = ["NetSales", "Revenue", "OperatingRevenue", "Sales", "TotalRevenue"]
OPERATING_PROFIT_FIELD_CANDIDATES = ["OP", "OperatingProfit", "OperatingIncome"]
NET_INCOME_FIELD_CANDIDATES = ["NP", "Profit", "ProfitAttributableToOwnersOfParent", "NetIncome"]
EPS_FIELD_CANDIDATES = ["EarningsPerShare", "BasicEarningsPerShare", "EPS"]


# この関数の役割:
# .envがあれば簡易的に環境変数へ読み込みます。
# なぜ必要か:
# python-dotenvが入っていない調査環境でも、JQUANTS_API_KEYを読み込めるようにするためです。
def load_env_file_if_exists() -> None:
    env_file_path = ".env"

    if not os.path.exists(env_file_path):
        return

    with open(env_file_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            stripped_line = line.strip()

            if stripped_line == "" or stripped_line.startswith("#"):
                continue

            if "=" not in stripped_line:
                continue

            key, value = stripped_line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


# この関数の役割:
# 調査結果の1項目を、値だけでなくメタ情報付きで作ります。
# なぜ必要か:
# 投資判断に使うには、値そのものだけでなく、時点、単位、データ元、元フィールド、取得可否を確認する必要があるためです。
def create_research_item(
    value: Any,
    unit: str,
    as_of_date: str,
    source: str,
    raw_field_name: str,
    status: str,
    note: str,
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "as_of_date": as_of_date,
        "source": source,
        "raw_field_name": raw_field_name,
        "status": status,
        "note": note,
    }


# この関数の役割:
# 未取得の項目を理由つきで作ります。
def create_not_acquired_item(source: str, raw_field_name: str, note: str) -> dict[str, Any]:
    return create_research_item(
        value=NOT_ACQUIRED,
        unit="-",
        as_of_date="-",
        source=source,
        raw_field_name=raw_field_name,
        status=STATUS_NOT_ACQUIRED,
        note=note,
    )


# この関数の役割:
# J-Quants APIにHTTPリクエストを送り、JSONを辞書として返します。
# なぜ必要か:
# requestsを追加しなくても動くよう、Python標準ライブラリだけでJ-Quants APIを試すためです。
def request_json(
    url: str,
    method: str = "GET",
    id_token: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    headers = {}

    if id_token is not None:
        headers["Authorization"] = f"Bearer {id_token}"

    if api_key is not None:
        headers["x-api-key"] = api_key

    request = Request(url=url, method=method, headers=headers)

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"HTTP {error.code}: {error.reason}. response={error_body}") from error

    return json.loads(response_body)


# この関数の役割:
# refresh tokenからJ-QuantsのIDトークンを取得します。
# なぜ必要か:
# J-Quants APIのデータ取得には、Authorizationヘッダーに指定するIDトークンが必要なためです。
def get_jquants_id_token(refresh_token: str) -> str:
    query_string = urlencode({"refreshtoken": refresh_token})
    url = f"{JQUANTS_V1_BASE_URL}/token/auth_refresh?{query_string}"
    response_json = request_json(url=url, method="POST")

    id_token = response_json.get("idToken")

    if id_token is None:
        raise ValueError(f"J-QuantsのIDトークンを取得できませんでした: {response_json}")

    return id_token


# この関数の役割:
# J-Quantsの銘柄コード候補を作ります。
# なぜ必要か:
# J-Quantsでは4桁コードに0を付けた5文字コードで返るケースがあるため、285Aと285A0の両方を試せるようにします。
def create_jquants_code_candidates(stock_code: str) -> list[str]:
    cleaned_stock_code = stock_code.strip().upper()
    candidates = [cleaned_stock_code]

    if len(cleaned_stock_code) == 4:
        candidates.append(f"{cleaned_stock_code}0")

    return candidates


# この関数の役割:
# J-Quants V2の財務サマリー(/fins/summary)を取得します。
# なぜ必要か:
# J-Quants V2ではAPIキー認証が使われるため、今後の正式データソース候補としてはこちらを優先して調査します。
def fetch_jquants_fin_summary_v2(api_key: str, stock_code: str) -> tuple[list[dict[str, Any]], str]:
    for code_candidate in create_jquants_code_candidates(stock_code):
        query_string = urlencode({"code": code_candidate})
        url = f"{JQUANTS_V2_BASE_URL}/fins/summary?{query_string}"
        response_json = request_json(url=url, method="GET", api_key=api_key)

        # V2のレスポンス形式が変わっても調査を続けられるよう、よくあるキーを順番に確認します。
        statements = response_json.get("data") or response_json.get("statements") or response_json.get("summary") or []

        if len(statements) > 0:
            return statements, code_candidate

    return [], "/".join(create_jquants_code_candidates(stock_code))


# この関数の役割:
# J-Quants V1の財務情報(/fins/statements)を取得します。
# なぜ必要か:
# 古いrefresh token方式を使っている場合でも、移行状況を調査できるように残しています。
def fetch_jquants_statements_v1(id_token: str, stock_code: str) -> tuple[list[dict[str, Any]], str]:
    for code_candidate in create_jquants_code_candidates(stock_code):
        query_string = urlencode({"code": code_candidate})
        url = f"{JQUANTS_V1_BASE_URL}/fins/statements?{query_string}"
        response_json = request_json(url=url, method="GET", id_token=id_token)
        statements = response_json.get("statements", [])

        if len(statements) > 0:
            return statements, code_candidate

    return [], "/".join(create_jquants_code_candidates(stock_code))


# この関数の役割:
# J-Quantsの財務レスポンスから最新らしいレコードを選びます。
# なぜ必要か:
# 複数の決算期が返る可能性があるため、まずはDisclosedDateが最も新しいものを調査対象にします。
def select_latest_statement(statements: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(statements) == 0:
        return None

    return sorted(
        statements,
        key=lambda statement: str(statement.get("DiscDate") or statement.get("DisclosedDate") or ""),
        reverse=True,
    )[0]


# この関数の役割:
# J-Quantsのstatementから、開示日・決算期・書類種別などの基本情報を取り出します。
# なぜ必要か:
# 財務数値は「いつの、どの期間の数字か」が重要なので、数値と期間情報を必ずセットで扱うためです。
def get_statement_period_metadata(statement: dict[str, Any]) -> dict[str, Any]:
    return {
        "disclosed_date": statement.get("DiscDate") or statement.get("DisclosedDate") or NOT_ACQUIRED,
        "document_type": statement.get("DocType") or statement.get("TypeOfDocument") or NOT_ACQUIRED,
        "current_period_type": statement.get("CurPerType") or statement.get("CurrentPeriodType") or NOT_ACQUIRED,
        "current_period_end": statement.get("CurPerEn") or statement.get("CurrentPeriodEndDate") or NOT_ACQUIRED,
        "current_fiscal_year_end": statement.get("CurFYEn") or statement.get("CurrentFiscalYearEndDate") or NOT_ACQUIRED,
    }


# この関数の役割:
# 指定されたperiod_type / fiscal_year_endに一致するstatementを選びます。
# なぜ必要か:
# latestだけを使うと、PDFが通期なのにJ-Quantsは3Q、という期間ズレが起きてしまうためです。
def select_statement_by_period(
    statements: list[dict[str, Any]],
    period_type: str | None,
    fiscal_year_end: str | None,
) -> dict[str, Any] | None:
    matching_statements = []

    for statement in statements:
        period_metadata = get_statement_period_metadata(statement)
        matches_period_type = True
        matches_fiscal_year_end = True

        if period_type is not None and period_type.strip() != "":
            matches_period_type = str(period_metadata["current_period_type"]).upper() == period_type.strip().upper()

        if fiscal_year_end is not None and fiscal_year_end.strip() != "":
            matches_fiscal_year_end = str(period_metadata["current_fiscal_year_end"]) == fiscal_year_end.strip()

        if matches_period_type and matches_fiscal_year_end:
            matching_statements.append(statement)

    if len(matching_statements) == 0:
        return None

    return select_latest_statement(matching_statements)


# この関数の役割:
# 候補フィールドの中から最初に存在する値を取り出します。
def get_first_existing_field(statement: dict[str, Any], field_candidates: list[str]) -> tuple[Any, str]:
    for field_name in field_candidates:
        if field_name not in statement:
            continue

        value = statement.get(field_name)

        if value is None or value == "":
            continue

        return value, field_name

    return NOT_ACQUIRED, "/".join(field_candidates)


# この関数の役割:
# J-Quantsの値を調査項目として整形します。
def create_jquants_statement_item(
    statement: dict[str, Any] | None,
    field_candidates: list[str],
    unit: str,
    note: str,
) -> dict[str, Any]:
    if statement is None:
        return create_not_acquired_item(
            source="J-Quants",
            raw_field_name="/".join(field_candidates),
            note="指定条件に一致するJ-Quants statementがないため、この項目は未取得です。",
        )

    value, raw_field_name = get_first_existing_field(statement, field_candidates)

    if value == NOT_ACQUIRED:
        return create_not_acquired_item(
            source="J-Quants",
            raw_field_name=raw_field_name,
            note=f"J-Quantsの最新財務レコードに該当フィールドが見つかりませんでした。{note}",
        )

    as_of_date = (
        statement.get("CurPerEn")
        or statement.get("CurFYEn")
        or statement.get("DiscDate")
        or statement.get("CurrentFiscalYearEndDate")
        or statement.get("CurrentPeriodEndDate")
        or statement.get("DisclosedDate")
        or "-"
    )

    return create_research_item(
        value=value,
        unit=unit,
        as_of_date=str(as_of_date),
        source="J-Quants",
        raw_field_name=raw_field_name,
        status=STATUS_ACQUIRED,
        note=note,
    )


# この関数の役割:
# 一覧表示用に、statementから主要4項目をまとめて取り出します。
# なぜ必要か:
# ユーザーが「どの決算期のデータを使うべきか」を人間の目で確認できるようにするためです。
def create_statement_summary(statement: dict[str, Any]) -> dict[str, Any]:
    period_metadata = get_statement_period_metadata(statement)
    sales_value, _ = get_first_existing_field(statement, SALES_FIELD_CANDIDATES)
    operating_profit_value, _ = get_first_existing_field(statement, OPERATING_PROFIT_FIELD_CANDIDATES)
    net_income_value, _ = get_first_existing_field(statement, NET_INCOME_FIELD_CANDIDATES)
    eps_value, _ = get_first_existing_field(statement, EPS_FIELD_CANDIDATES)

    return {
        "disclosed_date": period_metadata["disclosed_date"],
        "document_type": period_metadata["document_type"],
        "current_period_type": period_metadata["current_period_type"],
        "current_period_end": period_metadata["current_period_end"],
        "current_fiscal_year_end": period_metadata["current_fiscal_year_end"],
        "sales": sales_value,
        "operating_profit": operating_profit_value,
        "net_income": net_income_value,
        "eps": eps_value,
    }


# この関数の役割:
# PDFと比較する対象期間が一致しているか確認し、ズレがあればWARNINGを作ります。
def create_period_warning(
    selected_statement: dict[str, Any] | None,
    target_period_type: str | None,
    target_fiscal_year_end: str | None,
) -> str | None:
    if target_period_type is None and target_fiscal_year_end is None:
        return None

    if selected_statement is None:
        return "WARNING: 指定したperiod_type / fiscal_year_endに一致するJ-Quants statementが見つかりませんでした。PDFと同じ期間では比較できません。"

    period_metadata = get_statement_period_metadata(selected_statement)
    warning_messages = []

    if target_period_type is not None and target_period_type.strip() != "":
        selected_period_type = str(period_metadata["current_period_type"]).upper()
        if selected_period_type != target_period_type.strip().upper():
            warning_messages.append(
                f"period_typeが一致していません。指定={target_period_type}, J-Quants={period_metadata['current_period_type']}"
            )

    if target_fiscal_year_end is not None and target_fiscal_year_end.strip() != "":
        selected_fiscal_year_end = str(period_metadata["current_fiscal_year_end"])
        if selected_fiscal_year_end != target_fiscal_year_end.strip():
            warning_messages.append(
                f"fiscal_year_endが一致していません。指定={target_fiscal_year_end}, J-Quants={period_metadata['current_fiscal_year_end']}"
            )

    if len(warning_messages) == 0:
        return None

    return "WARNING: " + " / ".join(warning_messages)


# この関数の役割:
# yfinanceの値を比較用に取得します。
# なぜ必要か:
# J-Quantsとyfinanceの値・時点・取得可否を並べて確認するためです。
def fetch_yfinance_comparison_data(ticker_symbol: str) -> dict[str, Any]:
    try:
        import yfinance as yf
    except ModuleNotFoundError:
        return {}

    stock_ticker = yf.Ticker(ticker_symbol)
    info_dictionary = stock_ticker.info
    financials_table = stock_ticker.financials

    def get_financial_row(row_name: str) -> Any:
        if financials_table is None or getattr(financials_table, "empty", True):
            return NOT_ACQUIRED

        if row_name not in financials_table.index:
            return NOT_ACQUIRED

        row_values = financials_table.loc[row_name].dropna()

        if row_values.empty:
            return NOT_ACQUIRED

        return row_values.iloc[0]

    return {
        "sales": info_dictionary.get("totalRevenue") or get_financial_row("Total Revenue"),
        "operating_profit": get_financial_row("Operating Income"),
        "net_income": get_financial_row("Net Income"),
        "eps": info_dictionary.get("trailingEps"),
    }


# この関数の役割:
# J-Quantsの財務データ取得調査を実行します。
def run_jquants_research(
    stock_code: str = "285A",
    period_type: str | None = None,
    fiscal_year_end: str | None = None,
) -> dict[str, Any]:
    load_env_file_if_exists()
    api_key = os.getenv("JQUANTS_API_KEY")
    refresh_token = os.getenv("JQUANTS_REFRESH_TOKEN")

    if api_key is not None and api_key.strip() != "":
        try:
            statements, resolved_code = fetch_jquants_fin_summary_v2(api_key=api_key.strip(), stock_code=stock_code)
            auth_method = "JQUANTS_API_KEY / V2"
        except ValueError as error:
            return {
                "error": create_research_item(
                    value=NOT_ACQUIRED,
                    unit="-",
                    as_of_date="-",
                    source="J-Quants",
                    raw_field_name="JQUANTS_API_KEY",
                    status=STATUS_ERROR,
                    note=f"J-Quants V2 APIの呼び出しに失敗しました: {error}",
                )
            }
    elif refresh_token is not None and refresh_token.strip() != "":
        try:
            id_token = get_jquants_id_token(refresh_token=refresh_token.strip())
            statements, resolved_code = fetch_jquants_statements_v1(id_token=id_token, stock_code=stock_code)
            auth_method = "JQUANTS_REFRESH_TOKEN / V1"
        except ValueError as error:
            return {
                "error": create_research_item(
                    value=NOT_ACQUIRED,
                    unit="-",
                    as_of_date="-",
                    source="J-Quants",
                    raw_field_name="JQUANTS_REFRESH_TOKEN",
                    status=STATUS_ERROR,
                    note=(
                        "J-Quantsの旧refresh token方式でエラーになりました。"
                        "HTTP 410 Goneの場合、V1エンドポイントが利用できない可能性が高いため、"
                        ".envにJQUANTS_API_KEYを設定してV2 APIで再実行してください。"
                        f" 詳細: {error}"
                    ),
                )
            }
    else:
        return {
            "error": create_research_item(
                value=NOT_ACQUIRED,
                unit="-",
                as_of_date="-",
                source="J-Quants",
                raw_field_name="JQUANTS_API_KEY",
                status=STATUS_ERROR,
                note=".envにJQUANTS_API_KEYが設定されていないため、J-Quants V2 APIを実行できません。",
            )
        }

    latest_statement = select_latest_statement(statements)
    selected_statement = select_statement_by_period(
        statements=statements,
        period_type=period_type,
        fiscal_year_end=fiscal_year_end,
    )
    yfinance_data = fetch_yfinance_comparison_data(f"{stock_code}.T")
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_available_fields = []
    selected_available_fields = []

    if latest_statement is not None:
        latest_available_fields = sorted(latest_statement.keys())

    if selected_statement is not None:
        selected_available_fields = sorted(selected_statement.keys())

    return {
        "metadata": {
            "stock_code": stock_code,
            "resolved_jquants_code": resolved_code,
            "fetched_at": fetched_at,
            "auth_method": auth_method,
            "statement_count": len(statements),
            "target_period_type": period_type or NOT_ACQUIRED,
            "target_fiscal_year_end": fiscal_year_end or NOT_ACQUIRED,
            "latest_disclosed_date": (
                latest_statement.get("DiscDate") or latest_statement.get("DisclosedDate")
                if latest_statement is not None
                else NOT_ACQUIRED
            ),
            "latest_type_of_document": (
                latest_statement.get("DocType") or latest_statement.get("TypeOfDocument")
                if latest_statement is not None
                else NOT_ACQUIRED
            ),
            "current_period_type": latest_statement.get("CurPerType") if latest_statement is not None else NOT_ACQUIRED,
            "current_period_end": latest_statement.get("CurPerEn") if latest_statement is not None else NOT_ACQUIRED,
            "current_fiscal_year_end": latest_statement.get("CurFYEn") if latest_statement is not None else NOT_ACQUIRED,
            "latest_available_fields": ", ".join(latest_available_fields[:80]) if latest_available_fields else NOT_ACQUIRED,
            "selected_available_fields": ", ".join(selected_available_fields[:80]) if selected_available_fields else NOT_ACQUIRED,
            "period_warning": create_period_warning(
                selected_statement=selected_statement,
                target_period_type=period_type,
                target_fiscal_year_end=fiscal_year_end,
            ),
        },
        "statements": [create_statement_summary(statement) for statement in statements],
        "items": {
            "sales": create_jquants_statement_item(
                statement=selected_statement,
                field_candidates=SALES_FIELD_CANDIDATES,
                unit="円",
                note="売上系フィールド候補から取得しています。IFRS/日本基準の項目名差に注意が必要です。",
            ),
            "operating_profit": create_jquants_statement_item(
                statement=selected_statement,
                field_candidates=OPERATING_PROFIT_FIELD_CANDIDATES,
                unit="円",
                note="営業利益です。Non-GAAP営業利益ではない可能性があります。",
            ),
            "net_income": create_jquants_statement_item(
                statement=selected_statement,
                field_candidates=NET_INCOME_FIELD_CANDIDATES,
                unit="円",
                note="純利益または親会社帰属利益の候補です。正式採用前にフィールド定義確認が必要です。",
            ),
            "eps": create_jquants_statement_item(
                statement=selected_statement,
                field_candidates=EPS_FIELD_CANDIDATES,
                unit="円",
                note="EPSです。希薄化後EPSやNon-GAAP EPSとは異なる可能性があります。",
            ),
        },
        "yfinance_comparison": yfinance_data,
    }


# この関数の役割:
# J-Quantsとyfinanceの差分をMarkdown表として出力します。
def print_research_result_as_markdown(research_result: dict[str, Any]) -> None:
    if "error" in research_result:
        error_item = research_result["error"]
        print("# J-Quants 調査結果")
        print("")
        print(f"- 状態: {error_item['status']}")
        print(f"- 補足: {error_item['note']}")
        return

    metadata = research_result["metadata"]
    statements = research_result["statements"]
    items = research_result["items"]
    yfinance_comparison = research_result["yfinance_comparison"]

    print("# J-Quants 調査結果")
    print("")
    print(f"- stock_code: {metadata['stock_code']}")
    print(f"- resolved_jquants_code: {metadata['resolved_jquants_code']}")
    print(f"- fetched_at: {metadata['fetched_at']}")
    print(f"- auth_method: {metadata['auth_method']}")
    print(f"- statement_count: {metadata['statement_count']}")
    print(f"- target_period_type: {metadata['target_period_type']}")
    print(f"- target_fiscal_year_end: {metadata['target_fiscal_year_end']}")
    print(f"- latest_disclosed_date: {metadata['latest_disclosed_date']}")
    print(f"- latest_type_of_document: {metadata['latest_type_of_document']}")
    print(f"- current_period_type: {metadata['current_period_type']}")
    print(f"- current_period_end: {metadata['current_period_end']}")
    print(f"- current_fiscal_year_end: {metadata['current_fiscal_year_end']}")
    print(f"- latest_available_fields: {metadata['latest_available_fields']}")
    print(f"- selected_available_fields: {metadata['selected_available_fields']}")

    if metadata["period_warning"] is not None:
        print("")
        print(metadata["period_warning"])

    print("")
    print("## statements一覧")
    print("")
    print("| disclosed_date | document_type | current_period_type | current_period_end | current_fiscal_year_end | sales | operating_profit | net_income | eps |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for statement in statements:
        print(
            "| "
            f"{statement['disclosed_date']} | "
            f"{statement['document_type']} | "
            f"{statement['current_period_type']} | "
            f"{statement['current_period_end']} | "
            f"{statement['current_fiscal_year_end']} | "
            f"{statement['sales']} | "
            f"{statement['operating_profit']} | "
            f"{statement['net_income']} | "
            f"{statement['eps']} |"
        )

    print("")
    print("## 選択されたstatementの財務データ")
    print("")
    print("| 項目 | J-Quants値 | 単位 | 時点 | J-Quants元フィールド | 状態 | yfinance値 | 補足 |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")

    for item_key, item in items.items():
        print(
            "| "
            f"{item_key} | "
            f"{item['value']} | "
            f"{item['unit']} | "
            f"{item['as_of_date']} | "
            f"{item['raw_field_name']} | "
            f"{item['status']} | "
            f"{yfinance_comparison.get(item_key, NOT_ACQUIRED)} | "
            f"{item['note']} |"
        )


# この関数の役割:
# コマンドライン引数を読み取ります。
# なぜ必要か:
# PDFの対象期間に合わせて、J-Quantsのどのstatementを使うか指定できるようにするためです。
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="J-Quantsから取得した財務statementsを一覧表示し、指定期間に合うデータを選択します。"
    )
    parser.add_argument(
        "stock_code",
        nargs="?",
        default="285A",
        help="調査対象の証券コードです。例: 285A",
    )
    parser.add_argument(
        "--period-type",
        default=None,
        help="対象の決算期間です。例: FY, 3Q, 2Q, 1Q",
    )
    parser.add_argument(
        "--fiscal-year-end",
        default=None,
        help="対象の会計年度末です。例: 2026-03-31",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    result = run_jquants_research(
        stock_code=arguments.stock_code,
        period_type=arguments.period_type,
        fiscal_year_end=arguments.fiscal_year_end,
    )
    print_research_result_as_markdown(result)
