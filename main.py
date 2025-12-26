from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
import json
import os
import uuid
from typing import Optional
from models import (
    UserProfile, GameState, TradeAction,
    PLAYER_CLASSES, DIAGNOSTIC_QUESTIONS, INITIAL_INDICATORS, DUNGEONS,
    fetch_stock_data, calculate_level, get_xp_for_level,
    DIFFICULTY_LABELS, DIFFICULTY_COLORS
)
import database

app = FastAPI(title="タイムマシン・トレーダー")

# セッション管理ミドルウェア
SESSION_MAX_AGE = 1209600  # 2週間

class SessionMiddleware(BaseHTTPMiddleware):
    """セッションIDのみをクッキーで管理するミドルウェア"""
    async def dispatch(self, request: StarletteRequest, call_next):
        # セッションIDを取得または生成
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())

        request.state.session_id = session_id

        response = await call_next(request)

        # セッションIDをクッキーに設定
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=SESSION_MAX_AGE,
            path="/",
            httponly=False,
            samesite="lax",
            secure=False
        )
        return response

app.add_middleware(SessionMiddleware)

# 静的ファイルとテンプレート
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# テンプレートにグローバル変数を追加
templates.env.globals["PLAYER_CLASSES"] = PLAYER_CLASSES
templates.env.globals["DIFFICULTY_LABELS"] = DIFFICULTY_LABELS
templates.env.globals["DIFFICULTY_COLORS"] = DIFFICULTY_COLORS


def get_user_profile(request: Request) -> Optional[UserProfile]:
    """データベースからユーザープロフィールを取得"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return None
    return database.get_user_by_session(session_id)


def save_user_profile(request: Request, profile: UserProfile):
    """ユーザープロフィールをデータベースに保存"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return
    database.save_user(session_id, profile)


def get_game_state(request: Request) -> Optional[GameState]:
    """データベースからゲーム状態を取得"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return None
    return database.get_game_state(session_id)


def save_game_state(request: Request, state: GameState):
    """ゲーム状態をデータベースに保存"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return
    database.save_game_state(session_id, state)


def clear_game_state(request: Request):
    """ゲーム状態をデータベースから削除"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return
    database.delete_game_state(session_id)


# ルート
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """トップページ / オンボーディング開始"""
    profile = get_user_profile(request)
    if profile:
        return RedirectResponse(url="/home", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding(request: Request):
    """オンボーディング（転生）画面"""
    session_id = getattr(request.state, "session_id", None)
    if session_id:
        scores, current = database.get_diagnostic_scores(session_id)
    else:
        scores = {"hero": 0, "rogue": 0, "sage": 0}
        current = 0

    return templates.TemplateResponse("onboarding.html", {
        "request": request,
        "questions": DIAGNOSTIC_QUESTIONS,
        "question": DIAGNOSTIC_QUESTIONS[current],
        "current": current,
        "total": len(DIAGNOSTIC_QUESTIONS)
    })


@app.post("/onboarding/answer", response_class=HTMLResponse)
async def answer_question(request: Request, question_id: int = Form(...), option_index: int = Form(...)):
    """診断の回答を処理"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return RedirectResponse(url="/", status_code=302)

    # 診断スコアを取得
    scores, current = database.get_diagnostic_scores(session_id)

    # スコアを加算
    question = DIAGNOSTIC_QUESTIONS[question_id]
    option = question["options"][option_index]
    scores["hero"] += option["scores"]["hero"]
    scores["rogue"] += option["scores"]["rogue"]
    scores["sage"] += option["scores"]["sage"]

    current += 1

    # 診断スコアをDBに保存
    database.save_diagnostic_scores(session_id, scores, current)

    if current >= len(DIAGNOSTIC_QUESTIONS):
        # 診断完了 - クラス決定
        return RedirectResponse(url="/onboarding/result", status_code=302)

    # 次の質問を表示（HTMX部分更新）
    return templates.TemplateResponse("partials/question.html", {
        "request": request,
        "question": DIAGNOSTIC_QUESTIONS[current],
        "current": current,
        "total": len(DIAGNOSTIC_QUESTIONS)
    })


