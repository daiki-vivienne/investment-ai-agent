# このファイルの役割:
# .envファイルからアプリの設定を読み込み、他の処理に渡しやすい形に整えます。

from dataclasses import dataclass
import os


@dataclass
class ApplicationConfig:
    # このクラスの役割:
    # アプリで使う設定値をひとまとめにして管理します。
    openai_api_key: str
    openai_model: str
    jquants_api_key: str | None


# この関数の役割:
# .envファイルを読み込み、OpenAI APIキーなどの設定を返します。
# なぜ必要か:
# APIキーをコードに直接書くと危険なので、.envから読み込む形にしています。
def load_application_config() -> ApplicationConfig:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        raise ValueError(
            "python-dotenvがインストールされていません。pip install -r requirements.txt を実行してください。"
        )

    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    jquants_api_key = os.getenv("JQUANTS_API_KEY")

    if openai_api_key is None or openai_api_key.strip() == "":
        raise ValueError(
            "OPENAI_API_KEYが設定されていません。.envファイルを作成してAPIキーを書いてください。"
        )

    return ApplicationConfig(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        jquants_api_key=jquants_api_key,
    )
