# このファイルの役割:
# 株価などの市場データを外部サービスから取得します。

from src.data_models import MarketDataResult, NOT_ACQUIRED


# この関数の役割:
# 入力された証券コードをyfinanceで使えるtickerに変換します。
# なぜ必要か:
# 日本株はyfinanceでは「285A.T」のように末尾へ「.T」を付ける必要があるためです。
def normalize_ticker_for_yfinance(ticker: str, is_japanese_stock: bool = True) -> str:
    cleaned_ticker = ticker.strip()

    if cleaned_ticker == "":
        return ""

    if is_japanese_stock and not cleaned_ticker.upper().endswith(".T"):
        return f"{cleaned_ticker}.T"

    return cleaned_ticker


# この関数の役割:
# yfinanceを使って現在株価を取得します。
# なぜ必要か:
# Ver0.1では試作用としてyfinanceを使いますが、将来はこのファイルをJ-Quants API実装に差し替えやすくするためです。
def format_market_cap(market_cap: float | None) -> str:
    # この関数の役割:
    # 時価総額を読みやすい表示に変換します。
    if market_cap is None:
        return NOT_ACQUIRED

    market_cap_in_hundred_million_yen = market_cap / 100000000

    return f"{market_cap_in_hundred_million_yen:,.0f}億円"


# この関数の役割:
# yfinanceを使って現在株価、EPS、PBR、時価総額を取得します。
# なぜ必要か:
# PERなどの投資指標はPDF由来ではなくAPI由来データで計算する方針にするためです。
def fetch_market_data(ticker: str, is_japanese_stock: bool = True) -> MarketDataResult:
    normalized_ticker = normalize_ticker_for_yfinance(
        ticker=ticker,
        is_japanese_stock=is_japanese_stock,
    )

    if normalized_ticker == "":
        return MarketDataResult(
            requested_ticker=ticker,
            normalized_ticker=NOT_ACQUIRED,
            current_stock_price=None,
            display_current_stock_price=NOT_ACQUIRED,
            sales=None,
            display_sales=NOT_ACQUIRED,
            operating_profit=None,
            display_operating_profit=NOT_ACQUIRED,
            net_income=None,
            display_net_income=NOT_ACQUIRED,
            eps=None,
            display_eps=NOT_ACQUIRED,
            pbr=None,
            display_pbr=NOT_ACQUIRED,
            market_cap=None,
            display_market_cap=NOT_ACQUIRED,
            data_source="yfinance",
            note="証券コードが指定されていません。",
        )

    try:
        import yfinance as yf
    except ModuleNotFoundError:
        return MarketDataResult(
            requested_ticker=ticker,
            normalized_ticker=normalized_ticker,
            current_stock_price=None,
            display_current_stock_price=NOT_ACQUIRED,
            sales=None,
            display_sales=NOT_ACQUIRED,
            operating_profit=None,
            display_operating_profit=NOT_ACQUIRED,
            net_income=None,
            display_net_income=NOT_ACQUIRED,
            eps=None,
            display_eps=NOT_ACQUIRED,
            pbr=None,
            display_pbr=NOT_ACQUIRED,
            market_cap=None,
            display_market_cap=NOT_ACQUIRED,
            data_source="yfinance",
            note="yfinanceがインストールされていません。pip install -r requirements.txt を実行してください。",
        )

    try:
        stock_ticker = yf.Ticker(normalized_ticker)
        recent_price_history = stock_ticker.history(period="5d")

        if recent_price_history.empty:
            return MarketDataResult(
                requested_ticker=ticker,
                normalized_ticker=normalized_ticker,
                current_stock_price=None,
                display_current_stock_price=NOT_ACQUIRED,
                sales=None,
                display_sales=NOT_ACQUIRED,
                operating_profit=None,
                display_operating_profit=NOT_ACQUIRED,
                net_income=None,
                display_net_income=NOT_ACQUIRED,
                eps=None,
                display_eps=NOT_ACQUIRED,
                pbr=None,
                display_pbr=NOT_ACQUIRED,
                market_cap=None,
                display_market_cap=NOT_ACQUIRED,
                data_source="yfinance",
                note="yfinanceから株価データを取得できませんでした。",
            )

        latest_close_price = recent_price_history["Close"].dropna().iloc[-1]
        current_stock_price = float(latest_close_price)
        stock_info = stock_ticker.info
        eps = stock_info.get("trailingEps")
        pbr = stock_info.get("priceToBook")
        market_cap = stock_info.get("marketCap")

        return MarketDataResult(
            requested_ticker=ticker,
            normalized_ticker=normalized_ticker,
            current_stock_price=current_stock_price,
            display_current_stock_price=f"{current_stock_price:,.1f}円",
            sales=None,
            display_sales=NOT_ACQUIRED,
            operating_profit=None,
            display_operating_profit=NOT_ACQUIRED,
            net_income=None,
            display_net_income=NOT_ACQUIRED,
            eps=float(eps) if eps is not None else None,
            display_eps=f"{float(eps):,.2f}円" if eps is not None else NOT_ACQUIRED,
            pbr=float(pbr) if pbr is not None else None,
            display_pbr=f"{float(pbr):.2f}倍" if pbr is not None else NOT_ACQUIRED,
            market_cap=float(market_cap) if market_cap is not None else None,
            display_market_cap=format_market_cap(float(market_cap)) if market_cap is not None else NOT_ACQUIRED,
            data_source="yfinance",
            note="yfinanceから取得したデータです。試作用のため、将来はJ-Quants APIへ差し替える想定です。",
        )

    except Exception as error:
        return MarketDataResult(
            requested_ticker=ticker,
            normalized_ticker=normalized_ticker,
            current_stock_price=None,
            display_current_stock_price=NOT_ACQUIRED,
            sales=None,
            display_sales=NOT_ACQUIRED,
            operating_profit=None,
            display_operating_profit=NOT_ACQUIRED,
            net_income=None,
            display_net_income=NOT_ACQUIRED,
            eps=None,
            display_eps=NOT_ACQUIRED,
            pbr=None,
            display_pbr=NOT_ACQUIRED,
            market_cap=None,
            display_market_cap=NOT_ACQUIRED,
            data_source="yfinance",
            note=f"株価取得に失敗しました: {error}",
        )


# この関数の役割:
# 既存コードとの互換用に、現在株価取得の名前を残します。
# 今後は fetch_market_data を使う方針です。
def fetch_current_stock_price(ticker: str, is_japanese_stock: bool = True) -> MarketDataResult:
    return fetch_market_data(ticker=ticker, is_japanese_stock=is_japanese_stock)
