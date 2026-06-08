# このファイルの役割:
# 投資判断支援で使う分析結果のデータ構造を定義します。

from dataclasses import dataclass
from typing import Optional


NOT_ACQUIRED = "未取得"
EXTERNAL_DATA_REQUIRED = "外部データが必要"
FUTURE_IMPLEMENTATION = "将来実装予定"


@dataclass
class FinancialMetric:
    # このクラスの役割:
    # 売上、営業利益、純利益、EPSなどの1項目分の数値を管理します。
    # なぜ必要か:
    # 数値と前年比をセットで持つことで、AIが別の項目の前年比と取り違えるリスクを減らします。
    label: str
    value: Optional[float]
    display_value: str
    yoy: Optional[float]
    display_yoy: str
    source_text: str


@dataclass
class StructuredFinancialData:
    # このクラスの役割:
    # PDFから抽出した主要な決算数値を、AIへ渡す前にJSON化できる形で管理します。
    sales: FinancialMetric
    operating_profit: FinancialMetric
    net_income: FinancialMetric
    eps: FinancialMetric
    warnings: list[str]


@dataclass
class ValuationAnalysisResult:
    # このクラスの役割:
    # PER分析に必要な値をまとめて管理します。
    # なぜ必要か:
    # 株価、EPS、業界平均PERなどはPDFだけでは足りないため、未取得の状態も明確に扱うためです。
    current_stock_price: str
    eps: str
    actual_per: str
    forecast_per: str
    industry_average_per: str
    valuation_judgement: str
    note: str


@dataclass
class MarketDataResult:
    # このクラスの役割:
    # 外部APIから取得した市場データや投資指標を管理します。
    # なぜ必要か:
    # PDF由来の数値とAPI由来の数値を分け、PERなどの計算にはAPI由来データだけを使うためです。
    requested_ticker: str
    normalized_ticker: str
    current_stock_price: Optional[float]
    display_current_stock_price: str
    sales: Optional[float]
    display_sales: str
    operating_profit: Optional[float]
    display_operating_profit: str
    net_income: Optional[float]
    display_net_income: str
    eps: Optional[float]
    display_eps: str
    pbr: Optional[float]
    display_pbr: str
    market_cap: Optional[float]
    display_market_cap: str
    data_source: str
    note: str


@dataclass
class ScenarioAnalysisResult:
    # このクラスの役割:
    # 1年後の株価シナリオを1行分として管理します。
    # なぜ必要か:
    # 上振れ、通常、下振れの3ケースを同じ形式で表示しやすくするためです。
    scenario_name: str
    stock_price: str
    cagr: str
    reason: str


@dataclass
class AnalystTargetPriceResult:
    # このクラスの役割:
    # 証券会社や投資銀行の目標株価データを管理します。
    # 現時点では取得処理を作らず、将来の外部データ接続口として使います。
    institution_name: str
    target_price: str
    rating: str
    source: str
    note: str


@dataclass
class MarketSizeAnalysisResult:
    # このクラスの役割:
    # 企業に関連する市場の将来規模を管理します。
    # なぜ必要か:
    # NAND市場、SSD市場、AIデータセンター市場などを同じ形式で比較できるようにするためです。
    market_name: str
    three_years_later: str
    five_years_later: str
    ten_years_later: str
    note: str


@dataclass
class PeerComparisonResult:
    # このクラスの役割:
    # 自社スコアと業界内での相対評価を管理します。
    # なぜ必要か:
    # 点数だけでは強いか弱いか判断しづらいため、業界平均や中央値と比較できる形にします。
    score_name: str
    company_score: Optional[int]
    industry_median: str
    industry_average: str
    percentile_rank: str
    note: str
