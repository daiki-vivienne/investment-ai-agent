# このファイルの役割:
# J-Quants APIから財務サマリーを取得し、ユーザー指定の決算期と一致するか確認します。
#
# 注意:
# PDFから決算期を推測すると誤判定の原因になります。
# そのため、このファイルではユーザーがCLIで指定した period_type / fiscal_year_end を正として扱います。

from dataclasses import dataclass
from datetime import date
import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NOT_ACQUIRED = "未取得"
STATUS_ACQUIRED = "取得済み"
STATUS_NOT_ACQUIRED = "未取得"
SOURCE_JQUANTS = "J-Quants"
JQUANTS_V2_BASE_URL = "https://api.jquants.com/v2"

SALES_FIELD_CANDIDATES = ["Sales", "NetSales", "Revenue", "OperatingRevenue", "TotalRevenue"]
OPERATING_PROFIT_FIELD_CANDIDATES = ["OP", "OperatingProfit", "OperatingIncome"]
NET_INCOME_FIELD_CANDIDATES = ["NP", "Profit", "ProfitAttributableToOwnersOfParent", "NetIncome"]
EPS_FIELD_CANDIDATES = ["EPS", "EarningsPerShare", "BasicEarningsPerShare"]


@dataclass
class JQuantsDataItem:
    # このクラスの役割:
    # 1つの財務項目について、値だけでなく取得元・期間・状態も一緒に持ちます。
    value: Any
    unit: str
    period_end: str
    source: str
    raw_field_name: str
    status: str
    note: str


@dataclass
class JQuantsStatementSummary:
    # このクラスの役割:
    # J-Quantsから返った各statementを、一覧表示しやすい形にします。
    disclosed_date: str
    document_type: str
    current_period_type: str
    current_period_end: str
    current_fiscal_year_end: str
    sales: Any
    operating_profit: Any
    net_income: Any
    eps: Any


@dataclass
class JQuantsPeriodCheckResult:
    # このクラスの役割:
    # APIデータがユーザー指定期間と一致したか、分析に使ってよいかを管理します。
    requested_period_type: str
    requested_fiscal_year_end: str
    is_period_matched: bool
    warning_message: str | None
    subscription_note: str | None
    selected_statement: JQuantsStatementSummary | None
    statements: list[JQuantsStatementSummary]
    formal_data_items: dict[str, JQuantsDataItem]


# この関数の役割:
# J-Quants APIへGETリクエストを送り、JSONを辞書として返します。
# なぜ必要か:
# 既存のrequirementsを増やさず、標準ライブラリだけでAPI調査を続けるためです。
def request_json(url: str, api_key: str) -> dict[str, Any]:
    request = Request(
        url=url,
        method="GET",
        headers={"x-api-key": api_key},
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"J-Quants APIエラー: HTTP {error.code}: {error_body}") from error

    return json.loads(response_body)


# この関数の役割:
# J-Quantsの財務サマリー一覧を取得します。
def fetch_financial_summary_statements(api_key: str, stock_code: str) -> list[dict[str, Any]]:
    query_string = urlencode({"code": stock_code.strip().upper()})
    url = f"{JQUANTS_V2_BASE_URL}/fins/summary?{query_string}"
    response_json = request_json(url=url, api_key=api_key)
    statements = response_json.get("data") or response_json.get("statements") or response_json.get("summary") or []

    if not isinstance(statements, list):
        return []

    return statements


# この関数の役割:
# 無料プランなどで取得できる日付範囲外かどうかを確認するため、当日の日付指定を試します。
# なぜ必要か:
# データが無いのか、プラン上まだ見えないのかをユーザーに説明しやすくするためです。
def fetch_subscription_limit_note(api_key: str) -> str | None:
    query_string = urlencode({"date": date.today().isoformat()})
    url = f"{JQUANTS_V2_BASE_URL}/fins/summary?{query_string}"

    try:
        request_json(url=url, api_key=api_key)
    except ValueError as error:
        error_text = str(error)

        if "subscription covers" in error_text or "other plans" in error_text:
            return f"無料プランまたは契約プランの取得可能期間外の可能性があります。J-Quants応答: {error_text}"

        return None

    return None


# この関数の役割:
# 候補フィールドから、最初に取得できた値を返します。
def get_first_existing_field(statement: dict[str, Any], field_candidates: list[str]) -> tuple[Any, str]:
    for field_name in field_candidates:
        value = statement.get(field_name)

        if value is None or value == "":
            continue

        return value, field_name

    return NOT_ACQUIRED, "/".join(field_candidates)


# この関数の役割:
# J-Quantsの1件のstatementを一覧表示用の形へ整えます。
def create_statement_summary(statement: dict[str, Any]) -> JQuantsStatementSummary:
    sales, _ = get_first_existing_field(statement, SALES_FIELD_CANDIDATES)
    operating_profit, _ = get_first_existing_field(statement, OPERATING_PROFIT_FIELD_CANDIDATES)
    net_income, _ = get_first_existing_field(statement, NET_INCOME_FIELD_CANDIDATES)
    eps, _ = get_first_existing_field(statement, EPS_FIELD_CANDIDATES)

    return JQuantsStatementSummary(
        disclosed_date=str(statement.get("DiscDate") or statement.get("DisclosedDate") or NOT_ACQUIRED),
        document_type=str(statement.get("DocType") or statement.get("TypeOfDocument") or NOT_ACQUIRED),
        current_period_type=str(statement.get("CurPerType") or statement.get("TypeOfCurrentPeriod") or NOT_ACQUIRED),
        current_period_end=str(statement.get("CurPerEn") or statement.get("CurrentPeriodEndDate") or NOT_ACQUIRED),
        current_fiscal_year_end=str(statement.get("CurFYEn") or statement.get("CurrentFiscalYearEndDate") or NOT_ACQUIRED),
        sales=sales,
        operating_profit=operating_profit,
        net_income=net_income,
        eps=eps,
    )


