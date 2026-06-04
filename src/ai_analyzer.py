# このファイルの役割:
# PDFから抽出したテキストをOpenAI APIに渡し、投資家目線の分析レポートを作ります。

MAX_INPUT_TEXT_LENGTH = 30000


# この関数の役割:
# PDFテキストが長すぎる場合に、AIへ送る文字数を制限します。
# なぜ必要か:
# AIには一度に読める文字量の上限があるため、長すぎるPDFをそのまま送るとエラーになる可能性があります。
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
# 単なる要約ではなく、投資家が確認したい観点に沿って分析してもらうためです。
def build_analysis_prompt(extracted_pdf_text: str) -> str:
    return f"""
あなたは決算資料を読む投資分析アシスタントです。
以下の決算PDFテキストを読み、単なる要約ではなく、投資家目線で分析してください。

重要な前提:
- これは投資助言ではなく、学習・調査用の分析メモです。
- PDFテキストに書かれている事実を優先してください。
- 資料から確認できないことは、推測せず「資料からは確認できません」と書いてください。
- 数字が読み取れる場合は、売上、営業利益、純利益、前年同期比を具体的に書いてください。
- 数字が読み取れない場合は、無理に作らず「資料からは確認できません」と書いてください。
- ポジティブ要因だけでなく、リスク要因も投資家目線で冷静に書いてください。
- 半導体、AI、データセンター、NANDフラッシュ、メモリ市場に関係が薄い会社の場合は、その旨を明記してください。
- 初心者にも分かる言葉を使い、専門用語には短い補足を入れてください。
- 出力はMarkdownのみで返してください。

必ず以下のMarkdown構成で出力してください。

# 決算分析レポート

## 会社概要
- 何をしている会社か
- 主力事業は何か

## 業績サマリー
- 売上
- 営業利益
- 純利益
- 前年同期比の変化

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

## 今後注目すべき指標
次回決算で確認すべき項目を箇条書きで出力してください。

## 初心者向け解説
投資初心者にも分かる言葉で、「この決算は良かったのか、悪かったのか」を3〜5行で説明してください。

## 投資メモ
投資家として覚えておくべきポイントを箇条書きでまとめてください。

## AIスコア

成長性：0〜100点
- 理由:

収益性：0〜100点
- 理由:

財務健全性：0〜100点
- 理由:

将来性：0〜100点
- 理由:

決算PDFテキスト:
{extracted_pdf_text}
""".strip()


# この関数の役割:
# OpenAI APIを呼び出して、Markdown形式の分析レポートを作成します。
def analyze_financial_report(
    extracted_pdf_text: str,
    openai_api_key: str,
    openai_model: str,
) -> str:
    try:
        from openai import OpenAI
    except ModuleNotFoundError:
        raise ValueError("openaiがインストールされていません。pip install -r requirements.txt を実行してください。")

    text_for_ai = shorten_text_for_ai(extracted_pdf_text)
    analysis_prompt = build_analysis_prompt(text_for_ai)

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
