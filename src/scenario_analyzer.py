# このファイルの役割:
# 1年後の株価をシナリオ別に整理するための土台を作ります。

from src.data_models import EXTERNAL_DATA_REQUIRED, ScenarioAnalysisResult


# この関数の役割:
# 上振れ、通常、下振れの3つのシナリオ分析結果を作ります。
# なぜ必要か:
# 現時点では株価や成長率の外部データが無いため、予測値を推測で作らず、必要データを明示するためです。
def create_scenario_analysis() -> list[ScenarioAnalysisResult]:
    scenario_results = [
        ScenarioAnalysisResult(
            scenario_name="上振れ",
            stock_price=EXTERNAL_DATA_REQUIRED,
            cagr=EXTERNAL_DATA_REQUIRED,
            reason="売上成長率、EPS成長率、想定PER、現在株価などの外部データが必要です。",
        ),
        ScenarioAnalysisResult(
            scenario_name="通常",
            stock_price=EXTERNAL_DATA_REQUIRED,
            cagr=EXTERNAL_DATA_REQUIRED,
            reason="会社予想、コンセンサス予想、現在株価などの外部データが必要です。",
        ),
        ScenarioAnalysisResult(
            scenario_name="下振れ",
            stock_price=EXTERNAL_DATA_REQUIRED,
            cagr=EXTERNAL_DATA_REQUIRED,
            reason="業績悪化時のEPS、想定PER、市場環境データなどの外部データが必要です。",
        ),
    ]

    return scenario_results


# この関数の役割:
# シナリオ分析結果をMarkdown表に変換します。
def format_scenario_analysis_as_markdown(scenario_analysis_results: list[ScenarioAnalysisResult]) -> str:
    markdown_lines = [
        "## シナリオ別株価予測",
        "",
        "断定的な予言ではなく、将来データを入れて比較するためのシナリオ分析です。",
        "",
        "| シナリオ | 株価 | CAGR | 要因 |",
        "| ---- | -- | ---- | -- |",
    ]

    for scenario_analysis_result in scenario_analysis_results:
        markdown_lines.append(
            "| "
            f"{scenario_analysis_result.scenario_name} | "
            f"{scenario_analysis_result.stock_price} | "
            f"{scenario_analysis_result.cagr} | "
            f"{scenario_analysis_result.reason} |"
        )

    return "\n".join(markdown_lines)
