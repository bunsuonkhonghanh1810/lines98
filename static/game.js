let isMyTurn = true; 
let isGameOver = false;
let myRole = 1; 

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const CELL_SIZE = 60;
const ROWS = 9;
const COLS = 9;

const COLORS = { 0: null, 1: '#ffb6c1', 2: '#98fb98', 3: '#add8e6', 4: '#fdfd96', 5: '#afeeee', 6: '#dda0dd', 7: '#ffdab9' };

let board = Array(ROWS).fill().map(() => Array(COLS).fill(0));
let nextBalls = []; 
let selectedCell = null;
let opponentPath = null; 
let socket;

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl = `${protocol}//${window.location.host}/ws/play/${GAME_MODE}`;
    const urlParams = new URLSearchParams(window.location.search);
    const roomId = urlParams.get('room_id');
    if (roomId) wsUrl += `?room_id=${roomId}`;
    
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        document.getElementById('gameStatus').innerText = "Trạng thái: Đang chơi";
        document.getElementById('gameStatus').style.color = "#28a745";
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'update_board') {
            isGameOver = false;
            document.getElementById('gameOverModal').style.display = 'none';
            
            board = data.board;
            nextBalls = data.next_balls || []; 
            
            document.getElementById('playerScore').innerText = data.score_p1;
            if (document.getElementById('enemyScore')) document.getElementById('enemyScore').innerText = data.score_p2;
            
            if (data.my_role) myRole = data.my_role;

            if (data.turn) {
                const statusEl = document.getElementById('gameStatus');
                if (GAME_MODE === 'bot' || GAME_MODE === 'pvp') {
                    if (data.turn === myRole) {
                        isMyTurn = true; 
                        statusEl.innerText = ">> ĐẾN LƯỢT BẠN <<";
                        statusEl.style.color = "#28a745";
                        opponentPath = (data.last_path && data.last_path.length > 0) ? data.last_path : null;
                    } else {
                        isMyTurn = false; 
                        statusEl.innerText = ">> ĐỐI THỦ ĐANG NGHĨ <<";
                        statusEl.style.color = "#d9534f";
                        opponentPath = null;
                    }
                } else {
                    isMyTurn = true;
                    opponentPath = null; 
                }
            }

            updateNextBalls(nextBalls);
            drawBoard();
        }
        else if (data.type === 'game_over') {
            isGameOver = true; isMyTurn = false;
            document.getElementById('endScoreP1').innerText = data.score_p1;
            const p2ScoreEl = document.getElementById('endScoreP2');

            if(p2ScoreEl) {
                p2ScoreEl.innerText = data.score_p2;
                let title = "";
                if (data.score_p1 === data.score_p2) title = "🤝 HÒA NHAU";
                else if ((myRole === 1 && data.score_p1 > data.score_p2) || (myRole === 2 && data.score_p2 > data.score_p1)) title = "🏆 CHIẾN THẮNG";
                else title = "💀 THẤT BẠI";
                document.getElementById('endTitle').innerText = title;
            } else {
                document.getElementById('endTitle').innerText = "KẾT THÚC";
            }
            document.getElementById('gameOverModal').style.display = 'flex';
        }
        else if (data.type === 'chat' || data.type === 'emote') {
            const msgBox = document.getElementById('chatMessages');
            if(!msgBox) return; 
            const div = document.createElement('div');
            
            const isMe = (data.sender_role === myRole);
            div.classList.add('msg', isMe ? 'me' : 'enemy');
            
            if (data.type === 'emote') {
                div.classList.add('emote');
                div.innerText = data.emoji;
            } else {
                div.innerText = data.text;
            }
            msgBox.appendChild(div);
            msgBox.scrollTop = msgBox.scrollHeight;
            
            const chatContainer = document.getElementById('chatContainer');
            if (!isMe && chatContainer.classList.contains('collapsed')) toggleChat();
        }
        else if (data.type === 'error') {
            if (data.message.includes("bỏ chạy")) {
                alert("CHIẾN THẮNG: " + data.message);
                window.location.href = "/";
                return;
            }
            selectedCell = null; 
            drawBoard();
        }
    };
    socket.onclose = () => {
        document.getElementById('gameStatus').innerText = "Trạng thái: Mất kết nối tới Server";
        document.getElementById('gameStatus').style.color = "#d9534f";
    };
}

function drawBall(r, c, colorId, radius) {
    const centerX = c * CELL_SIZE + CELL_SIZE / 2;
    const centerY = r * CELL_SIZE + CELL_SIZE / 2;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fillStyle = COLORS[colorId]; ctx.fill();
    ctx.strokeStyle = '#555'; ctx.lineWidth = 2; ctx.stroke();
    ctx.beginPath();
    ctx.arc(centerX - radius/3, centerY - radius/3, radius/3.5, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)'; ctx.fill();
}

