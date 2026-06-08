# このファイルの役割:
# 企業に関連する市場規模分析の土台を作ります。

from src.data_models import EXTERNAL_DATA_REQUIRED, MarketSizeAnalysisResult


# この関数の役割:
# 市場規模分析の初期データを作ります。
# なぜ必要か:
# 市場規模は決算PDFだけでは網羅できないため、外部市場データが必要であることを明示します。
def create_market_size_analysis() -> list[MarketSizeAnalysisResult]:
    market_size_results = [
        MarketSizeAnalysisResult(
            market_name="NAND市場",
            three_years_later=EXTERNAL_DATA_REQUIRED,
            five_years_later=EXTERNAL_DATA_REQUIRED,
            ten_years_later=EXTERNAL_DATA_REQUIRED,
            note="NAND市場の市場規模データや調査レポートが必要です。",
        ),
        MarketSizeAnalysisResult(
            market_name="SSD市場",
            three_years_later=EXTERNAL_DATA_REQUIRED,
            five_years_later=EXTERNAL_DATA_REQUIRED,
            ten_years_later=EXTERNAL_DATA_REQUIRED,
            note="SSD市場の出荷数量、単価、市場規模データが必要です。",
        ),
        MarketSizeAnalysisResult(
            market_name="AIデータセンター市場",
            three_years_later=EXTERNAL_DATA_REQUIRED,
            five_years_later=EXTERNAL_DATA_REQUIRED,
            ten_years_later=EXTERNAL_DATA_REQUIRED,
            note="AIサーバー投資、データセンター投資、メモリ需要の外部データが必要です。",
        ),
    ]

    return market_size_results


# この関数の役割:
# 市場規模分析結果をMarkdown表に変換します。
def format_market_size_analysis_as_markdown(market_size_results: list[MarketSizeAnalysisResult]) -> str:
    markdown_lines = [
        "## 市場規模分析",
        "",
        "| 市場 | 3年後 | 5年後 | 10年後 | 補足 |",
        "| ---- | ---- | ---- | ---- | ---- |",
    ]

    for market_size_result in market_size_results:
        markdown_lines.append(
            "| "
            f"{market_size_result.market_name} | "
            f"{market_size_result.three_years_later} | "
            f"{market_size_result.five_years_later} | "
            f"{market_size_result.ten_years_later} | "
            f"{market_size_result.note} |"
        )

    return "\n".join(markdown_lines)
