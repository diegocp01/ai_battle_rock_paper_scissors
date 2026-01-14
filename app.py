from flask import Flask, render_template, jsonify, request
import random
from datetime import datetime
import time
import os

# Import the model functions
from openai_model_v1 import call_chatgpt_move
from anthropic_model_v1 import call_claude_move_with_thinking_flag

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Server-side game state storage
GAME_STATE = {}

# Rock Paper Scissors choices
VALID_CHOICES = ['rock', 'paper', 'scissors']
CHOICE_EMOJIS = {
    'rock': '🪨',
    'paper': '📄',
    'scissors': '✂️'
}

# Model name mappings
GPT_MODELS = {
    'gpt-5-mini': 'gpt-5-mini',
    'gpt-5.1-low': 'gpt-5.1',
    'gpt-5.1': 'gpt-5.1',
    'gpt-5.2': 'gpt-5.2',
    'gpt-5.2-high': 'gpt-5.2'
}

CLAUDE_MODELS = {
    'claude-haiku-4.5-standard': 'claude-haiku-4-5-20251001',
    'claude-haiku-4.5': 'claude-haiku-4-5-20251001',
    'claude-sonnet-4.5-standard': 'claude-sonnet-4-5-20250929',
    'claude-sonnet-4.5': 'claude-sonnet-4-5-20250929',
    'claude-opus-4.5': 'claude-opus-4-5-20251101'
}

GPT_DISPLAY_NAMES = {
    'gpt-5-mini': 'GPT 5 Mini',
    'gpt-5.1-low': 'GPT 5.1 Low',
    'gpt-5.1': 'GPT 5.1 Medium',
    'gpt-5.2': 'GPT 5.2 Medium',
    'gpt-5.2-high': 'GPT 5.2 High'
}

CLAUDE_DISPLAY_NAMES = {
    'claude-haiku-4.5-standard': 'Claude Haiku 4.5',
    'claude-haiku-4.5': 'Claude Haiku 4.5 Thinking',
    'claude-sonnet-4.5-standard': 'Claude Sonnet 4.5',
    'claude-sonnet-4.5': 'Claude Sonnet 4.5 Thinking',
    'claude-opus-4.5': 'Claude Opus 4.5 Thinking'
}


def determine_winner(choice1: str, choice2: str) -> str:
    """
    Determine the winner of a Rock Paper Scissors round.
    Returns 'gpt' if choice1 wins, 'claude' if choice2 wins, 'draw' if tie.
    """
    if choice1 == choice2:
        return 'draw'
    
    wins = {
        ('rock', 'scissors'): True,
        ('scissors', 'paper'): True,
        ('paper', 'rock'): True,
    }
    
    if wins.get((choice1, choice2)):
        return 'gpt'
    return 'claude'


def init_game_state(gpt_model='gpt-5.1', claude_model='claude-haiku-4.5'):
    """Initialize a fresh game state."""
    return {
        'current_round': 1,
        'total_rounds': 1,
        'round_in_progress': False,
        'all_rounds_complete': False,
        
        # Current round data
        'gpt_choice': None,
        'claude_choice': None,
        'round_winner': None,
        
        # History
        'round_history': [],  # List of {round, gpt_choice, claude_choice, winner}
        
        # Reasoning
        'gpt_reasoning': '',
        'claude_reasoning': '',
        
        # Stats
        'gpt_stats': {'wins': 0, 'losses': 0, 'draws': 0},
        'claude_stats': {'wins': 0, 'losses': 0, 'draws': 0},
        
        # Timing
        'gpt_total_time': 0.0,
        'claude_total_time': 0.0,
        'gpt_last_time': 0.0,
        'claude_last_time': 0.0,
        
        # Model settings
        'gpt_model': gpt_model,
        'claude_model': claude_model,
        'gpt_model_id': GPT_MODELS.get(gpt_model, 'gpt-5.1'),
        'claude_model_id': CLAUDE_MODELS.get(claude_model, 'claude-haiku-4-5-20251001'),
        'gpt_display_name': GPT_DISPLAY_NAMES.get(gpt_model, 'GPT 5.1 Medium'),
        'claude_display_name': CLAUDE_DISPLAY_NAMES.get(claude_model, 'Claude Haiku 4.5 Thinking'),
    }