function drawArrowPath(pathArr) {
    if (!pathArr || pathArr.length < 2) return;
    
    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([12, 10]); 
    ctx.strokeStyle = 'rgba(255, 80, 80, 0.55)'; 
    ctx.lineWidth = 6;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    for (let i = 0; i < pathArr.length; i++) {
        const x = pathArr[i][1] * CELL_SIZE + CELL_SIZE / 2;
        const y = pathArr[i][0] * CELL_SIZE + CELL_SIZE / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    const lastCell = pathArr[pathArr.length - 1];
    const prevCell = pathArr[pathArr.length - 2];
    const endX = lastCell[1] * CELL_SIZE + CELL_SIZE / 2;
    const endY = lastCell[0] * CELL_SIZE + CELL_SIZE / 2;
    const startX = prevCell[1] * CELL_SIZE + CELL_SIZE / 2;
    const startY = prevCell[0] * CELL_SIZE + CELL_SIZE / 2;
    
    const angle = Math.atan2(endY - startY, endX - startX);
    const headlen = 16;
    
    ctx.setLineDash([]); 
    ctx.beginPath();
    ctx.moveTo(endX, endY);
    ctx.lineTo(endX - headlen * Math.cos(angle - Math.PI / 6), endY - headlen * Math.sin(angle - Math.PI / 6));
    ctx.lineTo(endX - headlen * Math.cos(angle + Math.PI / 6), endY - headlen * Math.sin(angle + Math.PI / 6));
    ctx.lineTo(endX, endY);
    ctx.fillStyle = 'rgba(255, 80, 80, 0.8)';
    ctx.fill();
    ctx.restore();
}

function drawBoard() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
            ctx.fillStyle = '#f9f9f9';
            ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            ctx.strokeStyle = '#ddd';
            ctx.strokeRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);

            if (selectedCell && selectedCell.r === r && selectedCell.c === c) {
                ctx.fillStyle = '#ffcccc';
                ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
            }
            const ballColor = board[r][c];
            if (ballColor > 0) drawBall(r, c, ballColor, CELL_SIZE / 2 - 6);
        }
    }

    nextBalls.forEach(ball => {
        if (board[ball[0]][ball[1]] === 0) drawBall(ball[0], ball[1], ball[2], CELL_SIZE / 4);
    });

    if (opponentPath) drawArrowPath(opponentPath);
}

function updateNextBalls(nextBallsData) {
    const container = document.getElementById('nextBallsPreview');
    if (!container) return; 
    container.innerHTML = '';
    nextBallsData.forEach(ball => {
        const div = document.createElement('div');
        div.style.width = '30px'; div.style.height = '30px'; div.style.borderRadius = '50%';
        div.style.backgroundColor = COLORS[ball[2]]; div.style.border = '2px solid #555';
        div.style.boxShadow = 'inset -3px -3px 6px rgba(0,0,0,0.1), inset 3px 3px 6px rgba(255,255,255,0.6)';
        container.appendChild(div);
    });
}

// BẢN VÁ: Tọa độ chuột cho Responsive
canvas.addEventListener('mousedown', (e) => {
    if (isGameOver || !isMyTurn) return;
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    const c = Math.floor(x / CELL_SIZE);
    const r = Math.floor(y / CELL_SIZE);

    if (board[r][c] > 0) {
        selectedCell = { r, c }; drawBoard();
    } else if (selectedCell && board[r][c] === 0) {
        socket.send(JSON.stringify({action: "move", start: [selectedCell.r, selectedCell.c], end: [r, c]}));
        selectedCell = null; drawBoard();
    }
});

function requestRestart() {
    if(GAME_MODE === 'pvp') alert("Tính năng chơi lại PvP đang được phát triển!");
    else socket.send(JSON.stringify({ action: "restart" }));
}

function toggleChat() {
    const container = document.getElementById('chatContainer');
    if(!container) return;
    container.classList.toggle('collapsed');
    document.getElementById('chatToggleIcon').innerText = container.classList.contains('collapsed') ? '▲' : '▼';
}
function sendEmote(emoji) {
    if (GAME_MODE !== 'pvp') return alert("Chỉ dùng được trong PvP!");
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ action: "emote", emoji: emoji }));
}
function sendChat() {
    if (GAME_MODE !== 'pvp') return alert("Chỉ dùng được trong PvP!");
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (text && socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: "chat", text: text }));
        input.value = ''; 
    }
}
function handleChatKey(e) { if (e.key === 'Enter') sendChat(); }

initWebSocket();