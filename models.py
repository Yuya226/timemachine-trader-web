from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import random
import yfinance as yf
import pandas as pd

# プレイヤークラス情報
PLAYER_CLASSES = {
    "hero": {
        "id": "hero",
        "name": "Hero",
        "japanese_name": "勇者",
        "description": "王道の成長株を狙う、順張り・長期投資家。トレンドに乗って大きな利益を目指す。",
        "color": "#FFD700",
        "icon": "⚔️",
        "trading_style": "順張り・長期",
        "initial_skills": ["トレンドフォロー基礎", "移動平均線（基本）"],
    },
    "rogue": {
        "id": "rogue",
        "name": "Rogue",
        "japanese_name": "盗賊",
        "description": "リバウンド狙いの敏捷なトレーダー。逆張り・短期で素早く利益を確定する。",
        "color": "#A855F7",
        "icon": "🗡️",
        "trading_style": "逆張り・短期",
        "initial_skills": ["リバウンド検知", "RSI（基本）"],
    },
    "sage": {
        "id": "sage",
        "name": "Sage",
        "japanese_name": "賢者",
        "description": "業績分析を重視する知的投資家。ファンダメンタルズに基づいた堅実な投資を行う。",
        "color": "#3B82F6",
        "icon": "📖",
        "trading_style": "ファンダメンタル重視",
        "initial_skills": ["業績分析基礎", "PER/PBR分析"],
    },
}

# 診断質問
DIAGNOSTIC_QUESTIONS = [
    {
        "id": 0,
        "question": "投資で最も重要だと思うことは？",
        "options": [
            {"text": "大きなトレンドに乗ること", "scores": {"hero": 3, "rogue": 0, "sage": 1}},
            {"text": "素早く利益を確定すること", "scores": {"hero": 0, "rogue": 3, "sage": 1}},
            {"text": "企業の本質的価値を見極めること", "scores": {"hero": 1, "rogue": 0, "sage": 3}},
        ],
    },
    {
        "id": 1,
        "question": "株価が急落したとき、あなたはどうする？",
        "options": [
            {"text": "様子を見て、回復を待つ", "scores": {"hero": 3, "rogue": 0, "sage": 2}},
            {"text": "チャンス！買い増しを検討", "scores": {"hero": 1, "rogue": 3, "sage": 1}},
            {"text": "企業の業績を再確認する", "scores": {"hero": 0, "rogue": 1, "sage": 3}},
        ],
    },
    {
        "id": 2,
        "question": "理想的な投資期間は？",
        "options": [
            {"text": "1年以上の長期保有", "scores": {"hero": 3, "rogue": 0, "sage": 2}},
            {"text": "数日〜数週間の短期", "scores": {"hero": 0, "rogue": 3, "sage": 0}},
            {"text": "業績次第で柔軟に判断", "scores": {"hero": 1, "rogue": 1, "sage": 3}},
        ],
    },
    {
        "id": 3,
        "question": "投資判断で最も参考にするのは？",
        "options": [
            {"text": "チャートのトレンドライン", "scores": {"hero": 3, "rogue": 2, "sage": 0}},
            {"text": "出来高と価格の乖離", "scores": {"hero": 1, "rogue": 3, "sage": 0}},
            {"text": "決算書と財務諸表", "scores": {"hero": 0, "rogue": 0, "sage": 3}},
        ],
    },
    {
        "id": 4,
        "question": "リスクに対する考え方は？",
        "options": [
            {"text": "リスクを取って大きなリターンを狙う", "scores": {"hero": 3, "rogue": 2, "sage": 0}},
            {"text": "小さな利益を積み重ねる", "scores": {"hero": 0, "rogue": 3, "sage": 1}},
            {"text": "リスクを最小化して安定を重視", "scores": {"hero": 1, "rogue": 0, "sage": 3}},
        ],
    },
]

