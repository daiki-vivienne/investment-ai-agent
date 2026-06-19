# このファイルの役割:
# PDFから抽出したテキストをOpenAI APIに渡し、投資家目線の定性分析レポートを作ります。

MAX_INPUT_TEXT_LENGTH = 30000


# この関数の役割:
# API正式データが取得できているかを、AIに渡す文脈から判定します。
# なぜ必要か:
# 正式データが未取得のときは、通常より厳しい安全ルールをAIプロンプトに追加するためです。
def is_formal_api_data_missing(api_context_markdown: str) -> bool:
    return "正式データ取得状態: 未取得" in api_context_markdown


# この関数の役割:
# PDFテキストが長すぎる場合に、AIへ送る文字数を制限します。
def shorten_text_for_ai(extracted_pdf_text: str) -> str:
    if len(extracted_pdf_text) <= MAX_INPUT_TEXT_LENGTH:
        return extracted_pdf_text

    shortened_text = extracted_pdf_text[:MAX_INPUT_TEXT_LENGTH]
    notice_text = (
        "\n\n[注意] PDFのテキストが長いため、先頭部分のみを使って分析しています。"
        "将来バージョンでは分割要約に対応する予定です。"
    )

    return shortened_text + notice_text


# この関数の役割:
# AIに渡す指示文を作ります。
# なぜ必要か:
# PDFは定性情報、投資指標はAPIデータという役割に分けるためです。
def build_analysis_prompt(
    extracted_pdf_text: str,
    api_market_data_json: str,
    api_context_markdown: str,
) -> str:
    formal_data_missing = is_formal_api_data_missing(api_context_markdown)
    score_instruction = """
成長性：0〜100点
- 理由:

収益性：0〜100点
- 理由:

財務健全性：0〜100点
- 理由:

将来性：0〜100点
- 理由:
""".strip()

    if formal_data_missing:
        mode_specific_rules = """
正式データ未取得時の追加ルール:
- 業績の良し悪しを断定しないでください。
- PDF上の数値や定量表現は本文に転記しないでください。
- 「好調」「大幅成長」「利益を押し上げた」「改善した」「過去最高」「約2倍」「利益率が高い」などの定量評価表現を使わないでください。
- PDFに定量情報がある場合は、「PDF上の記述では、業績や財務に関する定量情報が掲載されていますが、API正式データ未取得のため本レポートでは数値を転記しません。」と書いてください。
- AIスコアは点数を出さず「未取得」としてください。
""".strip()
        score_instruction = """
成長性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。

収益性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。

財務健全性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。

将来性：未取得
- 理由: ユーザー指定期間と一致するAPI正式データが未取得のため、数値スコアは出しません。
""".strip()
    else:
        mode_specific_rules = """
正式データ取得済み時の追加ルール:
- 業績サマリーはAI本文では作らないでください。レポート先頭の「API正式業績サマリー」を正とします。
- 売上、営業利益、純利益、EPSの具体的な数値をAI本文で再出力しないでください。
- AIスコアは0〜100点で算出してください。
- AIスコアの理由では、レポート先頭のAPI正式業績サマリーにある項目だけを数値根拠にしてください。
- PDF由来の数値や定量表現は、正式データに含まれない項目の補完やAIスコアの根拠には使わないでください。
- D/Eレシオ、フリーキャッシュフロー、借入金、過去最高、前年比、利益率には触れないでください。これらはAPI正式業績サマリーに含まれていないためです。
- PERは入力情報の「PER分析」セクションにある場合のみ言及してください。PDFからPERを推測しないでください。
- PERを表現するときは「直近PER」「会社予想EPSベースの予想PER」「次期予想PER候補」の違いを混同しないでください。
- PER、株価、EPS、FEPS、NxFEPSの具体的な数値はAI本文で再出力しないでください。レポート先頭の「PER分析」を参照する形にしてください。
- セグメント別売上や用途別寄与はAPI正式業績サマリーに含まれていないため、「業績を押し上げた」「売上に寄与した」と断定しないでください。
""".strip()

    return f"""
あなたは決算資料を読む投資分析アシスタントです。
以下のAPI由来データと決算PDFテキストを読み、単なる要約ではなく、投資家目線で分析してください。

重要な前提:
- これは投資助言ではなく、学習・調査用の分析メモです。
- PDFは、事業内容、成長要因、リスク、経営陣の説明などの定性情報を読むために使ってください。
- PDFから売上、営業利益、純利益、EPSの具体的な数値を抜き出して本文に書かないでください。
- 売上、営業利益、純利益、EPS、FEPS、NxFEPSなどの正式データは、期間一致したJ-Quants正式データだけを使います。
- yfinance由来データは参考市場データです。正式な財務データとして扱わないでください。
- 期間が一致しないAPIデータやPDF由来の数値は、投資指標計算や断定的な定量評価に使わないでください。
- APIに無い数字は、推測せず「未取得」と書いてください。
- PDF由来の定量的な記述は、必ず「PDF上の主な記述」セクションに分け、数値は転記しないでください。
- API正式業績サマリーに含まれない数値や定量評価は、AI本文で断定しないでください。
- AI、データセンター、NAND需要などのテーマは、PDF上の事業テーマとして扱い、業績への寄与度を断定しないでください。
- ポジティブ要因だけでなく、リスク要因も投資家目線で冷静に書いてください。
- 初心者にも分かる言葉を使い、専門用語には短い補足を入れてください。
- 出力はMarkdownのみで返してください。
- 「API由来データと期間整合性」は入力情報です。出力本文の最後にそのまま貼り付けないでください。

{mode_specific_rules}

必ず以下のMarkdown構成で出力してください。

# 決算分析レポート

## 会社概要
- 何をしている会社か
- 主力事業は何か

## PDF上の主な記述
- PDFに記載された定性情報を中心に書いてください。
- PDF内の具体的な数値を転記しないでください。
- 「過去最高」「大幅増加」「改善」などの定量評価表現も転記しないでください。

## ポジティブ要因
- 成長している事業
- 利益改善要因
- 経営陣が強調しているポイント

## リスク要因
- 利益悪化リスク
- 市場環境リスク
- 競争リスク
- 財務リスク

## 半導体・AI観点の分析
- AI需要との関連性
- データセンター需要との関連性
- NANDフラッシュ市場への影響
- メモリ市場のサイクルとの関係
- 業績への影響は「可能性があります」「注目点です」のように表現し、「押し上げています」「寄与しています」と断定しないでください。

## 今後注目すべき指標
次回決算で確認すべき項目を箇条書きで出力してください。

## PER分析メモ
- 入力情報のPER分析セクションをもとに、PERが取得済みか未取得かを書いてください。
- PERが未取得の場合は、「ユーザー指定期間と一致するJ-Quants正式EPSが未取得のため、PERは計算しません。」のように、PER計算できない理由を書いてください。
- PER未取得の理由に「AIスコア」「数値スコア」という言葉を使わないでください。
- PERが取得済みの場合は、具体的な株価、EPS、FEPS、NxFEPS、PERの数値を再掲せず、データ元と計算根拠だけを書いてください。
- PERが取得済みの場合も、株価は現在時点、EPSは指定決算期の実績値であることを書いてください。
- 予想PERが取得済みの場合も、J-Quants FEPSを使った会社予想EPSベースの予想PERであり、アナリスト予想PERではないことを書いてください。
- 次期予想PER候補が取得済みの場合も、J-Quants NxFEPSを使った候補値であり、フィールド定義確認が必要なことを書いてください。
- 入力情報のPER分析セクションでEPS対象期間がFY以外の場合は、「このEPSは通期実績EPSや予想EPSではありません」と必ず書いてください。

## 初心者向け解説
投資初心者にも分かる言葉で、「この決算は良かったのか、悪かったのか」を3〜5行で説明してください。

## 投資メモ
投資家として覚えておくべきポイントを箇条書きでまとめてください。

## AIスコア

{score_instruction}

API由来データと期間整合性:
{api_context_markdown}

yfinance由来の参考市場データ:
{api_market_data_json}

決算PDFテキスト:
{extracted_pdf_text}
""".strip()


