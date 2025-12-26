from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import random

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
        "stock_symbol": "DEMO",
        "start_date": "2023-01-01",
        "end_date": "2023-01-31",
        "difficulty": "easy",
        "recommended_level": 1,
        "xp_reward": 100,
        "gold_reward": 500,
        "description": "穏やかな上昇トレンド。トレードの基本を学ぼう。",
    },
    {
        "id": "forest-1",
        "name": "迷いの森",
        "stock_symbol": "TECH",
        "start_date": "2023-03-01",
        "end_date": "2023-03-31",
        "difficulty": "easy",
        "recommended_level": 2,
        "xp_reward": 150,
        "gold_reward": 750,
        "description": "小さな上下を繰り返すレンジ相場。タイミングを見極めよう。",
    },
    {
        "id": "mountain-1",
        "name": "試練の山",
        "stock_symbol": "GROW",
        "start_date": "2023-06-01",
        "end_date": "2023-06-30",
        "difficulty": "normal",
        "recommended_level": 5,
        "xp_reward": 300,
        "gold_reward": 1500,
        "description": "急上昇と急落が混在。冷静な判断力が試される。",
    },
    {
        "id": "castle-1",
        "name": "魔王の城",
        "stock_symbol": "BOSS",
        "start_date": "2020-03-01",
        "end_date": "2020-03-31",
        "difficulty": "hard",
        "recommended_level": 10,
        "xp_reward": 500,
        "gold_reward": 3000,
        "description": "コロナショック。歴史的な暴落を乗り越えられるか？",
    },
    {
        "id": "abyss-1",
        "name": "深淵の迷宮",
        "stock_symbol": "LEGEND",
        "start_date": "2022-01-01",
        "end_date": "2022-03-31",
        "difficulty": "legendary",
        "recommended_level": 15,
        "xp_reward": 1000,
        "gold_reward": 10000,
        "description": "3ヶ月の長期戦。真の投資家だけが生き残る。",
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


def generate_mock_stock_data(dungeon: Dict) -> List[Dict]:
    """モック株価データを生成"""
    data = []
    
    start_date = datetime.strptime(dungeon["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(dungeon["end_date"], "%Y-%m-%d")
    
    base_price = 1000
    volatility = 0.02
    trend = 0
    
    # 難易度に応じてパラメータ調整
    difficulty = dungeon["difficulty"]
    if difficulty == "easy":
        volatility = 0.015
        trend = 0.003
    elif difficulty == "normal":
        volatility = 0.025
        trend = 0.001
    elif difficulty == "hard":
        volatility = 0.05
        trend = -0.005
    elif difficulty == "legendary":
        volatility = 0.04
        trend = 0
    
    current_date = start_date
    prev_close = base_price
    
    # シード固定で再現性を確保
    random.seed(hash(dungeon["id"]))
    
    while current_date <= end_date:
        # 週末をスキップ
        if current_date.weekday() < 5:
            random_change = (random.random() - 0.5) * 2 * volatility
            trend_change = trend
            total_change = random_change + trend_change
            
            open_price = prev_close * (1 + (random.random() - 0.5) * 0.005)
            close_price = open_price * (1 + total_change)
            high_price = max(open_price, close_price) * (1 + random.random() * 0.01)
            low_price = min(open_price, close_price) * (1 - random.random() * 0.01)
            volume = int(1000000 + random.random() * 500000)
            
            data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume,
            })
            
            prev_close = close_price
        
        # 日付を1日進める
        from datetime import timedelta
        current_date = current_date + timedelta(days=1)
    
    return data


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
