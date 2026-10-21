import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import app as arena
import results_store
from players.common import PlayerError


MODEL = {'id': 'gpt-6-luna', 'name': 'GPT-6-Luna',
         'efforts': ['low', 'medium', 'high'], 'default_effort': 'medium'}


class ResultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'results.json'
        self.patch(results_store, 'RESULTS_PATH', self.path)
        self.patch(arena.codex_sdk, 'status', return_value={
            'models': [MODEL], 'default_model': MODEL['id'], 'ready': True})
        self.patch(arena.codex_sdk, 'find_model', return_value=MODEL)
        self.gpt = self.patch(arena.codex_sdk, 'call_codex_move', return_value=('rock', 'GPT pick'))
        self.claude = self.patch(arena.claude_cli, 'call_claude_move', return_value=('scissors', 'Claude pick'))
        arena.GAME_STATE = {}
        self.client = arena.app.test_client()

    def patch(self, obj, name, *args, **kwargs):
        patcher = patch.object(obj, name, *args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def start(self, rounds=3):
        response = self.client.post('/api/start-games', json={
            'num_games': rounds, 'gpt_model': MODEL['id'], 'gpt_effort': 'high',
            'claude_model': 'claude-haiku-5-5', 'claude_effort': 'high',
            'experiment_id': 'test-batch',
        })
        self.assertEqual(response.status_code, 200)

    def play(self):
        response = self.client.post('/api/next-move')
        self.assertEqual(response.status_code, 200, response.json)

    def test_empty_archive_and_pages(self):
        self.assertEqual(self.client.get('/api/results').json['games'], [])
        self.assertEqual(self.client.get('/results').status_code, 200)
        self.assertIn(b'href="/results"', self.client.get('/').data)

    def test_rounds_update_one_game_and_survive_memory_reset(self):
        self.start()
        for index in range(3):
            self.play()
            saved = results_store.read_results()['games']
            self.assertEqual(len(saved), 1)
            self.assertEqual(len(saved[0]['round_history']), index + 1)
            if index < 2:
                self.assertEqual(self.client.post('/api/next-game').status_code, 200)
        game = saved[0]
        self.assertTrue(game['all_rounds_complete'])
        self.assertIsNotNone(game['completed_at'])
        self.assertEqual(game['gpt_effort'], game['claude_effort'])
        self.assertEqual(game['gpt_model'], 'gpt-6-luna')
        self.assertEqual(game['claude_model'], 'claude-haiku-5-5')
        self.assertEqual(game['round_history'][0]['gpt_reasoning'], 'GPT pick')
        self.assertEqual(game['round_history'][0]['claude_reasoning'], 'Claude pick')
        self.assertEqual(game['gpt_stats']['wins'], 3)
        arena.GAME_STATE = {}
        self.assertEqual(self.client.get('/api/results').json['games'], saved)

    def test_duplicate_move_and_skipped_round_rejected(self):
        self.start()
        self.assertEqual(self.client.post('/api/next-game').status_code, 409)
        self.play()
        self.assertEqual(self.client.post('/api/next-move').status_code, 409)
        self.assertEqual(self.gpt.call_count, 1)
        self.assertEqual(len(results_store.read_results()['games'][0]['round_history']), 1)
        self.client.post('/api/next-game')
        self.assertEqual(self.client.post('/api/next-game').status_code, 409)

    def test_games_append_with_distinct_ids(self):
        self.start(1)
        self.play()
        self.start(1)
        self.play()
        games = results_store.read_results()['games']
        self.assertEqual(len(games), 2)
        self.assertNotEqual(games[0]['id'], games[1]['id'])
        self.assertEqual(self.client.post('/api/next-move').status_code, 400)

    def test_invalid_move_never_replaced_with_random_choice(self):
        self.start()
        self.gpt.return_value = ('invalid', 'bad')
        self.assertEqual(self.client.post('/api/next-move').status_code, 502)
        self.assertEqual(results_store.read_results()['games'], [])
        self.assertEqual(arena.GAME_STATE['round_history'], [])

    def test_provider_failure_does_not_create_result(self):
        self.start()
        self.claude.side_effect = PlayerError('Unavailable')
        self.assertEqual(self.client.post('/api/next-move').status_code, 500)
        self.assertEqual(results_store.read_results()['games'], [])
        self.assertFalse(arena.GAME_STATE['round_in_progress'])

    def test_failed_save_keeps_previous_memory_and_archive(self):
        self.start()
        self.play()
        self.client.post('/api/next-game')
        before = self.path.read_bytes()
        self.patch(arena, 'save_game', side_effect=OSError('Disk full'))
        self.assertEqual(self.client.post('/api/next-move').status_code, 500)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(arena.GAME_STATE['round_history']), 1)

    def test_corrupt_archive_is_preserved(self):
        self.path.write_text('broken json')
        self.start()
        self.assertEqual(self.client.get('/api/results').status_code, 500)
        self.assertEqual(self.client.post('/api/next-move').status_code, 500)
        self.assertEqual(self.path.read_text(), 'broken json')

    def test_concurrent_archive_writes_do_not_drop_games(self):
        self.start()
        states = [dict(copy.deepcopy(arena.GAME_STATE), id=str(i)) for i in range(10)]
        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(results_store.save_game, states))
        self.assertEqual(len(json.loads(self.path.read_text())['games']), 10)

    def test_overlapping_game_requests_are_rejected(self):
        self.start()
        with arena.GAME_LOCK:
            self.assertEqual(self.client.post('/api/next-move').status_code, 409)
            self.assertEqual(self.client.post('/api/start-games', json={}).status_code, 409)
            self.assertEqual(self.client.post('/api/next-game').status_code, 409)

    def test_malformed_round_count(self):
        self.assertEqual(self.client.post('/api/start-games', json={'num_games': 'bad'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