@app.get("/onboarding/result", response_class=HTMLResponse)
async def onboarding_result(request: Request):
    """クラス決定結果画面"""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return RedirectResponse(url="/", status_code=302)

    scores, _ = database.get_diagnostic_scores(session_id)

    # 最高スコアのクラスを決定
    player_class = max(scores, key=scores.get)
    class_info = PLAYER_CLASSES[player_class]

    # ユーザープロフィールを作成
    profile = UserProfile(
        player_class=player_class,
        level=1,
        xp=0,
        xp_to_next_level=get_xp_for_level(1),
        gold=1000,
        indicators=[ind.copy() for ind in INITIAL_INDICATORS],
        completed_dungeons=[],
        total_profit=0,
        total_trades=0,
        win_rate=0.0
    )
    save_user_profile(request, profile)

    # 診断スコアをクリア
    database.clear_diagnostic_scores(session_id)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "class_info": class_info,
        "scores": scores
    })


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    """ホーム画面（冒険者ギルド）"""
    profile = get_user_profile(request)
    if not profile:
        return RedirectResponse(url="/", status_code=302)

    class_info = PLAYER_CLASSES[profile.player_class]

    return templates.TemplateResponse("home.html", {
        "request": request,
        "profile": profile,
        "class_info": class_info
    })


@app.get("/dungeons", response_class=HTMLResponse)
async def dungeons(request: Request):
    """ダンジョン選択画面"""
    profile = get_user_profile(request)
    if not profile:
        return RedirectResponse(url="/", status_code=302)

    # ダンジョンリストにクリア状態を反映
    dungeons_with_status = []
    for dungeon in DUNGEONS:
        d = dungeon.copy()
        d["completed"] = dungeon["id"] in profile.completed_dungeons
        d["can_enter"] = profile.level >= dungeon["recommended_level"]
        # 難易度の背景色を計算
        difficulty_color = DIFFICULTY_COLORS[dungeon["difficulty"]]
        d["difficulty_bg_color"] = f"{difficulty_color}33"
        dungeons_with_status.append(d)

    return templates.TemplateResponse("dungeons.html", {
        "request": request,
        "profile": profile.model_dump() if profile else {},
        "dungeons": dungeons_with_status,
        "DIFFICULTY_COLORS": DIFFICULTY_COLORS,
        "DIFFICULTY_LABELS": DIFFICULTY_LABELS
    })


@app.get("/dungeon/{dungeon_id}/panel", response_class=HTMLResponse)
async def enter_dungeon_panel(request: Request, dungeon_id: str):
    """ダンジョンパネル（HTMXでインラインロード）"""
    profile = get_user_profile(request)
    if not profile:
        return HTMLResponse(content="<p>セッションが切れました。<a href='/'>トップに戻る</a></p>")

    # ダンジョンを探す
    dungeon = next((d for d in DUNGEONS if d["id"] == dungeon_id), None)
    if not dungeon:
        return HTMLResponse(content="<p>ダンジョンが見つかりません</p>")

    # 株価データを取得
    stock_data = fetch_stock_data(dungeon)

    # ゲーム状態を初期化
    game_state = GameState(
        dungeon_id=dungeon_id,
        current_day=0,
        total_days=len(stock_data),
        cash=10000,
        shares=0,
        avg_price=0,
        stock_data=stock_data,
        trade_history=[]
    )
    save_game_state(request, game_state)

    # 装備中のインジケーターを取得
    equipped_indicators = [ind for ind in profile.indicators if ind.get("equipped", False)]

    # 難易度の背景色とスタイルを計算
    difficulty_color = DIFFICULTY_COLORS[dungeon["difficulty"]]
    difficulty_bg_color = f"{difficulty_color}33"
    difficulty_badge_style = f"background: {difficulty_bg_color}; color: {difficulty_color}; padding: 4px 12px; border-radius: 4px;"

    return templates.TemplateResponse("partials/dungeon_panel.html", {
        "request": request,
        "profile": profile,
        "dungeon": dungeon,
        "game_state": game_state,
        "current_price": stock_data[0],
        "equipped_indicators": equipped_indicators,
        "chart_data": json.dumps(stock_data[:1]),
        "DIFFICULTY_COLORS": DIFFICULTY_COLORS,
        "DIFFICULTY_LABELS": DIFFICULTY_LABELS,
        "difficulty_badge_style": difficulty_badge_style
    })


