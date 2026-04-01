from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import src.config as config
from src.aggregator import (
    VALID_RANGES,
    get_by_type,
    get_dashboard,
    get_health,
    get_summary,
    get_top_sessions,
    list_agents,
)

BASE_DIR = Path(__file__).resolve().parent
INDEX_HTML = (BASE_DIR / 'templates' / 'index.html').read_text(encoding='utf-8')
STYLE_CSS = (BASE_DIR / 'static' / 'style.css').read_text(encoding='utf-8')
APP_JS = (BASE_DIR / 'static' / 'app.js').read_text(encoding='utf-8')


class ClientDisconnected(Exception):
    pass


def ensure_range(range_name: str) -> str:
    return range_name if range_name in VALID_RANGES else '7d'


def parse_agents(qs: Dict[str, List[str]]) -> List[str]:
    raw = (qs.get('agents') or [''])[0].strip()
    return [item.strip() for item in raw.split(',') if item.strip()] if raw else []


class TokenBoardHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body, content_type: str = 'text/plain; charset=utf-8') -> None:
        data = body.encode('utf-8') if isinstance(body, str) else body
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as exc:
            # Browsers may abort XHR/fetch requests during refreshes; avoid noisy tracebacks for a dead socket.
            if isinstance(exc, OSError) and getattr(exc, 'winerror', None) not in (10053, 10054):
                raise
            raise ClientDisconnected() from exc

    def _send_json(self, payload: Dict) -> None:
        self._send(200, json.dumps(payload, ensure_ascii=False), 'application/json; charset=utf-8')

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        agent_ids = parse_agents(qs)
        range_name = ensure_range(qs.get('range', ['7d'])[0])

        try:
            if path == '/':
                self._send(200, INDEX_HTML, 'text/html; charset=utf-8')
            elif path == '/static/style.css':
                self._send(200, STYLE_CSS, 'text/css; charset=utf-8')
            elif path == '/static/app.js':
                self._send(200, APP_JS, 'application/javascript; charset=utf-8')
            elif path == '/api/dashboard':
                self._send_json(get_dashboard(range_name, agent_ids=agent_ids))
            elif path == '/api/summary':
                self._send_json(get_summary(range_name, agent_ids=agent_ids))
            elif path == '/api/agents':
                self._send_json(list_agents(range_name, agent_ids=agent_ids))
            elif path == '/api/by-type':
                self._send_json(get_by_type(range_name, agent_ids=agent_ids))
            elif path == '/api/top-sessions':
                limit = int(qs.get('limit', ['20'])[0])
                self._send_json(get_top_sessions(range_name, limit, agent_ids=agent_ids))
            elif path == '/api/health':
                self._send_json(get_health(agent_ids=agent_ids))
            else:
                self._send(404, 'Not Found')
        except ClientDisconnected:
            return
        except Exception as exc:
            try:
                self._send_json({'ok': False, 'error': str(exc)})
            except ClientDisconnected:
                return

    def log_message(self, _format, *args):
        return


def run() -> None:
    server = ThreadingHTTPServer((config.HOST, config.PORT), TokenBoardHandler)
    print('Token Board running at http://{0}:{1}'.format(config.HOST, config.PORT))
    server.serve_forever()


if __name__ == '__main__':
    run()
