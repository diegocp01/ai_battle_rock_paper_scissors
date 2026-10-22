"""Run/resume the nine requested games through the same API as the arena."""

import argparse
import copy

import app as arena
from players import claude_cli, codex_sdk
from results_store import read_results


MATCHUPS = [
    ('gpt-6-luna', 'claude-haiku-5-5'),
    ('gpt-6.1-sol', 'claude-sonnet-5-5'),
    ('gpt-6-astra', 'claude-opus-5-5'),
]
EFFORTS = ('low', 'medium', 'high')


def run(batch):
    gpt = codex_sdk.status()
    if not gpt['ready'] or not claude_cli.status()['ready']:
        raise RuntimeError('Sign in to both model runtimes before running experiments.')
    for model, opponent in MATCHUPS:
        info = codex_sdk.find_model(model)
        if not info or not set(EFFORTS).issubset(info['efforts']):
            raise RuntimeError(f'{model} does not support the requested reasoning settings.')

    with arena.app.test_client() as client:
        for model, opponent in MATCHUPS:
            for effort in EFFORTS:
                experiment_id = f'{batch}:{model}:{effort}'
                saved = next((game for game in read_results()['games']
                              if game['experiment_id'] == experiment_id), None)
                if saved and saved['all_rounds_complete']:
                    print(f'SKIP {model} vs {opponent} / {effort}: already saved', flush=True)
                    continue
                if saved:
                    arena.GAME_STATE = copy.deepcopy(saved)
                    if len(saved['round_history']) == saved['current_round']:
                        check(client.post('/api/next-game'))
                else:
                    check(client.post('/api/start-games', json={
                        'num_games': 3, 'gpt_model': model, 'claude_model': opponent,
                        'gpt_effort': effort, 'claude_effort': effort,
                        'experiment_id': experiment_id,
                    }))
                print(f'PLAY {model} vs {opponent} / {effort}', flush=True)
                while not arena.GAME_STATE['all_rounds_complete']:
                    result = check(client.post('/api/next-move'))
                    state = result['game_state']
                    print(f"  Round {state['current_round']}: {result['gpt_choice']} vs "
                          f"{result['claude_choice']} = {result['round_winner']}", flush=True)
                    if not state['all_rounds_complete']:
                        check(client.post('/api/next-game'))
        games = [game for game in read_results()['games']
                 if (game.get('experiment_id') or '').startswith(f'{batch}:')]
        print(f"SAVED {len(games)} games, {sum(len(g['round_history']) for g in games)} rounds", flush=True)


def check(response):
    data = response.get_json()
    if response.status_code != 200:
        raise RuntimeError(data.get('error', str(response.status_code)))
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True, help='Reuse this ID to resume without duplicating games')
    run(parser.parse_args().batch)
