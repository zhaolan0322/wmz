from __future__ import annotations

import json
from pathlib import Path

import src.config as config
import src.loader as loader
from src.aggregator import get_by_type, get_summary, get_top_sessions, list_agents, list_candidate_sources
from src.utils import utc_now

OUT_DIR = Path(__file__).resolve().parent.parent / 'data'
OUT_FILE = OUT_DIR / 'snapshot.json'
RANGES = ['today', '7d', '30d', 'all']
EXCLUDED_AGENTS = {'codex-5-3-codex'}


def auto_pick_sessions_path() -> Path:
    candidates = [
        config.SESSIONS_PATH,
        Path('/state/agents/main/sessions/sessions.json'),
        Path.home() / '.openclaw' / 'agents' / 'main' / 'sessions' / 'sessions.json',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def can_generate_live_snapshot() -> bool:
    return auto_pick_sessions_path().exists()


def build_snapshot() -> dict:
    agents_raw = list_agents()['items']
    agents = [item for item in agents_raw if item['agentId'] not in EXCLUDED_AGENTS]
    payload = {
        'snapshotCreatedAt': utc_now().isoformat(),
        'ranges': {},
        'agents': {'items': agents},
        'sources': {
            'items': [item for item in list_candidate_sources()['items'] if item['agentId'] not in EXCLUDED_AGENTS]
        },
    }

    for range_name in RANGES:
        payload['ranges'][range_name] = {
            'all': {
                'summary': get_summary(range_name),
                'byType': get_by_type(range_name),
                'topSessions': get_top_sessions(range_name, 50),
            },
            'agents': {},
        }
        payload['ranges'][range_name]['all']['summary']['snapshotCreatedAt'] = payload['snapshotCreatedAt']
        for item in agents:
            agent_id = item['agentId']
            agent_summary = get_summary(range_name, agent_ids=[agent_id])
            agent_summary['snapshotCreatedAt'] = payload['snapshotCreatedAt']
            payload['ranges'][range_name]['agents'][agent_id] = {
                'summary': agent_summary,
                'byType': get_by_type(range_name, agent_ids=[agent_id]),
                'topSessions': get_top_sessions(range_name, 50, agent_ids=[agent_id]),
            }
    return payload


def generate_snapshot() -> dict:
    if not can_generate_live_snapshot():
        raise RuntimeError('当前运行环境没有可读取的 sessions 数据源，禁止覆盖现有 snapshot。')
    chosen = auto_pick_sessions_path()
    config.SESSIONS_PATH = chosen
    loader.SESSIONS_PATH = chosen
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    loader._cache.update({'expires_at': 0.0, 'key': None, 'result': None})
    snapshot = build_snapshot()
    OUT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    return snapshot


def main() -> None:
    snapshot = generate_snapshot()
    print(OUT_FILE)
    print(f"source={auto_pick_sessions_path()}")
    print(f"snapshotCreatedAt={snapshot.get('snapshotCreatedAt')}")


if __name__ == '__main__':
    main()
