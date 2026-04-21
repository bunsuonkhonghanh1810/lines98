import numpy as np
import random
from game_env.board_logic import get_valid_moves_fast, check_and_clear_lines

class Lines98PvPEnv:
    def __init__(self):
        self.board = np.zeros((9, 9), dtype=int)
        self.score_p1 = 0 
        self.score_p2 = 0 
        self.current_turn = 1 
        self.done = False
        self.next_balls = []

    def reset(self):
        self.board.fill(0)
        self.score_p1 = 0
        self.score_p2 = 0
        self.current_turn = 1
        self.done = False
        self._spawn_balls(5)
        self._generate_next_balls()
        return self.board

    def _spawn_balls(self, count):
        empty_cells = list(zip(*np.where(self.board == 0)))
        if not empty_cells: return
        spawn_count = min(count, len(empty_cells))
        spawn_locs = random.sample(empty_cells, spawn_count)
        for r, c in spawn_locs:
            self.board[r, c] = random.randint(1, 7)

    def _generate_next_balls(self):
        empty_cells = list(zip(*np.where(self.board == 0)))
        self.next_balls = []
        if not empty_cells: return
        count = min(3, len(empty_cells))
        locs = random.sample(empty_cells, count)
        for r, c in locs:
            self.next_balls.append((r, c, random.randint(1, 7)))

    def step(self, move):
        (x1, y1), (x2, y2) = move
        
        # Di chuyển bóng
        self.board[x2, y2] = self.board[x1, y1]
        self.board[x1, y1] = 0

        # Kiểm tra xem có ăn được hàng không
        gained, self.board = check_and_clear_lines(self.board)

        if gained > 0:
            # Ăn điểm -> Cộng điểm và GIỮ LƯỢT (không sinh bóng)
            if self.current_turn == 1:
                self.score_p1 += gained * 10
            else:
                self.score_p2 += gained * 10
        else:
            # Không ăn điểm -> Bị rớt 3 quả bóng mới
            for r, c, color in self.next_balls:
                if self.board[r, c] == 0:
                    self.board[r, c] = color
                else:
                    # --- BẢN VÁ LỖI VÔ HẠN BÓNG ---
                    # Nếu bóng nhỏ bị người chơi đè mất chỗ, bốc nó ném sang ô trống khác
                    empties = list(zip(*np.where(self.board == 0)))
                    if empties:
                        nr, nc = random.choice(empties)
                        self.board[nr, nc] = color
                    
            # Biết đâu bóng mới rơi xuống lại tạo thành hàng 5?
            gained_after, self.board = check_and_clear_lines(self.board)
            if gained_after > 0:
                if self.current_turn == 1: 
                    self.score_p1 += gained_after * 10
                else: 
                    self.score_p2 += gained_after * 10

            # Tạo trước 3 quả bóng cho lượt sau
            self._generate_next_balls()
            
            # CHUYỂN LƯỢT CHO ĐỐI PHƯƠNG
            self.current_turn = 2 if self.current_turn == 1 else 1

        # --- CHỐT CHẶN KẾT THÚC GAME CHÍNH XÁC 100% ---
        # Kiểm tra nếu bàn cờ đã kín mít (0 ô trống) HOẶC không còn nước đi hợp lệ
        if np.sum(self.board == 0) == 0 or not get_valid_moves_fast(self.board):
            self.done = True