# 初期インジケーター
INITIAL_INDICATORS = [
    {
        "id": "line-chart",
        "name": "折れ線グラフ",
        "rpg_name": "ひのきの棒",
        "description": "基本的な価格推移を表示。すべての冒険者が最初に手にする武器。",
        "required_level": 1,
        "type": "weapon",
        "unlocked": True,
        "equipped": True,
    },
    {
        "id": "candlestick",
        "name": "ローソク足チャート",
        "rpg_name": "銅の剣",
        "description": "始値・終値・高値・安値を一目で把握。より詳細な分析が可能に。",
        "required_level": 2,
        "type": "weapon",
        "unlocked": False,
        "equipped": False,
    },
    {
        "id": "moving-average",
        "name": "移動平均線",
        "rpg_name": "ホイミの杖",
        "description": "価格のトレンドを滑らかに表示。トレンドの方向性を把握できる。",
        "required_level": 5,
        "type": "skill",
        "unlocked": False,
        "equipped": False,
    },
    {
        "id": "macd",
        "name": "MACD",
        "rpg_name": "メラゾーマの杖",
        "description": "トレンドの強さと転換点を検出。上級者向けの強力な武器。",
        "required_level": 10,
        "type": "skill",
        "unlocked": False,
        "equipped": False,
    },
    {
        "id": "rsi",
        "name": "RSI",
        "rpg_name": "氷の剣",
        "description": "買われすぎ・売られすぎを判定。逆張りの強い味方。",
        "required_level": 10,
        "type": "weapon",
        "unlocked": False,
        "equipped": False,
    },
    {
        "id": "bollinger",
        "name": "ボリンジャーバンド",
        "rpg_name": "雷神の槌",
        "description": "価格の変動範囲を予測。ボラティリティを視覚化。",
        "required_level": 15,
        "type": "weapon",
        "unlocked": False,
        "equipped": False,
    },
]

# ダンジョン一覧
DUNGEONS = [
    {
        "id": "tutorial-1",
        "name": "初心者の洞窟",
        "stock_symbol": "7203.T",  # トヨタ自動車
        "start_date": "2023-04-01",
        "end_date": "2023-07-31",
        "difficulty": "easy",
        "recommended_level": 1,
        "xp_reward": 200,
        "gold_reward": 1000,
        "description": "2023年のトヨタ自動車。綺麗な上昇トレンドを描いたボーナス相場。まずはここで「順張り」の快感を覚えよう。",
    },
    {
        "id": "forest-1",
        "name": "迷いの森",
        "stock_symbol": "9984.T",  # ソフトバンクグループ
        "start_date": "2021-04-01",
        "end_date": "2021-09-30",
        "difficulty": "normal",  # easyから格上げ
        "recommended_level": 3,
        "xp_reward": 400,
        "gold_reward": 2000,
        "description": "2021年のソフトバンクG。方向感のないレンジ相場から、徐々に崩れていく難所。無駄なトレードを減らす「待つ力」が試される。",
    },
    {
        "id": "mountain-1",
        "name": "試練の山",
        "stock_symbol": "^N225",   # 日経平均株価
        "start_date": "2018-01-01",
        "end_date": "2018-12-31",
        "difficulty": "normal",
        "recommended_level": 5,
        "xp_reward": 800,
        "gold_reward": 5000,
        "description": "2018年の日経平均。米中貿易摩擦で揺れ動いた乱高下相場。1年間の長期戦で、資金管理能力が問われる。",
    },
    {
        "id": "castle-1",
        "name": "魔王の城",
        "stock_symbol": "^N225",   # 日経平均株価
        "start_date": "2020-01-01",
        "end_date": "2020-06-30",
        "difficulty": "hard",
        "recommended_level": 10,
        "xp_reward": 2000,
        "gold_reward": 10000,
        "description": "【コロナ・ショック】数年に一度の歴史的暴落。プロでも退場する地獄の相場だが、底で拾えれば莫大な利益になる。",
    },
    {
        "id": "abyss-1",
        "name": "深淵の迷宮",
        "stock_symbol": "^N225",   # 日経平均株価
        "start_date": "2008-01-01",
        "end_date": "2008-12-31",
        "difficulty": "legendary",
        "recommended_level": 15,
        "xp_reward": 5000,
        "gold_reward": 50000,
        "description": "【リーマン・ショック】100年に一度の金融危機。終わりの見えない下落トレンド。空売りを駆使しなければ生き残れない。",
    },
]

