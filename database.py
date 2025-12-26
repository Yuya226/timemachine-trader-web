"""データベース管理モジュール"""
import sqlite3
import json
from typing import Optional
from models import UserProfile, GameState

DB_PATH = "game.db"


def get_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """データベーステーブルを初期化"""
    conn = get_connection()
    cursor = conn.cursor()

    # usersテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # game_statesテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # インデックスを作成
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_session_id ON users(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_states_session_id ON game_states(session_id)")

    conn.commit()
    conn.close()


def get_user_by_session(session_id: str) -> Optional[UserProfile]:
    """セッションIDからユーザープロフィールを取得"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM users WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            data = json.loads(row["data"])
            return UserProfile(**data)
        except Exception as e:
            print(f"Error parsing user profile: {e}")
            return None
    return None


def save_user(session_id: str, profile: UserProfile):
    """ユーザープロフィールを保存"""
    conn = get_connection()
    cursor = conn.cursor()

    data_json = profile.model_dump_json()

    cursor.execute("""
        INSERT INTO users (session_id, data, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) DO UPDATE SET
            data = ?,
            updated_at = CURRENT_TIMESTAMP
    """, (session_id, data_json, data_json))

    conn.commit()
    conn.close()


def get_game_state(session_id: str) -> Optional[GameState]:
    """セッションIDからゲーム状態を取得"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM game_states WHERE session_id = ? ORDER BY updated_at DESC LIMIT 1", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            data = json.loads(row["data"])
            return GameState(**data)
        except Exception as e:
            print(f"Error parsing game state: {e}")
            return None
    return None


def save_game_state(session_id: str, state: GameState):
    """ゲーム状態を保存"""
    conn = get_connection()
    cursor = conn.cursor()

    data_json = state.model_dump_json()

    cursor.execute("""
        INSERT INTO game_states (session_id, data, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (session_id, data_json))

    conn.commit()
    conn.close()


def delete_game_state(session_id: str):
    """ゲーム状態を削除"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM game_states WHERE session_id = ?", (session_id,))

    conn.commit()
    conn.close()


def save_diagnostic_scores(session_id: str, scores: dict, current_question: int):
    """診断スコアを一時保存（オンボーディング中のみ）"""
    conn = get_connection()
    cursor = conn.cursor()

    data = json.dumps({"scores": scores, "current_question": current_question})

    # game_statesテーブルを一時的に使用（dungeon_idに"onboarding"を設定）
    cursor.execute("""
        INSERT INTO game_states (session_id, data, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (session_id, data))

    conn.commit()
    conn.close()


def get_diagnostic_scores(session_id: str) -> tuple:
    """診断スコアを取得"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT data FROM game_states WHERE session_id = ? ORDER BY updated_at DESC LIMIT 1", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            data = json.loads(row["data"])
            if "scores" in data:
                return data.get("scores", {"hero": 0, "rogue": 0, "sage": 0}), data.get("current_question", 0)
        except:
            pass
    return {"hero": 0, "rogue": 0, "sage": 0}, 0


def clear_diagnostic_scores(session_id: str):
    """診断スコアを削除"""
    # オンボーディング完了時に呼び出す
    delete_game_state(session_id)

