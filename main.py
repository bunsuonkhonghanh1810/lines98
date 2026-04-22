import json
import asyncio
from datetime import datetime, timedelta
import uuid
import random
from urllib.parse import unquote
from sqlalchemy import func
from typing import Optional

import os
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import jwt

# --- Import Logic Game & AI của bạn ---
import database as db_mod
from game_env.lines98_pvp_env import Lines98PvPEnv
from agent.alphabeta_agent import AlphaBetaAgent
from game_env.board_logic import get_path


load_dotenv()

# --- KHỞI TẠO APP & CẤU HÌNH ---
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- HỆ THỐNG RANK ELO ---
def get_rank_info(elo):
    if elo < 100: return {"name": "Tập Sự", "icon": "🥉", "color": "#cd7f32"} # Đồng
    elif elo < 300: return {"name": "Nghiệp Dư", "icon": "🥈", "color": "#a9a9a9"} # Bạc
    elif elo < 600: return {"name": "Cao Thủ", "icon": "🥇", "color": "#ffd700"} # Vàng
    elif elo < 1000: return {"name": "Đại Cao Thủ", "icon": "💎", "color": "#00ced1"} # Kim cương
    else: return {"name": "Thách Đấu", "icon": "👑", "color": "#ff4500"} # Đỏ rực

# Đưa hàm này vào Jinja2 để mọi file HTML đều dùng được
templates.env.globals.update(get_rank_info=get_rank_info)

SECRET_KEY = os.getenv("SECRET_KEY", "default_fallback_key")

# Bộ nhớ RAM lưu trạng thái các trận đấu đang diễn ra
active_games = {}
# Hàng đợi chờ tìm trận (Matchmaking Queue)
waiting_players = []
pvp_rooms = {}

# --- DEPENDENCY: KIỂM TRA ĐĂNG NHẬP ---
def get_current_user(request: Request, db: Session = Depends(db_mod.get_db)):
    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        user = db.query(db_mod.User).filter(db_mod.User.username == username).first()
        return user
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# --- ROUTER: AUTHENTICATION ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
async def process_login(response: Response, username: str = Form(...), db: Session = Depends(db_mod.get_db)):
    user = db.query(db_mod.User).filter(db_mod.User.username == username).first()
    if not user:
        custom_avatar = f"https://api.dicebear.com/9.x/miniavs/svg?seed={username}"
        user = db_mod.User(username=username, hashed_password="default", avatar_url=custom_avatar)
        db.add(user)
        db.commit()
        db.refresh(user)

    expire = datetime.utcnow() + timedelta(days=7)
    token = jwt.encode({"sub": user.username, "exp": expire}, SECRET_KEY, algorithm="HS256")
    
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.set_cookie(key="session_token", value=token, httponly=True)
    return redirect

@app.get("/logout")
async def logout():
    redirect = RedirectResponse(url="/login", status_code=302)
    redirect.delete_cookie("session_token")
    return redirect

# --- ROUTER: CÁC TRANG CHÍNH ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: db_mod.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user})

@app.get("/leaderboard", response_class=HTMLResponse)
async def view_leaderboard(request: Request, db: Session = Depends(db_mod.get_db), user: db_mod.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    top_players = db.query(db_mod.User).order_by(db_mod.User.elo.desc()).limit(50).all()
    
    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={"user": user, "top_players": top_players}
    )

