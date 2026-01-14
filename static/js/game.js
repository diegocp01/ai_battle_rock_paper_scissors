// DOM Elements
const modalOverlay = document.getElementById('modal-overlay');
const gameCountSelect = document.getElementById('game-count');
const gptModelSelect = document.getElementById('gpt-model');
const claudeModelSelect = document.getElementById('claude-model');
const btnRun = document.getElementById('btn-run');
const gameContainer = document.getElementById('game-container');
const statsSection = document.getElementById('stats-section');
const phaseIndicator = document.getElementById('phase-indicator');

// Model name display elements
const gptModelNameEl = document.getElementById('gpt-model-name');
const claudeModelNameEl = document.getElementById('claude-model-name');

// Round display elements
const roundNumberEl = document.getElementById('round-number');
const totalRoundsEl = document.getElementById('total-rounds');
const gameStatusEl = document.getElementById('game-status');
const resultDisplayEl = document.getElementById('result-display');

// Choice display elements
const gptChoiceIconEl = document.getElementById('gpt-choice-icon');
const claudeChoiceIconEl = document.getElementById('claude-choice-icon');

// GPT elements
const gptThinkingEl = document.getElementById('gpt-thinking');
const gptWinsEl = document.getElementById('gpt-wins');
const gptLossesEl = document.getElementById('gpt-losses');
const gptDrawsEl = document.getElementById('gpt-draws');
const gptReasoningEl = document.getElementById('gpt-reasoning');
const gptTimerEl = document.getElementById('gpt-timer');
const gptLastTimeEl = document.getElementById('gpt-last-time');
const gptTotalTimeEl = document.getElementById('gpt-total-time');

// Claude elements
const claudeThinkingEl = document.getElementById('claude-thinking');
const claudeWinsEl = document.getElementById('claude-wins');
const claudeLossesEl = document.getElementById('claude-losses');
const claudeDrawsEl = document.getElementById('claude-draws');
const claudeReasoningEl = document.getElementById('claude-reasoning');
const claudeTimerEl = document.getElementById('claude-timer');
const claudeLastTimeEl = document.getElementById('claude-last-time');
const claudeTotalTimeEl = document.getElementById('claude-total-time');

// Stats table
const statsBody = document.getElementById('stats-body');

// Choice emoji mapping
const CHOICE_EMOJIS = {
    'rock': '🪨',
    'paper': '📄',
    'scissors': '✂️'
};

// Game state
let isRunning = false;
let timerInterval = null;
let timerStartTime = null;

// Initialize
btnRun.addEventListener('click', startGames);

function startTimer() {
    stopTimer();
    timerStartTime = Date.now();
    gptTimerEl.textContent = '0.0s';
    claudeTimerEl.textContent = '0.0s';

    timerInterval = setInterval(() => {
        const elapsed = (Date.now() - timerStartTime) / 1000;
        gptTimerEl.textContent = elapsed.toFixed(1) + 's';
        claudeTimerEl.textContent = elapsed.toFixed(1) + 's';
    }, 100);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

async function startGames() {
    const numRounds = parseInt(gameCountSelect.value);
    const gptModel = gptModelSelect.value;
    const claudeModel = claudeModelSelect.value;

    try {
        const response = await fetch('/api/start-games', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                num_games: numRounds,
                gpt_model: gptModel,
                claude_model: claudeModel
            })
        });

        const data = await response.json();
        if (data.success) {
            modalOverlay.classList.add('hidden');
            gameContainer.classList.remove('hidden');
            statsSection.classList.remove('hidden');

            resetChoiceDisplays();
            updateUI(data.game_state);
            runGameLoop();
        }
    } catch (error) {
        console.error('Error starting games:', error);
        alert('Failed to start games. Check console for details.');
    }
}

function resetChoiceDisplays() {
    gptChoiceIconEl.textContent = '❓';
    claudeChoiceIconEl.textContent = '❓';
    gptChoiceIconEl.className = 'choice-icon';
    claudeChoiceIconEl.className = 'choice-icon';
    resultDisplayEl.textContent = 'Get ready...';
    resultDisplayEl.className = 'result-display';
}

async function runGameLoop() {
    if (isRunning) return;
    isRunning = true;

    while (isRunning) {
        // Get current state
        const stateResponse = await fetch('/api/game-state');
        const state = await stateResponse.json();

        if (state.all_rounds_complete) {
            // Show final results
            const gptWins = state.gpt_stats.wins;
            const claudeWins = state.claude_stats.wins;

            if (gptWins > claudeWins) {
                resultDisplayEl.textContent = '🏆 GPT Wins the Battle!';
                resultDisplayEl.className = 'result-display winner-gpt';
            } else if (claudeWins > gptWins) {
                resultDisplayEl.textContent = '🏆 Claude Wins the Battle!';
                resultDisplayEl.className = 'result-display winner-claude';
            } else {
                resultDisplayEl.textContent = '🤝 Battle Ends in a Tie!';
                resultDisplayEl.className = 'result-display winner-draw';
            }

            gameStatusEl.textContent = '🏆 All rounds complete!';
            phaseIndicator.textContent = 'Battle Complete';
            isRunning = false;
            break;
        }

        // Reset displays for new round
        resetChoiceDisplays();
        await sleep(1000);

        // Show thinking indicators for both players
        phaseIndicator.textContent = '🎮 Round ' + state.current_round;
        gptThinkingEl.classList.remove('hidden');
        claudeThinkingEl.classList.remove('hidden');
        gameStatusEl.textContent = "Both AIs are thinking...";
        resultDisplayEl.textContent = '🤔 Choosing...';
        startTimer();

        // Make the move (both players choose simultaneously)
        try {
            const moveResponse = await fetch('/api/next-move', { method: 'POST' });
            const moveData = await moveResponse.json();

            stopTimer();
            gptThinkingEl.classList.add('hidden');
            claudeThinkingEl.classList.add('hidden');

            if (moveData.success) {
                // Reveal animation
                await revealChoices(moveData.gpt_choice, moveData.claude_choice, moveData.round_winner);

                updateUI(moveData.game_state);

                // Wait before next round
                if (!moveData.game_state.all_rounds_complete) {
                    await sleep(2500);

                    // Move to next round
                    const nextResponse = await fetch('/api/next-game', { method: 'POST' });
                    const nextData = await nextResponse.json();

                    if (nextData.success) {
                        updateUI(nextData.game_state);
                    }
                }
            } else {
                console.error('Move error:', moveData.error);
                gameStatusEl.textContent = 'Error: ' + moveData.error;
                isRunning = false;
                break;
            }
        } catch (error) {
            console.error('API error:', error);
            gameStatusEl.textContent = 'API Error - check console';
            stopTimer();
            gptThinkingEl.classList.add('hidden');
            claudeThinkingEl.classList.add('hidden');
            isRunning = false;
            break;
        }

        await sleep(500);
    }
}