@app.get("/dungeon/{dungeon_id}", response_class=HTMLResponse)
async def enter_dungeon(request: Request, dungeon_id: str):
    """ダンジョンに入る"""
    profile = get_user_profile(request)
    if not profile:
        return RedirectResponse(url="/", status_code=302)

    # ダンジョンを探す
    dungeon = next((d for d in DUNGEONS if d["id"] == dungeon_id), None)
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")

    # 株価データを取得
    stock_data = fetch_stock_data(dungeon)

    # ゲーム状態を初期化
    game_state = GameState(
        dungeon_id=dungeon_id,
        current_day=0,
        total_days=len(stock_data),
        cash=10000,
        shares=0,
        avg_price=0,
        stock_data=stock_data,
        trade_history=[]
    )
    save_game_state(request, game_state)

    # 装備中のインジケーターを取得
    equipped_indicators = [ind for ind in profile.indicators if ind.get("equipped", False)]

    # 難易度の背景色を計算
    difficulty_color = DIFFICULTY_COLORS[dungeon["difficulty"]]
    difficulty_bg_color = f"{difficulty_color}33"

    return templates.TemplateResponse("dungeon.html", {
        "request": request,
        "profile": profile,
        "dungeon": dungeon,
        "game_state": game_state,
        "current_price": stock_data[0],
        "equipped_indicators": equipped_indicators,
        "chart_data": json.dumps(stock_data[:1]),
        "DIFFICULTY_COLORS": DIFFICULTY_COLORS,
        "DIFFICULTY_LABELS": DIFFICULTY_LABELS,
        "difficulty_bg_color": difficulty_bg_color
    })


@app.post("/dungeon/trade", response_class=HTMLResponse)
async def trade(request: Request, action: str = Form(...)):
    """トレードアクションを実行"""
    profile = get_user_profile(request)
    game_state = get_game_state(request)

    if not profile or not game_state:
        return RedirectResponse(url="/", status_code=302)

    current_price = game_state.stock_data[game_state.current_day]["close"]

    # トレードを実行
    if action == "buy" and game_state.cash > 0:
        # 全額で購入
        shares_to_buy = int(game_state.cash / current_price)
        if shares_to_buy > 0:
            cost = shares_to_buy * current_price
            game_state.cash -= cost
            if game_state.shares > 0:
                # 平均取得価格を更新
                total_cost = game_state.avg_price * game_state.shares + cost
                game_state.shares += shares_to_buy
                game_state.avg_price = total_cost / game_state.shares
            else:
                game_state.shares = shares_to_buy
                game_state.avg_price = current_price
            game_state.trade_history.append({
                "day": game_state.current_day,
                "action": "buy",
                "price": current_price,
                "shares": shares_to_buy
            })

    elif action == "sell" and game_state.shares > 0:
        # 全株売却
        proceeds = game_state.shares * current_price
        game_state.cash += proceeds
        game_state.trade_history.append({
            "day": game_state.current_day,
            "action": "sell",
            "price": current_price,
            "shares": game_state.shares,
            "profit": (current_price - game_state.avg_price) * game_state.shares
        })
        game_state.shares = 0
        game_state.avg_price = 0

    save_game_state(request, game_state)

    # ダンジョン情報を取得
    dungeon = next((d for d in DUNGEONS if d["id"] == game_state.dungeon_id), None)
    equipped_indicators = [ind for ind in profile.indicators if ind.get("equipped", False)]

    return templates.TemplateResponse("partials/game_panel.html", {
        "request": request,
        "profile": profile,
        "dungeon": dungeon,
        "game_state": game_state,
        "current_price": game_state.stock_data[game_state.current_day],
        "equipped_indicators": equipped_indicators,
        "chart_data": json.dumps(game_state.stock_data[:game_state.current_day + 1])
    })


@app.post("/dungeon/next-day", response_class=HTMLResponse)
async def next_day(request: Request):
    """次の日へ進む"""
    profile = get_user_profile(request)
    game_state = get_game_state(request)

    if not profile or not game_state:
        return RedirectResponse(url="/", status_code=302)

    game_state.current_day += 1

    # ダンジョン終了判定
    if game_state.current_day >= game_state.total_days:
        save_game_state(request, game_state)
        return RedirectResponse(url="/dungeon/result", status_code=302)

    save_game_state(request, game_state)

    # ダンジョン情報を取得
    dungeon = next((d for d in DUNGEONS if d["id"] == game_state.dungeon_id), None)
    equipped_indicators = [ind for ind in profile.indicators if ind.get("equipped", False)]

    return templates.TemplateResponse("partials/game_panel.html", {
        "request": request,
        "profile": profile,
        "dungeon": dungeon,
        "game_state": game_state,
        "current_price": game_state.stock_data[game_state.current_day],
        "equipped_indicators": equipped_indicators,
        "chart_data": json.dumps(game_state.stock_data[:game_state.current_day + 1])
    })


