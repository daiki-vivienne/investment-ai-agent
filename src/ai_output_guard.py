# このファイルの役割:
# AIが作ったMarkdown本文を安全側に補正します。
#
# なぜ必要か:
# プロンプトだけでは、AIがPDF由来の「過去最高」「FCF」「借入金」などを
# AIスコアや投資メモの根拠に使ってしまうことがあります。
# 数値の正確性を優先するため、危険な表現を含むセクションは固定文に差し替えます。

from src.jquants_client import JQuantsPeriodCheckResult

SECTION_HEADERS = [
    "## 会社概要",
    "## PDF上の主な記述",
    "## ポジティブ要因",
    "## リスク要因",
    "## 半導体・AI観点の分析",
    "## 今後注目すべき指標",
    "## PER分析メモ",
    "## 初心者向け解説",
    "## 投資メモ",
    "## AIスコア",
]

UNSAFE_PDF_QUANT_WORDS = [
    "過去最高",
    "大幅",
    "改善",
    "約2倍",
    "3倍",
    "前年比",
    "前年同期比",
    "利益率",
    "フリーキャッシュフロー",
    "キャッシュフロー",
    "借入金",
    "D/E",
]

UNSAFE_SCORE_WORDS = [
    "過去最高",
    "前年比",
    "前年同期比",
    "利益率",
    "フリーキャッシュフロー",
    "キャッシュフロー",
    "借入金",
    "D/E",
    "改善",
]


# この関数の役割:
# Markdownを見出しごとのセクションに分けます。
def split_markdown_sections(markdown_text: str) -> dict[str, str]:
    sections = {}
    current_header = ""
    current_lines = []

    for line in markdown_text.splitlines():
        if line.startswith("## "):
            if current_header != "":
                sections[current_header] = "\n".join(current_lines).strip()

            current_header = line.strip()
            current_lines = [line]
            continue

        if current_header == "":
            current_header = "__preamble__"
            current_lines = []

        current_lines.append(line)

    if current_header != "":
        sections[current_header] = "\n".join(current_lines).strip()

    return sections


# この関数の役割:
# もとの順番に近い形でMarkdownセクションを結合します。
def join_markdown_sections(sections: dict[str, str]) -> str:
    ordered_sections = []

    if "__preamble__" in sections and sections["__preamble__"].strip() != "":
        ordered_sections.append(sections["__preamble__"].strip())

    for section_header in SECTION_HEADERS:
        section_text = sections.get(section_header)

        if section_text is None or section_text.strip() == "":
            continue

        ordered_sections.append(section_text.strip())

    return "\n\n".join(ordered_sections).strip()


# この関数の役割:
# 指定した危険語がセクション内に含まれるか確認します。
def contains_unsafe_word(section_text: str, unsafe_words: list[str]) -> bool:
    return any(unsafe_word in section_text for unsafe_word in unsafe_words)


# この関数の役割:
# PDF上の主な記述セクションを安全な固定文にします。
def build_safe_pdf_notes_section() -> str:
    return """
## PDF上の主な記述

- PDF上の記述では、事業内容、需要テーマ、経営方針、リスク要因などが説明されています。
- PDF内には業績や財務に関する定量情報も掲載されていますが、AIによる数値転記ミスを避けるため、本レポート本文では具体的な数値や定量評価表現を転記しません。
- 投資指標計算やAIスコアでは、期間一致したAPI正式データのみを根拠として扱います。
""".strip()


# この関数の役割:
# ポジティブ要因を定性情報だけに寄せます。
def build_safe_positive_section() -> str:
    return """
## ポジティブ要因

- AI、データセンター、エンタープライズ向けストレージは、PDF上で重要な事業テーマとして言及されています。
- NANDフラッシュメモリやSSDに関する技術開発、世代更新、生産体制は、今後確認すべき事業上のポイントです。
- 利益改善要因や財務改善については、API正式業績サマリーに含まれていない項目を根拠に断定しません。
""".strip()


# この関数の役割:
# 初心者向け解説を、正式データと参考情報の違いが分かる内容に固定します。
def build_safe_beginner_section(is_period_matched: bool) -> str:
    if is_period_matched:
        return """
## 初心者向け解説

ユーザー指定期間と一致するJ-Quants正式データは取得できています。
ただし、PDF由来の数値や定量評価表現はAI本文の根拠にせず、売上・営業利益・純利益・EPSは「API正式業績サマリー」を確認します。
会社の事業テーマやリスクは参考になりますが、投資判断では正式データと追加調査を組み合わせて確認する必要があります。
""".strip()

    return """
## 初心者向け解説

API正式データが未取得のため、この決算の良し悪しは断定しません。
PDFには事業テーマや経営方針が書かれていますが、数値判断は期間一致したAPI正式データが取れるまで保留します。
まずは「期間整合性チェック」と「API正式業績サマリー」を確認することが重要です。
""".strip()


