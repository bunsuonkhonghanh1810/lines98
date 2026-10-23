# Lines 98 Full-Stack Platform
### Real-Time Multiplayer PvP and Heuristic AI Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![Protocol](https://img.shields.io/badge/Protocol-WebSocket-black.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

A web-based full-stack implementation of the classical Lines 98 board game, featuring real-time multiplayer synchronization via WebSockets, an automated heuristic AI opponent, user authentication, and an Elo-based competitive ranking system.

---

## System Capabilities

- **Heuristic AI Engine:** An autonomous agent driven by search-based heuristics (`AlphaBetaAgent`) evaluating board density, prospective lines, and mobility constraints.
- **Real-Time Multiplayer (PvP):** Low-latency bidirectional state management implemented using WebSocket connections, room-based state isolation, and dynamic matchmaking queues.
- **Competitive Ranking System:** Dynamic Elo calculation engine categorizing players across standardized competitive tiers (Apprentice, Amateur, Master, Grandmaster, Challenger).
- **Authentication & Persistence:** Secure session handling via JSON Web Tokens (JWT) stored in HTTP-only cookies, with relational data persistence managed through SQLAlchemy ORM.
- **Pathfinding Subsystem:** Grid path validation using Breadth-First Search (BFS) to enforce movement constraints on the 9x9 board.

---

## Directory Structure

```text
lines98-fullstack/
├── main.py                    # Application entry point, HTTP routes, and WebSocket endpoints
├── database.py                # Database configuration, connection pool, and models
├── requirements.txt           # Python package specifications
├── .env.example               # Environment variable templates
├── agent/
│   └── alphabeta_agent.py     # AI agent logic and heuristic board evaluation
├── game_env/
│   ├── board_logic.py         # Pathfinding, line detection, and board updates
│   └── lines98_pvp_env.py     # Two-player state management and turn-taking rules
├── static/                    # CSS stylesheets, client-side JavaScript, and game assets
└── templates/                 # Jinja2 HTML templates
```

---

## Installation and Execution

### 1. Prerequisites
- Python 3.10 or higher
- Modern web browser with WebSocket support

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/bunsuonkhonghanh1810/lines98.git
cd lines98

# Initialize virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 3. Run Application Server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Navigate to `http://127.0.0.1:8000` to access the application.

---

## Core Technologies

- **Backend Framework:** FastAPI, Uvicorn
- **Real-Time Protocol:** WebSockets
- **Data Persistence:** SQLAlchemy, SQLite / PostgreSQL
- **Security:** PyJWT, Passlib / Cryptography
- **Frontend Architecture:** Jinja2 Templates, HTML5 Canvas, Vanilla JavaScript

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