# 難易度ラベル
DIFFICULTY_LABELS = {
    "easy": "初級",
    "normal": "中級",
    "hard": "上級",
    "legendary": "伝説",
}

# 難易度カラー
DIFFICULTY_COLORS = {
    "easy": "#10B981",
    "normal": "#F59E0B",
    "hard": "#EF4444",
    "legendary": "#A855F7",
}


class UserProfile(BaseModel):
    player_class: str
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    gold: int = 1000
    indicators: List[Dict[str, Any]] = []
    completed_dungeons: List[str] = []
    total_profit: float = 0
    total_trades: int = 0
    win_rate: float = 0.0


class GameState(BaseModel):
    dungeon_id: str
    current_day: int = 0
    total_days: int = 0
    cash: float = 10000
    shares: int = 0
    avg_price: float = 0
    stock_data: List[Dict[str, Any]] = []
    trade_history: List[Dict[str, Any]] = []


class TradeAction(BaseModel):
    action: str  # buy, sell, wait
    shares: int = 0


def fetch_stock_data(dungeon: Dict) -> List[Dict]:
    """yfinanceを使用して実在の株価データを取得し、テクニカル指標を計算"""
    try:
        symbol = dungeon["stock_symbol"]
        start_date = dungeon["start_date"]
        end_date = dungeon["end_date"]

        # yfinanceでデータを取得
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)

        # データが空の場合は空リストを返す
        if df.empty:
            return []

        # テクニカル指標を計算
        # SMA (移動平均線)
        df['sma_25'] = df['Close'].rolling(window=25).mean()
        df['sma_75'] = df['Close'].rolling(window=75).mean()

        # RSI (相対力指数) - 14日
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # ボリンジャーバンド (20日, 2σ)
        df['bb_middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        # DataFrameを辞書リストに変換
        data = []
        for date, row in df.iterrows():
            # NaNをNoneに変換してJSONシリアライズ可能にする
            def convert_nan(value):
                if pd.isna(value):
                    return None
                return round(float(value), 2) if isinstance(value, (int, float)) else value

            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
                "sma_25": convert_nan(row.get("sma_25")),
                "sma_75": convert_nan(row.get("sma_75")),
                "rsi_14": convert_nan(row.get("rsi_14")),
                "macd": convert_nan(row.get("macd")),
                "macd_signal": convert_nan(row.get("macd_signal")),
                "macd_hist": convert_nan(row.get("macd_hist")),
                "bb_upper": convert_nan(row.get("bb_upper")),
                "bb_middle": convert_nan(row.get("bb_middle")),
                "bb_lower": convert_nan(row.get("bb_lower")),
            })

        return data
    except Exception as e:
        # エラーが発生した場合は空リストを返す
        print(f"Error fetching stock data for {dungeon.get('stock_symbol', 'unknown')}: {e}")
        return []


def get_xp_for_level(level: int) -> int:
    """レベルアップに必要なXPを計算"""
    return int(100 * (1.5 ** (level - 1)))


def calculate_level(total_xp: int) -> Dict[str, int]:
    """総XPからレベルを計算"""
    level = 1
    remaining_xp = total_xp

    while remaining_xp >= get_xp_for_level(level):
        remaining_xp -= get_xp_for_level(level)
        level += 1

    return {
        "level": level,
        "current_xp": remaining_xp,
        "xp_to_next": get_xp_for_level(level),
    }
