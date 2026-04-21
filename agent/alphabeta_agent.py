import math
import numpy as np
import collections
from env.board_logic import get_valid_moves_fast, check_and_clear_lines

def simulate_move_only(board, move):
    (x1, y1), (x2, y2) = move
    new_board = board.copy()
    new_board[x2, y2] = new_board[x1, y1]
    new_board[x1, y1] = 0
    return new_board

class AlphaBetaAgent:
    def __init__(self, weights=None, depth=2):
        if weights is None:
            # Gắn sẵn bộ gen 556.9 làm gốc
            self.w = {
                'empty': 26.40, 'win_4_1e': 1000.00, 'win_3_2e': 88.75,
                'win_2_3e': 3.09, 'win_4_1t': -27.18, 'win_3_1e_1t': -14.77,
                'island_penalty': -65.86, 'edge_penalty': 0.00,
                'adj_same_color': 33.22, 'block_next': -95.53
            }
        else:
            self.w = weights
        self.depth = depth

    def evaluate_board(self, board):
        score = 0.0
        
        # 1. Không gian trống
        score += np.sum(board == 0) * self.w.get('empty', 0)
        
        # 2. Heuristic: Cửa sổ trượt
        windows = []
        for r in range(9):
            for c in range(5): windows.append([board[r, c+i] for i in range(5)])
        for c in range(9):
            for r in range(5): windows.append([board[r+i, c] for i in range(5)])
        for r in range(5):
            for c in range(5): windows.append([board[r+i, c+i] for i in range(5)])
        for r in range(5):
            for c in range(4, 9): windows.append([board[r+i, c-i] for i in range(5)])

        for w in windows:
            empty_count = w.count(0)
            if empty_count == 5: continue
            color_counts = {}
            for val in w:
                if val > 0: color_counts[val] = color_counts.get(val, 0) + 1
            if not color_counts: continue
            max_color = max(color_counts, key=color_counts.get)
            max_count = color_counts[max_color]
            trash_count = 5 - max_count - empty_count
            
            if max_count == 4 and empty_count == 1: score += self.w.get('win_4_1e', 0)
            elif max_count == 4 and trash_count == 1: score += self.w.get('win_4_1t', 0)
            elif max_count == 3 and empty_count == 2: score += self.w.get('win_3_2e', 0)
            elif max_count == 3 and empty_count == 1 and trash_count == 1: score += self.w.get('win_3_1e_1t', 0)
            elif max_count == 2 and empty_count == 3: score += self.w.get('win_2_3e', 0)

        # 3. Đếm đảo bằng Deque (Siêu tốc độ)
        visited = set()
        islands = 0
        for r in range(9):
            for c in range(9):
                if board[r, c] == 0 and (r, c) not in visited:
                    islands += 1
                    queue = collections.deque([(r, c)])
                    visited.add((r, c))
                    while queue:
                        curr_r, curr_c = queue.popleft()
                        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                            nr, nc = curr_r + dr, curr_c + dc
                            if 0 <= nr < 9 and 0 <= nc < 9 and board[nr, nc] == 0 and (nr, nc) not in visited:
                                visited.add((nr, nc))
                                queue.append((nr, nc))
        if islands > 1: score += (islands - 1) * self.w.get('island_penalty', 0)
        
        # 4. Tụ bầy & Trung tâm (Đã được phục hồi)
        for r in range(9):
            for c in range(9):
                color = board[r, c]
                if color > 0:
                    dist_to_center = abs(r - 4) + abs(c - 4)
                    score -= dist_to_center * self.w.get('edge_penalty', 0)
                    
                    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 9 and 0 <= nc < 9 and board[nr, nc] == color:
                            score += self.w.get('adj_same_color', 0) / 2.0

        return score

    def get_top_k_moves(self, board, valid_moves, k=15):
        scored_moves = []
        for move in valid_moves:
            sim_board = simulate_move_only(board, move)
            gained, _ = check_and_clear_lines(sim_board)
            score = self.evaluate_board(sim_board) + (gained * 10000)
            scored_moves.append((score, move))
        
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        return [move for score, move in scored_moves[:k]]

    def minimax(self, board, depth, alpha, beta, is_maximizing):
        valid_moves = get_valid_moves_fast(board)
        
        if depth == 0 or not valid_moves:
            return self.evaluate_board(board)

        # Cắt tỉa nhánh cực gắt: Chỉ duyệt 10 nước tốt nhất
        top_moves = self.get_top_k_moves(board, valid_moves, k=10)

        if is_maximizing:
            max_eval = -math.inf
            for move in top_moves:
                sim_board = simulate_move_only(board, move)
                gained, sim_board = check_and_clear_lines(sim_board)
                
                eval_score = self.minimax(sim_board, depth - 1, alpha, beta, False)
                if gained > 0: eval_score += gained * 1000 
                
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha: break 
            return max_eval
        else:
            min_eval = math.inf
            for move in top_moves:
                sim_board = simulate_move_only(board, move)
                opp_gained, sim_board = check_and_clear_lines(sim_board)
                
                eval_score = self.minimax(sim_board, depth - 1, alpha, beta, True)
                if opp_gained > 0: eval_score -= opp_gained * 1000 
                
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha: break 
            return min_eval

    def get_best_move(self, env):
        board = env.board
        valid_moves = get_valid_moves_fast(board)
        if not valid_moves: return None

        top_moves = self.get_top_k_moves(board, valid_moves, k=15)

        best_move = None
        best_val = -math.inf
        alpha = -math.inf
        beta = math.inf
        
        for move in top_moves:
            sim_board = simulate_move_only(board, move)
            gained, sim_board = check_and_clear_lines(sim_board)
            
            move_val = self.minimax(sim_board, self.depth - 1, alpha, beta, False)
            if gained > 0: move_val += gained * 10000 
            
            if move_val > best_val:
                best_val = move_val
                best_move = move
            alpha = max(alpha, best_val)
            
        return best_move