def generate_move_prompt(player_name: str, round_history: list, current_round: int, total_rounds: int) -> str:
    """Generate prompt for AI to make a Rock Paper Scissors choice."""
    
    # Format round history
    if round_history:
        history_lines = []
        for r in round_history:
            gpt_emoji = CHOICE_EMOJIS.get(r['gpt_choice'], r['gpt_choice'])
            claude_emoji = CHOICE_EMOJIS.get(r['claude_choice'], r['claude_choice'])
            
            if 'GPT' in player_name:
                your_choice = r['gpt_choice'].upper()
                opp_choice = r['claude_choice'].upper()
                if r['winner'] == 'gpt':
                    result = 'You WON'
                elif r['winner'] == 'claude':
                    result = 'You LOST'
                else:
                    result = 'DRAW'
            else:
                your_choice = r['claude_choice'].upper()
                opp_choice = r['gpt_choice'].upper()
                if r['winner'] == 'claude':
                    result = 'You WON'
                elif r['winner'] == 'gpt':
                    result = 'You LOST'
                else:
                    result = 'DRAW'
            
            history_lines.append(f"Round {r['round']}: You chose {your_choice}, Opponent chose {opp_choice} → {result}")
        
        history_text = "\n".join(history_lines)
    else:
        history_text = "This is the first round - no history yet!"
    
    # Calculate score
    if 'GPT' in player_name:
        your_wins = sum(1 for r in round_history if r['winner'] == 'gpt')
        opp_wins = sum(1 for r in round_history if r['winner'] == 'claude')
    else:
        your_wins = sum(1 for r in round_history if r['winner'] == 'claude')
        opp_wins = sum(1 for r in round_history if r['winner'] == 'gpt')
    draws = sum(1 for r in round_history if r['winner'] == 'draw')
    
    return f"""You are {player_name} playing Rock Paper Scissors. Round {current_round} of {total_rounds}.

PREVIOUS ROUNDS:
{history_text}

CURRENT SCORE: You {your_wins} - Opponent {opp_wins} ({draws} draws)

RULES:
- Rock beats Scissors
- Scissors beats Paper
- Paper beats Rock

Choose: rock, paper, or scissors."""


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/start-games', methods=['POST'])
def start_games():
    """Start a new series of rounds."""
    global GAME_STATE
    data = request.get_json()
    num_rounds = int(data.get('num_games', 1))
    num_rounds = max(1, min(10, num_rounds))
    
    gpt_model = data.get('gpt_model', 'gpt-5.1')
    claude_model = data.get('claude_model', 'claude-haiku-4.5')
    
    state = init_game_state(gpt_model=gpt_model, claude_model=claude_model)
    state['total_rounds'] = num_rounds
    GAME_STATE = state
    
    return jsonify({
        'success': True,
        'game_state': get_client_state(state)
    })


@app.route('/api/game-state', methods=['GET'])
def get_game_state_route():
    """Get current game state."""
    global GAME_STATE
    if not GAME_STATE:
        GAME_STATE = init_game_state()
    return jsonify(get_client_state(GAME_STATE))


