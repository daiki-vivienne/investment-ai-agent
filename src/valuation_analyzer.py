# このファイルの役割:
# API由来の正式EPSと株価を使って、PERなどの投資指標を計算します。
#
# 注意:
# PDF由来のEPSは使いません。
# ユーザー指定期間と一致したJ-Quants正式EPSが取得できた場合だけ、PER計算に進みます。

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.jquants_client import JQuantsPeriodCheckResult, NOT_ACQUIRED, STATUS_ACQUIRED


@dataclass
class PerAnalysisResult:
    # このクラスの役割:
    # PER分析に必要な値と、取得状態・注意点をひとまとめにします。
    current_price: Any
    eps: Any
    eps_period_type: str
    per: Any
    per_type: str
    status: str
    price_source: str
    eps_source: str
    as_of_date: str
    note: str


# この関数の役割:
# 日本株コードをyfinance用tickerに変換します。
def convert_stock_code_to_yfinance_ticker(stock_code: str) -> str:
    cleaned_stock_code = stock_code.strip().upper()

    if cleaned_stock_code.endswith(".T"):
        return cleaned_stock_code

    return f"{cleaned_stock_code}.T"


# この関数の役割:
# yfinanceから現在株価を取得します。
# なぜ必要か:
# PERは「株価 ÷ EPS」で計算するため、株価が必要です。
def fetch_current_price_from_yfinance(stock_code: str) -> tuple[Any, str]:
    try:
        import yfinance as yf
    except ModuleNotFoundError:
        raise ValueError("yfinanceがインストールされていません。pip install -r requirements.txt を実行してください。")

    ticker_symbol = convert_stock_code_to_yfinance_ticker(stock_code)
    stock_ticker = yf.Ticker(ticker_symbol)
    info_dictionary = stock_ticker.info

    current_price = info_dictionary.get("currentPrice") or info_dictionary.get("regularMarketPrice")

    if current_price is None:
        return NOT_ACQUIRED, "currentPrice / regularMarketPrice"

    return current_price, "currentPrice / regularMarketPrice"


# この関数の役割:
# J-Quants正式EPSとyfinance株価からPERを計算します。
def calculate_per_analysis(
    stock_code: str | None,
    period_check_result: JQuantsPeriodCheckResult | None,
) -> PerAnalysisResult | None:
    eps_period_type = period_check_result.requested_period_type if period_check_result is not None else "-"

    if stock_code is None or stock_code.strip() == "":
        return None

    if period_check_result is None or not period_check_result.is_period_matched:
        return PerAnalysisResult(
            current_price=NOT_ACQUIRED,
            eps=NOT_ACQUIRED,
            eps_period_type=eps_period_type,
            per=NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="ユーザー指定期間と一致するJ-Quants正式EPSが未取得のため、PERは計算しません。",
        )

    eps_item = period_check_result.formal_data_items.get("eps")

    if eps_item is None or eps_item.status != STATUS_ACQUIRED:
        return PerAnalysisResult(
            current_price=NOT_ACQUIRED,
            eps=NOT_ACQUIRED,
            eps_period_type=eps_period_type,
            per=NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="J-Quants正式EPSが未取得のため、PERは計算しません。",
        )

    try:
        eps_value = float(eps_item.value)
    except (TypeError, ValueError):
        return PerAnalysisResult(
            current_price=NOT_ACQUIRED,
            eps=eps_item.value,
            eps_period_type=eps_period_type,
            per=NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="J-Quants正式EPSを数値に変換できないため、PERは計算しません。",
        )

    if eps_value <= 0:
        return PerAnalysisResult(
            current_price=NOT_ACQUIRED,
            eps=eps_item.value,
            eps_period_type=eps_period_type,
            per=NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="EPSが0以下のため、PERは計算しません。",
        )

    try:
        current_price, raw_price_field_name = fetch_current_price_from_yfinance(stock_code)
    except ValueError as error:
        return PerAnalysisResult(
            current_price=NOT_ACQUIRED,
            eps=eps_item.value,
            eps_period_type=eps_period_type,
            per=NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source=f"J-Quants {eps_item.raw_field_name}",
            as_of_date="-",
            note=f"株価取得に失敗したため、PERは計算しません。詳細: {error}",
        )

    if current_price == NOT_ACQUIRED:
        return PerAnalysisResult(
            current_price=NOT_ACQUIRED,
            eps=eps_item.value,
            eps_period_type=eps_period_type,
            per=NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source=f"J-Quants {eps_item.raw_field_name}",
            as_of_date="-",
            note="yfinanceから現在株価を取得できなかったため、PERは計算しません。",
        )

    per_value = float(current_price) / eps_value
    non_fy_note = ""

    if eps_period_type.upper() != "FY":
        non_fy_note = f" このEPSは{eps_period_type}の実績EPSであり、通期実績EPSや予想EPSではありません。"

    return PerAnalysisResult(
        current_price=current_price,
        eps=eps_value,
        eps_period_type=eps_period_type,
        per=round(per_value, 2),
        per_type="現在株価ベースの実績PER",
        status="取得済み",
        price_source=f"yfinance {raw_price_field_name}",
        eps_source=f"J-Quants {eps_item.raw_field_name}",
        as_of_date=f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        note=(
            "現在株価ベースの実績PERです。株価はyfinanceの現在株価、EPSはユーザー指定期間と一致したJ-Quants実績EPSを使っています。"
            "株価時点とEPS対象期間は異なります。"
            f"{non_fy_note}"
        ),
    )
