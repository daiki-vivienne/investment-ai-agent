# このファイルの役割:
# DiscordからPDFを受け取り、共通のレポート生成サービスを呼び出すBotを起動します。
#
# なぜ必要か:
# 友達とDiscordでPDFを共有しながら分析できるようにするためです。
# 分析処理そのものはsrc/report_service.pyに任せ、Discord専用の重複実装を避けます。

import asyncio
from datetime import datetime
from pathlib import Path
import os
import uuid

import discord
from dotenv import load_dotenv

from src.config import load_application_config
from src.report_service import generate_report

COMMAND_PREFIX = "!analyze"
DISCORD_UPLOAD_DIRECTORY = Path("data/discord_uploads")
REPORT_OUTPUT_DIRECTORY = Path("data/reports")


# この関数の役割:
# Discord Bot用のトークンを.envから読み込みます。
def load_discord_bot_token() -> str:
    load_dotenv()
    discord_bot_token = os.getenv("DISCORD_BOT_TOKEN")

    if discord_bot_token is None or discord_bot_token.strip() == "":
        raise ValueError(
            "DISCORD_BOT_TOKENが設定されていません。"
            ".envにDISCORD_BOT_TOKENを書いてから、もう一度実行してください。"
        )

    return discord_bot_token


# この関数の役割:
# Botが反応してよいDiscordチャンネルIDを.envから読み込みます。
#
# なぜ必要か:
# どのチャンネルでも投資分析Botが反応すると、雑談チャンネルなどで誤作動する可能性があります。
# 未設定なら従来通り、チャンネル制限なしで動かします。
def load_allowed_channel_id() -> int | None:
    load_dotenv()
    allowed_channel_id_text = os.getenv("DISCORD_ALLOWED_CHANNEL_ID")

    if allowed_channel_id_text is None or allowed_channel_id_text.strip() == "":
        return None

    try:
        return int(allowed_channel_id_text)
    except ValueError as error:
        raise ValueError(
            "DISCORD_ALLOWED_CHANNEL_IDは数字だけで設定してください。"
            "Discordのチャンネル名ではなく、チャンネルIDを指定します。"
        ) from error


# この関数の役割:
# !analyzeコマンドの使い方を返します。
def build_usage_message() -> str:
    return (
        "使い方: PDFを1つ添付して `!analyze 285A FY 2025-03-31` のように送ってください。\n"
        "例: `!analyze 285A FY 2025-03-31`"
    )


# この関数の役割:
# Discordメッセージからstock_code、period_type、fiscal_year_endを取り出します。
def parse_analyze_command(message_content: str) -> tuple[str, str, str]:
    command_parts = message_content.strip().split()

    if len(command_parts) != 4:
        raise ValueError(build_usage_message())

    command_name = command_parts[0]

    if command_name != COMMAND_PREFIX:
        raise ValueError(build_usage_message())

    stock_code = command_parts[1]
    period_type = command_parts[2]
    fiscal_year_end = command_parts[3]

    return stock_code, period_type, fiscal_year_end


# この関数の役割:
# メッセージにPDFが1つだけ添付されているか確認します。
def get_single_pdf_attachment(message: discord.Message) -> discord.Attachment:
    if len(message.attachments) == 0:
        raise ValueError("PDFファイルを1つ添付してください。")

    if len(message.attachments) > 1:
        raise ValueError("複数PDFにはまだ対応していません。1つのPDFだけ添付してください。")

    attachment = message.attachments[0]
    file_name = attachment.filename.lower()

    if not file_name.endswith(".pdf"):
        raise ValueError("PDFファイルのみ対応しています。PDFを添付してください。")

    return attachment


# この関数の役割:
# 添付PDFを一時フォルダに保存します。
#
# なぜ必要か:
# generate_report()はローカルファイルパスを受け取るため、Discord添付を一度保存する必要があります。
def create_upload_file_path(original_file_name: str) -> Path:
    current_time_text = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique_id = uuid.uuid4().hex
    safe_file_name = Path(original_file_name).name

    return DISCORD_UPLOAD_DIRECTORY / f"{current_time_text}_{unique_id}_{safe_file_name}"


# この関数の役割:
# Discordの返信へ使う進捗メッセージをコンソールにも出します。
def print_progress(message: str) -> None:
    print(message)


# この関数の役割:
# PDF添付を受け取り、レポート生成を実行してDiscordへ返信します。
async def handle_analyze_message(message: discord.Message) -> None:
    try:
        stock_code, period_type, fiscal_year_end = parse_analyze_command(message.content)
        attachment = get_single_pdf_attachment(message)
    except ValueError as error:
        await message.reply(str(error), mention_author=False)
        return

    await message.reply("分析を開始しました。少し時間がかかります。", mention_author=False)

    DISCORD_UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    uploaded_pdf_path = create_upload_file_path(attachment.filename)

    try:
        await attachment.save(uploaded_pdf_path)

        application_config = load_application_config()

        generation_result = await asyncio.to_thread(
            generate_report,
            pdf_path=uploaded_pdf_path,
            output_dir=REPORT_OUTPUT_DIRECTORY,
            openai_api_key=application_config.openai_api_key,
            openai_model=application_config.openai_model,
            jquants_api_key=application_config.jquants_api_key,
            stock_code=stock_code,
            ticker=stock_code,
            period_type=period_type,
            fiscal_year_end=fiscal_year_end,
            progress_callback=print_progress,
        )

        await message.reply(
            content=(
                f"{generation_result.message}\n"
                "Markdownレポートを添付します。"
            ),
            file=discord.File(str(generation_result.report_file_path)),
            mention_author=False,
        )

    except FileNotFoundError as error:
        await message.reply(
            f"ファイル処理で問題が発生しました。詳細: {error}",
            mention_author=False,
        )
    except ValueError as error:
        await message.reply(
            f"設定または入力内容に問題があります。\n詳細: {error}",
            mention_author=False,
        )
    except Exception as error:
        await message.reply(
            "予期しないエラーが発生しました。PDF、APIキー、インターネット接続を確認してください。\n"
            f"詳細: {error}",
            mention_author=False,
        )
    finally:
        if uploaded_pdf_path.exists():
            uploaded_pdf_path.unlink()


# この関数の役割:
# Discord Botを作成します。
def create_discord_client() -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True

    allowed_channel_id = load_allowed_channel_id()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        print(f"Discord Botとしてログインしました: {client.user}")
        print("PDFを添付して !analyze 285A FY 2025-03-31 のように送ると分析します。")
        if allowed_channel_id is None:
            print("許可チャンネルIDは未設定です。すべてのチャンネルで!analyzeに反応します。")
        else:
            print(f"許可チャンネルID: {allowed_channel_id}")

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author == client.user:
            return

        if not message.content.strip().startswith(COMMAND_PREFIX):
            return

        if allowed_channel_id is not None and message.channel.id != allowed_channel_id:
            return

        await handle_analyze_message(message)

    return client


# この関数の役割:
# Discord Botを起動します。
def run_discord_bot() -> None:
    discord_bot_token = load_discord_bot_token()
    discord_client = create_discord_client()
    discord_client.run(discord_bot_token)


if __name__ == "__main__":
    try:
        run_discord_bot()
    except ValueError as error:
        print("")
        print("Discord Botの設定に問題があります。")
        print(f"詳細: {error}")
        print(".envにDISCORD_BOT_TOKENが設定されているか確認してください。")