@app.route('/api/next-move', methods=['POST'])
def next_move():
    """Execute the next round - both players make a choice."""
    global GAME_STATE
    state = GAME_STATE
    if not state:
        return jsonify({'error': 'No game in progress'}), 400
    
    if state['all_rounds_complete']:
        return jsonify({'error': 'All rounds complete'}), 400
    
    state['round_in_progress'] = True
    current_round = state['current_round']
    
    # Generate prompts for both players
    gpt_prompt = generate_move_prompt(
        "GPT", 
        state['round_history'], 
        current_round, 
        state['total_rounds']
    )
    claude_prompt = generate_move_prompt(
        "Claude", 
        state['round_history'], 
        current_round, 
        state['total_rounds']
    )
    
    # Call GPT
    gpt_start = time.time()
    try:
        gpt_choice, gpt_reasoning = call_chatgpt_move(
            gpt_prompt, 
            state['gpt_model_id'], 
            model_key=state['gpt_model']
        )
    except Exception as e:
        state['round_in_progress'] = False
        return jsonify({'error': f'GPT API error: {str(e)}'}), 500
    gpt_elapsed = time.time() - gpt_start
    
    state['gpt_reasoning'] = gpt_reasoning or 'Choice made.'
    state['gpt_last_time'] = round(gpt_elapsed, 2)
    state['gpt_total_time'] = round(state['gpt_total_time'] + gpt_elapsed, 2)
    
    # Call Claude
    use_thinking = state['claude_model'] not in ('claude-haiku-4.5-standard', 'claude-sonnet-4.5-standard')
    
    claude_start = time.time()
    try:
        claude_choice, claude_reasoning = call_claude_move_with_thinking_flag(
            claude_prompt, 
            state['claude_model_id'], 
            use_thinking
        )
    except Exception as e:
        state['round_in_progress'] = False
        return jsonify({'error': f'Claude API error: {str(e)}'}), 500
    claude_elapsed = time.time() - claude_start
    
    state['claude_reasoning'] = claude_reasoning or 'Choice made.'
    state['claude_last_time'] = round(claude_elapsed, 2)
    state['claude_total_time'] = round(state['claude_total_time'] + claude_elapsed, 2)
    
    # Validate choices
    if gpt_choice not in VALID_CHOICES:
        gpt_choice = random.choice(VALID_CHOICES)
    if claude_choice not in VALID_CHOICES:
        claude_choice = random.choice(VALID_CHOICES)
    
    # Store choices
    state['gpt_choice'] = gpt_choice
    state['claude_choice'] = claude_choice
    
    # Determine winner
    round_winner = determine_winner(gpt_choice, claude_choice)
    state['round_winner'] = round_winner
    
    # Update stats
    if round_winner == 'gpt':
        state['gpt_stats']['wins'] += 1
        state['claude_stats']['losses'] += 1
    elif round_winner == 'claude':
        state['claude_stats']['wins'] += 1
        state['gpt_stats']['losses'] += 1
    else:
        state['gpt_stats']['draws'] += 1
        state['claude_stats']['draws'] += 1
    
    # Add to history
    state['round_history'].append({
        'round': current_round,
        'time': datetime.now().strftime('%H:%M:%S'),
        'gpt_choice': gpt_choice,
        'claude_choice': claude_choice,
        'winner': round_winner,
        'gpt_time': state['gpt_last_time'],
        'claude_time': state['claude_last_time']
    })
    
    # Check if all rounds complete
    if current_round >= state['total_rounds']:
        state['all_rounds_complete'] = True
    
    state['round_in_progress'] = False
    GAME_STATE = state
    
    return jsonify({
        'success': True,
        'gpt_choice': gpt_choice,
        'claude_choice': claude_choice,
        'round_winner': round_winner,
        'game_state': get_client_state(state)
    })


@app.route('/api/next-game', methods=['POST'])
def next_round():
    """Start the next round in the series."""
    global GAME_STATE
    state = GAME_STATE
    if not state:
        return jsonify({'error': 'No game in progress'}), 400
    
    if state['all_rounds_complete']:
        return jsonify({'error': 'All rounds complete'}), 400
    
    # Move to next round
    state['current_round'] += 1
    state['gpt_choice'] = None
    state['claude_choice'] = None
    state['round_winner'] = None
    
    GAME_STATE = state
    
    return jsonify({
        'success': True,
        'game_state': get_client_state(state)
    })


def get_client_state(state):
    """Get state formatted for the client."""
    return {
        'current_round': state['current_round'],
        'total_rounds': state['total_rounds'],
        'round_in_progress': state.get('round_in_progress', False),
        'all_rounds_complete': state['all_rounds_complete'],
        
        'gpt_choice': state['gpt_choice'],
        'claude_choice': state['claude_choice'],
        'round_winner': state['round_winner'],
        
        'round_history': state['round_history'],
        
        'gpt_reasoning': state['gpt_reasoning'][:500] if state['gpt_reasoning'] else '',
        'claude_reasoning': state['claude_reasoning'][:500] if state['claude_reasoning'] else '',
        
        'gpt_stats': state['gpt_stats'],
        'claude_stats': state['claude_stats'],
        
        'gpt_total_time': state.get('gpt_total_time', 0.0),
        'claude_total_time': state.get('claude_total_time', 0.0),
        'gpt_last_time': state.get('gpt_last_time', 0.0),
        'claude_last_time': state.get('claude_last_time', 0.0),
        
        'gpt_display_name': state.get('gpt_display_name', 'GPT 5.1 Medium'),
        'claude_display_name': state.get('claude_display_name', 'Claude Haiku 4.5 Thinking'),
    }


if __name__ == '__main__':
    app.run(debug=True, port=5001)