@app.get("/dungeon/result", response_class=HTMLResponse)
async def dungeon_result(request: Request):
    """ダンジョン結果画面"""
    profile = get_user_profile(request)
    game_state = get_game_state(request)

    if not profile or not game_state:
        return RedirectResponse(url="/", status_code=302)

    # 最終的なポジションを清算
    final_price = game_state.stock_data[-1]["close"]
    final_value = game_state.cash + game_state.shares * final_price

    # 損益計算
    starting_cash = 10000
    profit_loss = final_value - starting_cash
    profit_loss_percent = (profit_loss / starting_cash) * 100

    # ダンジョン情報
    dungeon = next((d for d in DUNGEONS if d["id"] == game_state.dungeon_id), None)

    # XPと報酬計算
    base_xp = dungeon["xp_reward"]
    base_gold = dungeon["gold_reward"]

    # 利益に応じてボーナス
    if profit_loss_percent > 0:
        xp_earned = int(base_xp * (1 + profit_loss_percent / 100))
        gold_earned = int(base_gold * (1 + profit_loss_percent / 100))
    else:
        xp_earned = int(base_xp * 0.5)  # 損失でも経験値は半分もらえる
        gold_earned = 0

    # プロフィール更新
    profile.xp += xp_earned
    profile.gold += gold_earned
    profile.total_profit += profit_loss
    profile.total_trades += len(game_state.trade_history)

    # 勝率更新
    winning_trades = len([t for t in game_state.trade_history if t.get("profit", 0) > 0])
    total_sells = len([t for t in game_state.trade_history if t["action"] == "sell"])
    if total_sells > 0:
        new_win_rate = winning_trades / total_sells
        # 移動平均で更新
        profile.win_rate = (profile.win_rate + new_win_rate) / 2

    # レベルアップ判定
    level_info = calculate_level(profile.xp)
    old_level = profile.level
    profile.level = level_info["level"]
    profile.xp_to_next_level = level_info["xp_to_next"]

    leveled_up = profile.level > old_level

    # 新しいインジケーター解放
    new_indicators = []
    for ind in profile.indicators:
        if not ind.get("unlocked", False) and ind["required_level"] <= profile.level:
            ind["unlocked"] = True
            new_indicators.append(ind)

    # ダンジョンクリア記録
    if game_state.dungeon_id not in profile.completed_dungeons:
        profile.completed_dungeons.append(game_state.dungeon_id)

    save_user_profile(request, profile)
    clear_game_state(request)

    return templates.TemplateResponse("dungeon_result.html", {
        "request": request,
        "profile": profile,
        "dungeon": dungeon,
        "final_value": final_value,
        "profit_loss": profit_loss,
        "profit_loss_percent": profit_loss_percent,
        "xp_earned": xp_earned,
        "gold_earned": gold_earned,
        "leveled_up": leveled_up,
        "old_level": old_level,
        "new_indicators": new_indicators,
        "trade_count": len(game_state.trade_history)
    })


@app.get("/equipment", response_class=HTMLResponse)
async def equipment(request: Request):
    """装備管理画面"""
    profile = get_user_profile(request)
    if not profile:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse("equipment.html", {
        "request": request,
        "profile": profile,
        "class_info": PLAYER_CLASSES[profile.player_class]
    })


@app.post("/equipment/toggle", response_class=HTMLResponse)
async def toggle_equipment(request: Request, indicator_id: str = Form(...)):
    """装備の着脱"""
    profile = get_user_profile(request)
    if not profile:
        return RedirectResponse(url="/", status_code=302)

    for ind in profile.indicators:
        if ind["id"] == indicator_id and ind.get("unlocked", False):
            ind["equipped"] = not ind.get("equipped", False)
            break

    save_user_profile(request, profile)

    return templates.TemplateResponse("partials/equipment_list.html", {
        "request": request,
        "profile": profile
    })


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """プロフィール画面"""
    profile = get_user_profile(request)
    if not profile:
        return RedirectResponse(url="/", status_code=302)

    class_info = PLAYER_CLASSES[profile.player_class]

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "profile": profile,
        "class_info": class_info
    })


@app.post("/reset", response_class=HTMLResponse)
async def reset_game(request: Request):
    """ゲームをリセット"""
    session_id = getattr(request.state, "session_id", None)
    if session_id:
        # ゲーム状態を削除
        database.delete_game_state(session_id)
        # ユーザープロフィールを削除
        # 注: usersテーブルから削除する場合は追加の関数が必要ですが、
        # ここではゲーム状態のみ削除します
    return RedirectResponse(url="/", status_code=302)


# データベースを初期化
database.init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
