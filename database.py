import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

load_dotenv()

# Kết nối Database
engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Lấy trọng số từ .env thành một dictionary để AI sử dụng
AI_WEIGHTS = {
    'empty': float(os.getenv("EMPTY_W")),
    'win_4_1e': float(os.getenv("WIN_4_1E_W")),
    'win_3_2e': float(os.getenv("WIN_3_2E_W")),
    'win_2_3e': float(os.getenv("WIN_2_3E_W")),
    'win_4_1t': float(os.getenv("WIN_4_1T_W")),
    'win_3_1e_1t': float(os.getenv("WIN_3_1E_1T_W")),
    'island_penalty': float(os.getenv("ISLAND_P_W")),
    'edge_penalty': float(os.getenv("EDGE_P_W")),
    'adj_same_color': float(os.getenv("ADJ_SAME_W")),
    'block_next': float(os.getenv("BLOCK_NEXT_W")),
}

# Model người dùng
# Model người dùng (Đã cập nhật khớp với Database mới)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    avatar_url = Column(String, default="https://api.dicebear.com/9.x/miniavs/svg?seed=Mason")
    elo = Column(Integer, default=0)         # Điểm PvP (Bắt đầu từ 0)
    highest_score = Column(Integer, default=0) # Kỷ lục Single Play
    pvp_wins = Column(Integer, default=0)    # Số trận thắng PvP
    pvp_losses = Column(Integer, default=0)  # Số trận thua PvP
    created_at = Column(DateTime, default=datetime.utcnow)

# Model Lịch sử Trận đấu
class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    match_type = Column(String, nullable=False) # 'single', 'bot', 'pvp_rank'
    player1_id = Column(Integer, ForeignKey("users.id"))
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Đối thủ (Null nếu là AI/Single)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    score_p1 = Column(Integer, default=0)
    score_p2 = Column(Integer, default=0)
    played_at = Column(DateTime, default=datetime.utcnow)

# Tạo bảng nếu chưa có
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()