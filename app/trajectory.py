"""One complete trajectory per line. No messages or provider reasoning persisted."""
import json
from pathlib import Path
from threading import Lock

from app.models import RunResponse


DEFAULT_PATH = Path(__file__).resolve().parent.parent / 'data' / 'trajectories.jsonl'
_WRITE_LOCK = Lock()


def save_trajectory(query: str, scenario: str, result: RunResponse, path: Path) -> None:
    record = result.model_dump(mode='json')
    record.update(query=query, scenario=scenario, total_steps=len(result.trajectory))
    record['steps'] = record.pop('trajectory')
    line = json.dumps(record, ensure_ascii=False) + '\n'
    with _WRITE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(line)