# --- THÊM MỚI: ROUTER PROFILE CÁ NHÂN ---
@app.get("/profile/{username}", response_class=HTMLResponse)
async def view_profile(request: Request, username: str, db: Session = Depends(db_mod.get_db), user: db_mod.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Giải mã URL tiếng Việt và tìm kiếm không phân biệt hoa thường
    decoded_name = unquote(username)
    profile_user = db.query(db_mod.User).filter(
        func.lower(db_mod.User.username) == func.lower(decoded_name)
    ).first()

    if not profile_user:
        return HTMLResponse(content="<h1 style='text-align:center; margin-top:50px;'>404 - Không tìm thấy cao thủ này!</h1>", status_code=404)

    # Tính tỷ lệ thắng
    total_pvp = profile_user.pvp_wins + profile_user.pvp_losses
    winrate = round((profile_user.pvp_wins / total_pvp) * 100) if total_pvp > 0 else 0

    # Lấy 3 trận gần nhất làm Mini History
    raw_history = db.query(db_mod.Match).filter(
        (db_mod.Match.player1_id == profile_user.id) | (db_mod.Match.player2_id == profile_user.id)
    ).order_by(db_mod.Match.played_at.desc()).limit(3).all()
    
    recent_matches = []
    for match in raw_history:
        if match.match_type == "single":
            enemy_name = "Tự kỷ"
        elif match.match_type == "bot":
            enemy_name = "Máy tính"
        else:
            enemy_id = match.player2_id if match.player1_id == profile_user.id else match.player1_id
            enemy = db.query(db_mod.User).filter(db_mod.User.id == enemy_id).first()
            enemy_name = enemy.username if enemy else "Unknown"

        if match.match_type == "single": result_str = "Kỷ lục"
        elif match.winner_id == profile_user.id: result_str = "Thắng"
        elif match.winner_id is None: result_str = "Hòa"
        else: result_str = "Thua"

        recent_matches.append({
            "mode": match.match_type.upper(),
            "enemy": enemy_name,
            "score": f"{match.score_p1} - {match.score_p2}",
            "result": result_str
        })

    return templates.TemplateResponse(
        request=request,
        name="profile.html", 
        context={
            "user": user, 
            "profile_user": profile_user, 
            "winrate": winrate, 
            "recent_matches": recent_matches
        }
    )

# --- ROUTER HISTORY ĐÃ ĐƯỢC GỘP & SỬA LỖI ---
@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request, username: Optional[str] = None, db: Session = Depends(db_mod.get_db), user: db_mod.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    target_user = user 
    if username:
        decoded_name = unquote(username)
        found_user = db.query(db_mod.User).filter(func.lower(db_mod.User.username) == func.lower(decoded_name)).first()
        if found_user:
            target_user = found_user
    
    raw_history = db.query(db_mod.Match).filter(
        (db_mod.Match.player1_id == target_user.id) | (db_mod.Match.player2_id == target_user.id)
    ).order_by(db_mod.Match.played_at.desc()).limit(20).all()
    
    history_data = []
    for match in raw_history:
        if match.match_type == "single":
            enemy_name = "Tự kỷ"
        elif match.match_type == "bot":
            enemy_name = "Máy tính (Bot)"
        else:
            enemy_id = match.player2_id if match.player1_id == target_user.id else match.player1_id
            enemy = db.query(db_mod.User).filter(db_mod.User.id == enemy_id).first()
            enemy_name = enemy.username if enemy else "Unknown"

        if match.match_type == "single":
            result = "Kỷ lục"
        elif match.winner_id == target_user.id:
            result = "🏆 Thắng"
        elif match.winner_id is None:
            result = "🤝 Hòa"
        else:
            result = "💀 Thua"

        history_data.append({
            "mode": match.match_type.upper(),
            "enemy": enemy_name,
            "score": f"{match.score_p1} - {match.score_p2}",
            "result": result,
            "date": (match.played_at + timedelta(hours=7)).strftime("%H:%M | %d/%m/%Y")
        })

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"user": user, "target_user": target_user, "history": history_data} 
    )

@app.get("/waiting", response_class=HTMLResponse)
async def waiting_room(request: Request, user: db_mod.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="waiting.html", context={"user": user})

# --- ROUTER: VÀO GIAO DIỆN GAME ---
@app.get("/play/{mode}", response_class=HTMLResponse)
async def play_game(mode: str, request: Request, user: db_mod.User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="game.html",
        context={"user": user, "mode": mode}
    )

# --- WEBSOCKET: HÀNG ĐỢI TÌM TRẬN ---
@app.websocket("/ws/matchmaking")
async def websocket_matchmaking(websocket: WebSocket):
    await websocket.accept()
    waiting_players.append(websocket)
    print(f"Có người đang tìm trận. Hàng đợi hiện tại: {len(waiting_players)}")

    try:
        if len(waiting_players) >= 2:
            p1_ws = waiting_players.pop(0)
            p2_ws = waiting_players.pop(0)
            room_id = str(uuid.uuid4())[:8]
            await p1_ws.send_json({"match_found": True, "room_id": room_id})
            await p2_ws.send_json({"match_found": True, "room_id": room_id})

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        if websocket in waiting_players:
            waiting_players.remove(websocket)
            print("Một người chơi đã hủy tìm trận.")