# この関数の役割:
# 投資メモを判断保留と確認事項中心にします。
def build_safe_investment_memo_section() -> str:
    return """
## 投資メモ

- 売上、営業利益、純利益、EPSは、AI本文ではなく「API正式業績サマリー」を確認します。
- PDF由来の定量表現は、投資指標計算やAIスコアの根拠には使いません。
- 追加で確認すべき項目は、同業比較、予想EPS、予想PER、財務指標、ニュース、市場環境です。
""".strip()


# この関数の役割:
# PER分析メモを、AIの言い忘れがあっても安全な固定文にします。
def build_safe_per_memo_section(period_check_result: JQuantsPeriodCheckResult | None) -> str:
    if period_check_result is None or not period_check_result.is_period_matched:
        return """
## PER分析メモ

- PERは未取得です。
- 理由: ユーザー指定期間と一致するJ-Quants正式データが未取得のため、直近PER・予想PER・次期予想PER候補は計算しません。
""".strip()

    period_type = period_check_result.requested_period_type
    non_fy_note = ""

    if period_type.upper() != "FY":
        non_fy_note = "\n- このEPSは通期実績EPSや予想EPSではありません。"

    return f"""
## PER分析メモ

- 直近PER、会社予想EPSベースの予想PER、次期予想PER候補の取得状態は、上部の「PER分析」セクションを確認してください。
- 株価データ元はyfinance、EPS/FEPS/NxFEPSのデータ元はJ-Quantsです。
- 株価は現在時点、EPS/FEPS/NxFEPSはJ-Quantsの期間一致statement内の値です。{non_fy_note}
""".strip()


# この関数の役割:
# AIスコアを、許可された正式データだけに基づく控えめな表現に補正します。
def build_safe_ai_score_section(is_period_matched: bool) -> str:
    if not is_period_matched:
        return """
## AIスコア

成長性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。

収益性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。

財務健全性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。

将来性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。
""".strip()

    return """
## AIスコア

成長性：70点
- 理由: J-Quants正式データで売上、営業利益、純利益、EPSは取得済みです。ただし前年比や業界比較は未取得のため、控えめに評価します。

収益性：70点
- 理由: J-Quants正式データで営業利益と純利益は取得済みです。ただし利益率や前年比は未取得のため、控えめに評価します。

財務健全性：未取得
- 理由: 自己資本比率、D/Eレシオ、キャッシュフローなどの正式データを本レポートでは取得していないため、数値スコアは出しません。

将来性：70点
- 理由: PDF上の事業テーマとしてAI・データセンター関連が確認できます。ただし市場規模、予想EPS、同業比較は未取得のため、控えめに評価します。
""".strip()


# この関数の役割:
# AI出力を安全なMarkdownへ補正します。
def guard_ai_analysis_markdown(
    analysis_markdown: str,
    period_check_result: JQuantsPeriodCheckResult | None,
) -> str:
    is_period_matched = period_check_result is not None and period_check_result.is_period_matched
    sections = split_markdown_sections(analysis_markdown)

    pdf_section = sections.get("## PDF上の主な記述", "")
    if contains_unsafe_word(pdf_section, UNSAFE_PDF_QUANT_WORDS):
        sections["## PDF上の主な記述"] = build_safe_pdf_notes_section()

    positive_section = sections.get("## ポジティブ要因", "")
    if contains_unsafe_word(positive_section, UNSAFE_PDF_QUANT_WORDS):
        sections["## ポジティブ要因"] = build_safe_positive_section()

    beginner_section = sections.get("## 初心者向け解説", "")
    if contains_unsafe_word(beginner_section, UNSAFE_PDF_QUANT_WORDS):
        sections["## 初心者向け解説"] = build_safe_beginner_section(is_period_matched)

    memo_section = sections.get("## 投資メモ", "")
    if contains_unsafe_word(memo_section, UNSAFE_PDF_QUANT_WORDS):
        sections["## 投資メモ"] = build_safe_investment_memo_section()

    # PERの具体的な数値は機械生成した表だけに表示し、
    # AIによる再転記や数値の取り違えを防ぐため、メモは常に固定文へ置き換えます。
    sections["## PER分析メモ"] = build_safe_per_memo_section(period_check_result)

    score_section = sections.get("## AIスコア", "")
    if contains_unsafe_word(score_section, UNSAFE_SCORE_WORDS):
        sections["## AIスコア"] = build_safe_ai_score_section(is_period_matched)

    return join_markdown_sections(sections)
