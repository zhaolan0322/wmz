from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SESSIONS_PATH = Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions' / 'sessions.json'
DATA_CACHE_SECONDS = int(os.getenv('TOKEN_BOARD_CACHE_SECONDS', '30'))
HOST = os.getenv('TOKEN_BOARD_HOST', '127.0.0.1')
PORT = int(os.getenv('TOKEN_BOARD_PORT', '8787'))
SESSIONS_PATH = Path(os.getenv('TOKEN_BOARD_SESSIONS_PATH', str(DEFAULT_SESSIONS_PATH))).expanduser()
PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / 'static'
TEMPLATES_DIR = PROJECT_DIR / 'templates'