# --- WEBSOCKET: XỬ LÝ TRẬN ĐẤU THỜI GIAN THỰC ---
@app.websocket("/ws/play/{mode}")
async def websocket_game_endpoint(websocket: WebSocket, mode: str, db: Session = Depends(db_mod.get_db)):
    await websocket.accept()
    room_id = websocket.query_params.get("room_id")
    print(f"\n[RADAR] Có kết nối mới! Mode: {mode} | Room ID: {room_id}")
    
    token = websocket.cookies.get("session_token")
    user = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user = db.query(db_mod.User).filter(db_mod.User.username == payload.get("sub")).first()
        except: pass

    # ================= 1. LOGIC CHẾ ĐỘ PVP =================
    if mode == "pvp":
        if not room_id: 
            await websocket.close()
            return

        is_p1 = False
        if room_id not in pvp_rooms:
            is_p1 = True
            env = Lines98PvPEnv()
            env.reset()
            pvp_rooms[room_id] = {
                "env": env, "p1_ws": websocket, "p2_ws": None,
                "p1_user": user, "p2_user": None
            }
        else:
            pvp_rooms[room_id]["p2_ws"] = websocket
            pvp_rooms[room_id]["p2_user"] = user

        room = pvp_rooms[room_id]
        my_role = 1 if is_p1 else 2

        async def broadcast_pvp_state(last_path=None):
            env = room["env"]
            base_state = {
                "type": "update_board",
                "board": env.board.astype(int).tolist(),
                "score_p1": env.score_p1, "score_p2": env.score_p2,
                "next_balls": [[int(v) for v in ball] for ball in env.next_balls],
                "turn": env.current_turn,
                "last_path": last_path or []
            }
            if room["p1_ws"]:
                try: await room["p1_ws"].send_json({**base_state, "my_role": 1})
                except: pass
            if room["p2_ws"]:
                try: await room["p2_ws"].send_json({**base_state, "my_role": 2})
                except: pass

        if is_p1:
            await websocket.send_json({
                "type": "update_board", "board": room["env"].board.astype(int).tolist(),
                "score_p1": 0, "score_p2": 0, "next_balls": [], "turn": 2, "my_role": 1, "last_path": []
            })
        else:
            import random
            room["env"].current_turn = random.choice([1, 2])
            await broadcast_pvp_state()

        try:
            while True:
                data = await websocket.receive_text()
                move_cmd = json.loads(data)

                if move_cmd["action"] in ["chat", "emote"]:
                    msg_payload = {"type": move_cmd["action"], "sender_role": my_role}
                    if move_cmd["action"] == "chat": msg_payload["text"] = move_cmd.get("text", "")
                    elif move_cmd["action"] == "emote": msg_payload["emoji"] = move_cmd.get("emoji", "")

                    if room["p1_ws"]:
                        try: await room["p1_ws"].send_json(msg_payload)
                        except: pass
                    if room["p2_ws"]:
                        try: await room["p2_ws"].send_json(msg_payload)
                        except: pass
                    continue 

                if move_cmd["action"] == "move":
                    if room["p2_ws"] is None: continue 
                    env = room["env"]
                    if env.done or env.current_turn != my_role: continue 

                    start_pos = tuple(move_cmd["start"])
                    end_pos = tuple(move_cmd["end"])
                    path = get_path(env.board, start_pos, end_pos)

                    if path:
                        env.step((start_pos, end_pos))
                        await broadcast_pvp_state(last_path=path)

                        if env.done:
                            db_new = db_mod.SessionLocal()
                            try:
                                p1_u = db_new.query(db_mod.User).filter(db_mod.User.id == room["p1_user"].id).first() if room["p1_user"] else None
                                p2_u = db_new.query(db_mod.User).filter(db_mod.User.id == room["p2_user"].id).first() if room["p2_user"] else None
                                winner_id = None
                                if env.score_p1 > env.score_p2:
                                    if p1_u: p1_u.pvp_wins += 1; p1_u.elo += 20; winner_id = p1_u.id
                                    if p2_u: p2_u.pvp_losses += 1; p2_u.elo = max(0, p2_u.elo - 20)
                                elif env.score_p2 > env.score_p1:
                                    if p2_u: p2_u.pvp_wins += 1; p2_u.elo += 20; winner_id = p2_u.id
                                    if p1_u: p1_u.pvp_losses += 1; p1_u.elo = max(0, p1_u.elo - 20)
                                new_match = db_mod.Match(
                                    match_type="pvp", player1_id=p1_u.id if p1_u else None, player2_id=p2_u.id if p2_u else None,
                                    winner_id=winner_id, score_p1=env.score_p1, score_p2=env.score_p2
                                )
                                db_new.add(new_match); db_new.commit()
                            except Exception as e: db_new.rollback()
                            finally: db_new.close()

                            if room["p1_ws"]:
                                try: await room["p1_ws"].send_json({"type": "game_over", "score_p1": env.score_p1, "score_p2": env.score_p2})
                                except: pass
                            if room["p2_ws"]:
                                try: await room["p2_ws"].send_json({"type": "game_over", "score_p1": env.score_p1, "score_p2": env.score_p2})
                                except: pass
                    else:
                        await websocket.send_json({"type": "error", "message": "Bị kẹt!"})

        except WebSocketDisconnect:
            if room["p2_ws"] is not None and not room["env"].done:
                room["env"].done = True
                db_new = db_mod.SessionLocal()
                try:
                    p1_u = db_new.query(db_mod.User).filter(db_mod.User.id == room["p1_user"].id).first() if room["p1_user"] else None
                    p2_u = db_new.query(db_mod.User).filter(db_mod.User.id == room["p2_user"].id).first() if room["p2_user"] else None
                    winner_id = None
                    if my_role == 1:
                        if p2_u: p2_u.pvp_wins += 1; p2_u.elo += 20; winner_id = p2_u.id
                        if p1_u: p1_u.pvp_losses += 1; p1_u.elo = max(0, p1_u.elo - 20)
                    else:
                        if p1_u: p1_u.pvp_wins += 1; p1_u.elo += 20; winner_id = p1_u.id
                        if p2_u: p2_u.pvp_losses += 1; p2_u.elo = max(0, p2_u.elo - 20)
                    new_match = db_mod.Match(
                        match_type="pvp", player1_id=p1_u.id if p1_u else None, player2_id=p2_u.id if p2_u else None,
                        winner_id=winner_id, score_p1=room["env"].score_p1, score_p2=room["env"].score_p2
                    )
                    db_new.add(new_match); db_new.commit()
                except Exception as e: db_new.rollback()
                finally: db_new.close()

            other_ws = room["p2_ws"] if my_role == 1 else room["p1_ws"]
            if other_ws:
                try: await other_ws.send_json({"type": "error", "message": "Đối thủ đã bỏ chạy! Bạn được xử thắng và cộng 20 Elo."})
                except: pass
            if room_id in pvp_rooms:
                del pvp_rooms[room_id]

    # ================= 2. LOGIC CHẾ ĐỘ SINGLE & BOT =================
    else:
        env = Lines98PvPEnv()
        env.reset()
        agent = AlphaBetaAgent(weights=db_mod.AI_WEIGHTS, depth=2) if mode == "bot" else None
        
        async def send_single_state(last_path=None):
            await websocket.send_json({
                "type": "update_board",
                "board": env.board.astype(int).tolist(),
                "score_p1": env.score_p1, "score_p2": env.score_p2,
                "next_balls": [[int(v) for v in ball] for ball in env.next_balls],
                "turn": env.current_turn,
                "last_path": last_path or []
            })

        def save_match_result():
            if not user: return
            db_new = db_mod.SessionLocal()
            try:
                fresh_user = db_new.query(db_mod.User).filter(db_mod.User.id == user.id).first()
                if mode == "single" and env.score_p1 > fresh_user.highest_score: fresh_user.highest_score = env.score_p1
                new_match = db_mod.Match(match_type=mode, player1_id=fresh_user.id, player2_id=None, score_p1=env.score_p1, score_p2=env.score_p2)
                db_new.add(new_match); db_new.commit()
            except: db_new.rollback()
            finally: db_new.close()

        try:
            await send_single_state()
            while True:
                data = await websocket.receive_text()
                move_cmd = json.loads(data)
                
                if move_cmd["action"] == "restart":
                    env.reset()
                    await send_single_state()
                    continue 

                if move_cmd["action"] == "move":
                    if env.done: continue
                    if mode == "bot" and env.current_turn != 1: continue

                    start_pos = tuple(move_cmd["start"])
                    end_pos = tuple(move_cmd["end"])
                    if mode == "single": env.current_turn = 1
                    
                    if get_path(env.board, start_pos, end_pos):
                        env.step((start_pos, end_pos))
                        await send_single_state(last_path=[]) 
                        
                        if env.done:
                            save_match_result()
                            await websocket.send_json({"type": "game_over", "score_p1": env.score_p1, "score_p2": env.score_p2})
                            continue

                        while mode == "bot" and env.current_turn == 2 and not env.done:
                            await asyncio.sleep(0.4)
                            best_move = agent.get_best_move(env)
                            bot_path = []
                            if best_move: 
                                bot_path = get_path(env.board, best_move[0], best_move[1])
                                env.step(best_move)
                            else: env.done = True
                            
                            await send_single_state(last_path=bot_path) 
                            if env.done:
                                save_match_result()
                                await websocket.send_json({"type": "game_over", "score_p1": env.score_p1, "score_p2": env.score_p2})
                                break
                    else:
                        await websocket.send_json({"type": "error", "message": "Bị kẹt!"})
        except WebSocketDisconnect: pass