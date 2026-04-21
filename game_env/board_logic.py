import numpy as np
from collections import deque

def get_valid_moves_fast(board):
    """Sử dụng Flood Fill (BFS siêu tốc) để tìm các nước đi hợp lệ. 
    Trả về list các tuple: ((x1, y1), (x2, y2))"""
    valid_moves = []
    visited = np.zeros_like(board, dtype=bool)
    empty_regions = []

    # 1. Tìm các đảo ô trống
    for i in range(9):
        for j in range(9):
            if board[i, j] == 0 and not visited[i, j]:
                region = []
                queue = deque([(i, j)]) # Sửa lỗi hiệu năng bằng deque
                visited[i, j] = True
                
                while queue:
                    curr_x, curr_y = queue.popleft() # Lấy ra siêu nhanh O(1)
                    region.append((curr_x, curr_y))
                    
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = curr_x + dx, curr_y + dy
                        if 0 <= nx < 9 and 0 <= ny < 9 and board[nx, ny] == 0 and not visited[nx, ny]:
                            visited[nx, ny] = True
                            queue.append((nx, ny))
                empty_regions.append(region)

    # 2. Xem bóng chạm vào đảo nào
    for bx in range(9):
        for by in range(9):
            if board[bx, by] > 0:
                adjacent_empties = set()
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = bx + dx, by + dy
                    if 0 <= nx < 9 and 0 <= ny < 9 and board[nx, ny] == 0:
                        adjacent_empties.add((nx, ny))
                
                if not adjacent_empties: continue
                    
                reachable_empties = set()
                for region in empty_regions:
                    if any(adj in region for adj in adjacent_empties):
                        reachable_empties.update(region)
                        
                for ex, ey in reachable_empties:
                    valid_moves.append(((bx, by), (ex, ey)))
                    
    return valid_moves

def check_and_clear_lines(board):
    """Kiểm tra và xóa các hàng >= 5 quả. Trả về (điểm_số, bàn_cờ_mới)"""
    new_board = board.copy()
    to_clear = set()
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    
    for r in range(9):
        for c in range(9):
            color = new_board[r, c]
            if color == 0: continue
            
            for dr, dc in directions:
                line = [(r, c)]
                nr, nc = r + dr, c + dc
                while 0 <= nr < 9 and 0 <= nc < 9 and new_board[nr, nc] == color:
                    line.append((nr, nc))
                    nr += dr
                    nc += dc
                
                if len(line) >= 5:
                    for pos in line:
                        to_clear.add(pos)
                        
    score = 0
    if to_clear:
        # Cách tính điểm cơ bản: 5 quả = 10 điểm
        score = len(to_clear) * 2 
        for r, c in to_clear:
            new_board[r, c] = 0
            
    return score, new_board

def get_path(board, start, end):
    """
    Tìm đường đi ngắn nhất từ start đến end bằng thuật toán BFS (Loang).
    Trả về danh sách các tọa độ đi qua, hoặc None nếu bị chặn đường.
    """
    # Nếu ô bắt đầu là ô trống, hoặc ô đích đã có bóng -> Lỗi
    if board[start[0], start[1]] == 0 or board[end[0], end[1]] != 0:
        return None
    
    queue = deque([[start]]) # Dùng deque để đường truyền Game Server không bị nghẽn
    visited = set()
    visited.add(start)
    
    while queue:
        path = queue.popleft() # Lấy từ đầu hàng đợi O(1)
        r, c = path[-1]
        
        # Nếu đã loang tới đích, trả về đường đi
        if (r, c) == end:
            return path
            
        # Loang ra 4 hướng: Lên, Xuống, Trái, Phải
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 9 and 0 <= nc < 9 and board[nr, nc] == 0 and (nr, nc) not in visited:
                visited.add((nr, nc))
                new_path = list(path)
                new_path.append((nr, nc))
                queue.append(new_path)
    
    # Loang hết bàn cờ mà không tới được đích -> Bị chặn
    return None