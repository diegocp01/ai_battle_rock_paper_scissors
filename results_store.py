"""Durable game snapshots, written atomically after every successful round."""

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


RESULTS_PATH = Path(__file__).parent / 'data' / 'results.json'


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _read(path):
    if not path.exists():
        return {'schema_version': 1, 'games': []}
    # A damaged archive must surface an error, never silently erase history.
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('games'), list):
        raise ValueError('Unsupported results archive')
    return data


def read_results():
    path = Path(RESULTS_PATH)
    with _locked(path):
        return _read(path)


def save_game(state):
    path = Path(RESULTS_PATH)
    with _locked(path):
        data = _read(path)
        games = data['games']
        index = next((i for i, game in enumerate(games) if game['id'] == state['id']), None)
        if index is None:
            games.append(state)
        else:
            games[index] = state
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as temp:
                temp_name = temp.name
                json.dump(data, temp, indent=2, ensure_ascii=False)
                temp.write('\n')
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