async function revealChoices(gptChoice, claudeChoice, winner) {
    // Countdown animation
    const countdownOptions = ['3️⃣', '2️⃣', '1️⃣'];

    for (const num of countdownOptions) {
        gptChoiceIconEl.textContent = num;
        claudeChoiceIconEl.textContent = num;
        await sleep(400);
    }

    // Reveal!
    gptChoiceIconEl.textContent = CHOICE_EMOJIS[gptChoice] || gptChoice;
    claudeChoiceIconEl.textContent = CHOICE_EMOJIS[claudeChoice] || claudeChoice;

    // Add reveal animation class
    gptChoiceIconEl.classList.add('revealed');
    claudeChoiceIconEl.classList.add('revealed');

    // Show result
    await sleep(300);

    if (winner === 'gpt') {
        resultDisplayEl.textContent = '🎉 GPT Wins!';
        resultDisplayEl.className = 'result-display winner-gpt';
        gptChoiceIconEl.classList.add('winner');
        gameStatusEl.textContent = `🪨📄✂️ ${gptChoice.toUpperCase()} beats ${claudeChoice.toUpperCase()}!`;
    } else if (winner === 'claude') {
        resultDisplayEl.textContent = '🎉 Claude Wins!';
        resultDisplayEl.className = 'result-display winner-claude';
        claudeChoiceIconEl.classList.add('winner');
        gameStatusEl.textContent = `🪨📄✂️ ${claudeChoice.toUpperCase()} beats ${gptChoice.toUpperCase()}!`;
    } else {
        resultDisplayEl.textContent = "🤝 It's a Draw!";
        resultDisplayEl.className = 'result-display winner-draw';
        gameStatusEl.textContent = `🪨📄✂️ Both chose ${gptChoice.toUpperCase()}!`;
    }
}

function updateUI(state) {
    // Update round number
    roundNumberEl.textContent = state.current_round;
    totalRoundsEl.textContent = state.total_rounds;

    // Update stats
    gptWinsEl.textContent = state.gpt_stats.wins;
    gptLossesEl.textContent = state.gpt_stats.losses;
    gptDrawsEl.textContent = state.gpt_stats.draws || 0;
    claudeWinsEl.textContent = state.claude_stats.wins;
    claudeLossesEl.textContent = state.claude_stats.losses;
    claudeDrawsEl.textContent = state.claude_stats.draws || 0;

    // Update timing
    gptLastTimeEl.textContent = state.gpt_last_time + 's';
    gptTotalTimeEl.textContent = state.gpt_total_time + 's';
    claudeLastTimeEl.textContent = state.claude_last_time + 's';
    claudeTotalTimeEl.textContent = state.claude_total_time + 's';

    // Update reasoning
    if (state.gpt_reasoning) {
        gptReasoningEl.textContent = state.gpt_reasoning;
    }
    if (state.claude_reasoning) {
        claudeReasoningEl.textContent = state.claude_reasoning;
    }

    // Update round history table
    updateStatsTable(state.round_history);

    // Update model display names
    if (state.gpt_display_name) {
        gptModelNameEl.textContent = state.gpt_display_name;
    }
    if (state.claude_display_name) {
        claudeModelNameEl.textContent = state.claude_display_name;
    }
}

function updateStatsTable(history) {
    statsBody.innerHTML = '';

    history.forEach(round => {
        const row = document.createElement('tr');

        let winnerClass = 'winner-draw';
        let winnerText = 'Draw';
        if (round.winner === 'gpt') {
            winnerClass = 'winner-gpt';
            winnerText = 'GPT';
        } else if (round.winner === 'claude') {
            winnerClass = 'winner-claude';
            winnerText = 'Claude';
        }

        const gptEmoji = CHOICE_EMOJIS[round.gpt_choice] || round.gpt_choice;
        const claudeEmoji = CHOICE_EMOJIS[round.claude_choice] || round.claude_choice;

        row.innerHTML = `
            <td>${round.round}</td>
            <td>${round.time}</td>
            <td class="choice-cell">${gptEmoji} ${round.gpt_choice}</td>
            <td class="choice-cell">${claudeEmoji} ${round.claude_choice}</td>
            <td class="${winnerClass}">${winnerText}</td>
            <td>${round.gpt_time || 0}s</td>
            <td>${round.claude_time || 0}s</td>
        `;

        statsBody.appendChild(row);
    });
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