# この関数の役割:
# ユーザー指定の期間に一致するstatementを探します。
def find_matching_statement(
    statements: list[dict[str, Any]],
    period_type: str,
    fiscal_year_end: str,
) -> dict[str, Any] | None:
    matching_statements = []

    for statement in statements:
        statement_period_type = str(statement.get("CurPerType") or statement.get("TypeOfCurrentPeriod") or "").upper()
        statement_fiscal_year_end = str(statement.get("CurFYEn") or statement.get("CurrentFiscalYearEndDate") or "")

        if statement_period_type == period_type.upper() and statement_fiscal_year_end == fiscal_year_end:
            matching_statements.append(statement)

    if len(matching_statements) == 0:
        return None

    # 同じ期間のデータが複数ある場合は、開示日が新しいものを使います。
    # 訂正開示などがあった場合、古いデータより新しいデータを優先するためです。
    return sorted(
        matching_statements,
        key=lambda statement: str(statement.get("DiscDate") or statement.get("DisclosedDate") or ""),
        reverse=True,
    )[0]


# この関数の役割:
# 選択されたstatementから、正式データ候補として使える主要財務項目を作ります。
def create_formal_data_items(selected_statement: dict[str, Any] | None) -> dict[str, JQuantsDataItem]:
    item_definitions = {
        "sales": ("売上", SALES_FIELD_CANDIDATES),
        "operating_profit": ("営業利益", OPERATING_PROFIT_FIELD_CANDIDATES),
        "net_income": ("純利益", NET_INCOME_FIELD_CANDIDATES),
        "eps": ("EPS", EPS_FIELD_CANDIDATES),
    }
    formal_data_items = {}

    for item_key, (display_name, field_candidates) in item_definitions.items():
        if selected_statement is None:
            formal_data_items[item_key] = JQuantsDataItem(
                value=NOT_ACQUIRED,
                unit="-",
                period_end="-",
                source=SOURCE_JQUANTS,
                raw_field_name="/".join(field_candidates),
                status=STATUS_NOT_ACQUIRED,
                note=f"ユーザー指定の期間に一致するstatementがないため、{display_name}は正式データとして扱いません。",
            )
            continue

        value, raw_field_name = get_first_existing_field(selected_statement, field_candidates)
        period_end = str(selected_statement.get("CurPerEn") or selected_statement.get("CurrentPeriodEndDate") or NOT_ACQUIRED)

        if value == NOT_ACQUIRED:
            status = STATUS_NOT_ACQUIRED
            note = f"期間は一致しましたが、J-Quantsの該当フィールドから{display_name}を取得できませんでした。"
        else:
            status = STATUS_ACQUIRED
            note = "ユーザー指定の期間と一致したため、正式データ候補として扱えます。"

        formal_data_items[item_key] = JQuantsDataItem(
            value=value,
            unit="円",
            period_end=period_end,
            source=SOURCE_JQUANTS,
            raw_field_name=raw_field_name,
            status=status,
            note=note,
        )

    return formal_data_items


# この関数の役割:
# J-Quantsデータを取得し、ユーザー指定期間と一致するかを確認します。
def check_jquants_period_consistency(
    api_key: str | None,
    stock_code: str | None,
    period_type: str | None,
    fiscal_year_end: str | None,
) -> JQuantsPeriodCheckResult | None:
    if api_key is None or api_key.strip() == "":
        return None

    if stock_code is None or stock_code.strip() == "":
        return None

    if period_type is None or period_type.strip() == "":
        return None

    if fiscal_year_end is None or fiscal_year_end.strip() == "":
        return None

    statements = fetch_financial_summary_statements(api_key=api_key.strip(), stock_code=stock_code.strip())
    selected_statement = find_matching_statement(
        statements=statements,
        period_type=period_type.strip(),
        fiscal_year_end=fiscal_year_end.strip(),
    )
    statement_summaries = [create_statement_summary(statement) for statement in statements]
    selected_statement_summary = create_statement_summary(selected_statement) if selected_statement is not None else None
    subscription_note = None

    if selected_statement is None:
        subscription_note = fetch_subscription_limit_note(api_key=api_key.strip())
        warning_message = (
            "WARNING: ユーザー指定の決算期と一致するJ-Quants statementが見つかりませんでした。"
            "期間が一致しないAPIデータは分析やPER計算に使いません。"
        )
    else:
        warning_message = None

    return JQuantsPeriodCheckResult(
        requested_period_type=period_type.strip(),
        requested_fiscal_year_end=fiscal_year_end.strip(),
        is_period_matched=selected_statement is not None,
        warning_message=warning_message,
        subscription_note=subscription_note,
        selected_statement=selected_statement_summary,
        statements=statement_summaries,
        formal_data_items=create_formal_data_items(selected_statement),
    )