# この関数の役割:
# OpenAI APIを呼び出して、Markdown形式の分析レポートを作成します。
def analyze_financial_report(
    extracted_pdf_text: str,
    api_market_data_json: str,
    openai_api_key: str,
    openai_model: str,
    api_context_markdown: str = "APIデータは未取得です。",
) -> str:
    try:
        from openai import OpenAI
    except ModuleNotFoundError:
        raise ValueError("openaiがインストールされていません。pip install -r requirements.txt を実行してください。")

    text_for_ai = shorten_text_for_ai(extracted_pdf_text)
    analysis_prompt = build_analysis_prompt(
        extracted_pdf_text=text_for_ai,
        api_market_data_json=api_market_data_json,
        api_context_markdown=api_context_markdown,
    )

    client = OpenAI(api_key=openai_api_key)

    try:
        response = client.chat.completions.create(
            model=openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは決算資料を読み、投資家目線で分かりやすい分析メモを作るアシスタントです。",
                },
                {
                    "role": "user",
                    "content": analysis_prompt,
                },
            ],
            temperature=0.2,
        )
    except Exception as error:
        raise ValueError(f"OpenAI APIの呼び出しに失敗しました: {error}")

    analysis_markdown = response.choices[0].message.content

    if analysis_markdown is None or analysis_markdown.strip() == "":
        raise ValueError("AIから分析結果が返ってきませんでした。もう一度実行してみてください。")

    return analysis_markdown
