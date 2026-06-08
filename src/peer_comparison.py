# このファイルの役割:
# 同業他社との相対比較を行うための土台を作ります。

from src.data_models import NOT_ACQUIRED, PeerComparisonResult


# この関数の役割:
# 同業比較の初期データを作ります。
# なぜ必要か:
# 自社スコアだけでは高いのか低いのか分かりにくいため、将来は業界平均や中央値と比較できるようにします。
def create_peer_comparison() -> list[PeerComparisonResult]:
    comparison_results = [
        PeerComparisonResult(
            score_name="成長性",
            company_score=None,
            industry_median=NOT_ACQUIRED,
            industry_average=NOT_ACQUIRED,
            percentile_rank=NOT_ACQUIRED,
            note="比較対象データが未取得です。",
        ),
        PeerComparisonResult(
            score_name="収益性",
            company_score=None,
            industry_median=NOT_ACQUIRED,
            industry_average=NOT_ACQUIRED,
            percentile_rank=NOT_ACQUIRED,
            note="比較対象データが未取得です。",
        ),
        PeerComparisonResult(
            score_name="財務健全性",
            company_score=None,
            industry_median=NOT_ACQUIRED,
            industry_average=NOT_ACQUIRED,
            percentile_rank=NOT_ACQUIRED,
            note="比較対象データが未取得です。",
        ),
        PeerComparisonResult(
            score_name="将来性",
            company_score=None,
            industry_median=NOT_ACQUIRED,
            industry_average=NOT_ACQUIRED,
            percentile_rank=NOT_ACQUIRED,
            note="比較対象データが未取得です。",
        ),
    ]

    return comparison_results


# この関数の役割:
# 同業比較結果をMarkdown表に変換します。
def format_peer_comparison_as_markdown(comparison_results: list[PeerComparisonResult]) -> str:
    markdown_lines = [
        "## 同業他社比較",
        "",
        "| 指標 | 自社スコア | 業界中央値 | 業界平均 | 上位何%か | 補足 |",
        "| ---- | ---- | ---- | ---- | ---- | ---- |",
    ]

    for comparison_result in comparison_results:
        company_score_text = NOT_ACQUIRED

        if comparison_result.company_score is not None:
            company_score_text = f"{comparison_result.company_score}点"

        markdown_lines.append(
            "| "
            f"{comparison_result.score_name} | "
            f"{company_score_text} | "
            f"{comparison_result.industry_median} | "
            f"{comparison_result.industry_average} | "
            f"{comparison_result.percentile_rank} | "
            f"{comparison_result.note} |"
        )

    return "\n".join(markdown_lines)
