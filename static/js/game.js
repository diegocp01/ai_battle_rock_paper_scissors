// ==========================================================
// RPS Arena: GPT vs Claude
// ==========================================================

const $ = (id) => document.getElementById(id);

// Screens
const setupEl = $('setup');
const gameContainer = $('game-container');
const btnRun = $('btn-run');
const setupErrorEl = $('setup-error');

// Scoreboard
const gptModelNameEl = $('gpt-model-name');
const claudeModelNameEl = $('claude-model-name');
const gptScoreEl = $('gpt-score');
const claudeScoreEl = $('claude-score');
const roundNumberEl = $('round-number');
const totalRoundsEl = $('total-rounds');
const roundPipsEl = $('round-pips');
const phaseIndicator = $('phase-indicator');
const momentumGptEl = $('momentum-gpt');
const momentumClaudeEl = $('momentum-claude');

// Arena
const arenaEl = $('arena');
const calloutKickerEl = $('callout-kicker');
const resultDisplayEl = $('result-display');
const gameStatusEl = $('game-status');
const actionsEl = $('actions');
const btnRetry = $('btn-retry');
const btnRematch = $('btn-rematch');
const btnNew = $('btn-new');

// Round log
const statsBody = $('stats-body');
const logEmptyEl = $('log-empty');

// Per-player elements
function playerEls(key) {
    return {
        hand: $(`${key}-hand`),
        glyph: $(`${key}-choice-icon`),
        label: $(`${key}-choice-label`),
        clock: $(`${key}-clock`),
        clockLabel: $(`${key}-clock-label`),
        timer: $(`${key}-timer`),
        wins: $(`${key}-wins`),
        losses: $(`${key}-losses`),
        draws: $(`${key}-draws`),
        reasoning: $(`${key}-reasoning`),
        lastTime: $(`${key}-last-time`),
        totalTime: $(`${key}-total-time`),
    };
}

const PLAYERS = {
    gpt: { name: 'GPT', els: playerEls('gpt') },
    claude: { name: 'Claude', els: playerEls('claude') },
};

const CHOICES = {
    rock: { emoji: '🪨', label: 'Rock' },
    paper: { emoji: '📄', label: 'Paper' },
    scissors: { emoji: '✂️', label: 'Scissors' },
};

const VERBS = {
    rock: 'crushes',
    paper: 'covers',
    scissors: 'cut',
};

const FIST = '✊';
const STORAGE_KEY = 'rps-arena-settings';
const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Game state
let isRunning = false;
let timerInterval = null;
let lastSettings = null;
let lastScores = { gpt: 0, claude: 0 };

// ---------- Setup ----------
restoreSettings();
btnRun.addEventListener('click', () => startGames(readSettings()));
btnRetry.addEventListener('click', () => {
    hideActions();
    runGameLoop();
});
btnRematch.addEventListener('click', () => startGames(lastSettings));
btnNew.addEventListener('click', showSetup);

function checkedValue(name) {
    const input = document.querySelector(`input[name="${name}"]:checked`);
    return input ? input.value : null;
}

function readSettings() {
    return {
        num_games: parseInt(checkedValue('game-count'), 10) || 3,
        gpt_model: checkedValue('gpt-model'),
        claude_model: checkedValue('claude-model'),
    };
}

function restoreSettings() {
    let saved = null;
    try {
        saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    } catch (e) {
        saved = null;
    }
    if (!saved) return;

    const pairs = [
        ['game-count', saved.num_games],
        ['gpt-model', saved.gpt_model],
        ['claude-model', saved.claude_model],
    ];
    for (const [name, value] of pairs) {
        const input = document.querySelector(`input[name="${name}"][value="${value}"]`);
        if (input) input.checked = true;
    }
}

function saveSettings(settings) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {
        // Storage unavailable; settings just won't be remembered.
    }
}

function showSetup() {
    if (isRunning) return;
    gameContainer.hidden = true;
    setupEl.hidden = false;
    window.scrollTo({ top: 0, behavior: REDUCED_MOTION ? 'auto' : 'smooth' });
}

async function startGames(settings) {
    if (isRunning || !settings) return;

    btnRun.disabled = true;
    btnRematch.disabled = true;
    setupErrorEl.hidden = true;

    try {
        const data = await postJSON('/api/start-games', settings);
        if (!data.success) throw new Error(data.error || 'Could not start the battle.');

        lastSettings = settings;
        saveSettings(settings);
        lastScores = { gpt: 0, claude: 0 };

        setupEl.hidden = true;
        gameContainer.hidden = false;
        window.scrollTo({ top: 0 });

        resetArena();
        clearReasoning();
        updateUI(data.game_state);
        runGameLoop();
    } catch (error) {
        console.error('Error starting games:', error);
        if (!setupEl.hidden) {
            setupErrorEl.textContent = `Couldn't start the battle: ${error.message}`;
            setupErrorEl.hidden = false;
        } else {
            showError(error.message);
        }
    } finally {
        btnRun.disabled = false;
        btnRematch.disabled = false;
    }
}

// ---------- Game loop ----------
async function runGameLoop() {
    if (isRunning) return;
    isRunning = true;

    try {
        while (true) {
            const state = await getJSON('/api/game-state');

            if (state.all_rounds_complete) {
                showFinal(state);
                break;
            }

            // Fresh round
            resetArena();
            calloutKickerEl.textContent = `Round ${state.current_round} of ${state.total_rounds}`;
            setCallout('Get ready.');
            gameStatusEl.textContent = 'Both models are stepping in.';
            setPhase('Round ' + state.current_round, true);
            await sleep(900);

            // Both players choose simultaneously
            setThinking(true);
            setCallout('Thinking…');
            gameStatusEl.textContent = 'Each model is deciding on its own.';
            setPhase('Thinking', true);

            const moveData = await postJSON('/api/next-move');
            setThinking(false);

            if (!moveData.success) {
                throw new Error(moveData.error || 'The move request failed.');
            }

            await revealChoices(moveData.gpt_choice, moveData.claude_choice, moveData.round_winner);
            updateUI(moveData.game_state);

            if (moveData.game_state.all_rounds_complete) {
                await sleep(1600);
                continue; // loop picks up the final state
            }

            setPhase('Round over', false);
            await sleep(2600);

            const nextData = await postJSON('/api/next-game');
            if (nextData.success) updateUI(nextData.game_state);
        }
    } catch (error) {
        console.error('Game loop error:', error);
        setThinking(false);
        showError(error.message);
    } finally {
        isRunning = false;
    }
}

async function revealChoices(gptChoice, claudeChoice, winner) {
    setPhase('Shoot!', true);

    // Rock, paper, scissors, shoot!
    for (const word of ['Rock', 'Paper', 'Scissors']) {
        setCallout(word + '…');
        pump();
        await sleep(400);
    }

    setCallout('Shoot!');
    showChoice('gpt', gptChoice);
    showChoice('claude', claudeChoice);
    await sleep(450);

    const gpt = CHOICES[gptChoice];
    const claude = CHOICES[claudeChoice];

    if (winner === 'gpt' || winner === 'claude') {
        const loser = winner === 'gpt' ? 'claude' : 'gpt';
        const winChoice = winner === 'gpt' ? gptChoice : claudeChoice;
        const loseChoice = winner === 'gpt' ? claudeChoice : gptChoice;

        PLAYERS[winner].els.hand.classList.add('is-winner');
        PLAYERS[loser].els.hand.classList.add('is-loser');
        setCallout(`${PLAYERS[winner].name} wins.`, `winner-${winner}`);
        gameStatusEl.textContent = `${CHOICES[winChoice].label} ${VERBS[winChoice]} ${CHOICES[loseChoice].label.toLowerCase()}.`;
    } else {
        PLAYERS.gpt.els.hand.classList.add('is-draw');
        PLAYERS.claude.els.hand.classList.add('is-draw');
        setCallout('Draw.', 'winner-draw');
        gameStatusEl.textContent = `Both threw ${(gpt || claude).label.toLowerCase()}.`;
    }
}

function showChoice(key, choice) {
    const { hand, glyph, label } = PLAYERS[key].els;
    const info = CHOICES[choice];
    glyph.textContent = info ? info.emoji : '❔';
    label.textContent = info ? info.label : choice;
    hand.classList.remove('is-thinking', 'is-pumping');
    void hand.offsetWidth; // restart animation
    hand.classList.add('is-revealed');
}

function pump() {
    for (const key of Object.keys(PLAYERS)) {
        const { hand } = PLAYERS[key].els;
        hand.classList.remove('is-thinking', 'is-pumping');
        void hand.offsetWidth;
        hand.classList.add('is-pumping');
    }
}

function showFinal(state) {
    const gptWins = state.gpt_stats.wins;
    const claudeWins = state.claude_stats.wins;
    const draws = state.gpt_stats.draws || 0;

    let winner = 'draw';
    if (gptWins > claudeWins) winner = 'gpt';
    else if (claudeWins > gptWins) winner = 'claude';

    arenaEl.classList.add('is-final');
    calloutKickerEl.textContent = 'Final result';
    setPhase('Final', false);

    const title = winner === 'draw' ? 'A perfect tie.' : `${PLAYERS[winner].name} takes the match.`;
    setCallout(title, `winner-${winner}`);
    const score = document.createElement('span');
    score.className = 'final-score';
    score.textContent = `${gptWins} – ${claudeWins}` + (draws ? ` · ${draws} draw${draws === 1 ? '' : 's'}` : '');
    resultDisplayEl.appendChild(score);

    const gptName = state.gpt_display_name || 'GPT';
    const claudeName = state.claude_display_name || 'Claude';
    gameStatusEl.textContent = winner === 'draw'
        ? `${gptName} and ${claudeName} couldn't be separated.`
        : `${winner === 'gpt' ? gptName : claudeName} over ${winner === 'gpt' ? claudeName : gptName} after ${state.total_rounds} round${state.total_rounds === 1 ? '' : 's'}.`;

    // Trophy hands
    for (const key of Object.keys(PLAYERS)) {
        const { hand, glyph, label } = PLAYERS[key].els;
        hand.className = 'hand is-revealed';
        if (winner === 'draw') {
            glyph.textContent = '🤝';
            hand.classList.add('is-draw');
            label.textContent = 'Draw';
        } else if (key === winner) {
            glyph.textContent = '🏆';
            hand.classList.add('is-winner');
            label.textContent = 'Winner';
        } else {
            glyph.textContent = '🫡';
            hand.classList.add('is-loser');
            label.textContent = 'Runner-up';
        }
    }

    btnRetry.hidden = true;
    btnRematch.hidden = false;
    actionsEl.hidden = false;

}

function showError(message) {
    calloutKickerEl.textContent = 'Something went wrong';
    setCallout('Round interrupted.', 'is-error');
    gameStatusEl.textContent = message || 'Check the server logs for details.';
    setPhase('Paused', false);
    for (const key of Object.keys(PLAYERS)) {
        const { clockLabel, reasoning } = PLAYERS[key].els;
        clockLabel.textContent = 'Stopped';
        if (reasoning.classList.contains('is-thinking')) {
            reasoning.textContent = 'No answer this round.';
        }
    }
    btnRetry.hidden = false;
    btnRematch.hidden = true;
    actionsEl.hidden = false;
}

function hideActions() {
    actionsEl.hidden = true;
}

// ---------- Arena helpers ----------
function resetArena() {
    hideActions();
    arenaEl.classList.remove('is-final');
    for (const key of Object.keys(PLAYERS)) {
        const { hand, glyph, label, clock, clockLabel, timer } = PLAYERS[key].els;
        hand.className = 'hand';
        glyph.textContent = FIST;
        label.textContent = PLAYERS[key].name;
        clock.classList.remove('is-ticking');
        clockLabel.textContent = 'Ready';
        timer.textContent = '0.0s';
    }
}

function clearReasoning() {
    for (const key of Object.keys(PLAYERS)) {
        const el = PLAYERS[key].els.reasoning;
        el.className = 'reasoning-text is-empty';
        el.textContent = 'Waiting for the first move.';
    }
}

function setCallout(text, modifier) {
    resultDisplayEl.textContent = text;
    resultDisplayEl.className = 'callout-main';
    if (modifier) resultDisplayEl.classList.add(modifier);
    void resultDisplayEl.offsetWidth;
    resultDisplayEl.classList.add('pop');
}

function setPhase(text, live) {
    phaseIndicator.textContent = text;
    phaseIndicator.classList.toggle('is-live', Boolean(live));
}

function setThinking(on) {
    for (const key of Object.keys(PLAYERS)) {
        const { hand, clock, clockLabel, reasoning } = PLAYERS[key].els;
        hand.classList.toggle('is-thinking', on);
        clock.classList.toggle('is-ticking', on);
        clockLabel.textContent = on ? 'Thinking' : 'Answered';
        if (on) {
            reasoning.className = 'reasoning-text is-thinking';
            reasoning.textContent = 'Thinking…';
        }
    }
    if (on) startTimer();
    else stopTimer();
}

function startTimer() {
    stopTimer();
    const start = performance.now();
    PLAYERS.gpt.els.timer.textContent = '0.0s';
    PLAYERS.claude.els.timer.textContent = '0.0s';

    timerInterval = setInterval(() => {
        const elapsed = ((performance.now() - start) / 1000).toFixed(1) + 's';
        PLAYERS.gpt.els.timer.textContent = elapsed;
        PLAYERS.claude.els.timer.textContent = elapsed;
    }, 100);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}


// ---------- UI sync ----------
function updateUI(state) {
    roundNumberEl.textContent = state.current_round;
    totalRoundsEl.textContent = state.total_rounds;

    if (state.gpt_display_name) gptModelNameEl.textContent = state.gpt_display_name;
    if (state.claude_display_name) claudeModelNameEl.textContent = state.claude_display_name;

    // Scores
    setScore('gpt', gptScoreEl, state.gpt_stats.wins);
    setScore('claude', claudeScoreEl, state.claude_stats.wins);
    updateMomentum(state.gpt_stats.wins, state.claude_stats.wins);
    updatePips(state);

    for (const key of Object.keys(PLAYERS)) {
        const els = PLAYERS[key].els;
        const stats = state[`${key}_stats`];
        els.wins.textContent = stats.wins;
        els.losses.textContent = stats.losses;
        els.draws.textContent = stats.draws || 0;

        const last = state[`${key}_last_time`];
        els.lastTime.textContent = formatSeconds(last);
        els.totalTime.textContent = formatSeconds(state[`${key}_total_time`]);
        if (state.round_history.length && !els.clock.classList.contains('is-ticking')) {
            els.timer.textContent = formatSeconds(last);
        }

        const reasoning = state[`${key}_reasoning`];
        if (reasoning) renderReasoning(els.reasoning, reasoning);
    }

    updateRoundLog(state.round_history);
}

function setScore(key, el, value) {
    el.textContent = value;
    if (value > lastScores[key]) {
        el.classList.remove('bump');
        void el.offsetWidth;
        el.classList.add('bump');
    }
    lastScores[key] = value;
}

function updateMomentum(gptWins, claudeWins) {
    const total = gptWins + claudeWins;
    const gptShare = total === 0 ? 50 : (gptWins / total) * 100;
    momentumGptEl.style.width = gptShare + '%';
    momentumClaudeEl.style.width = 100 - gptShare + '%';
}

function updatePips(state) {
    const history = state.round_history;
    roundPipsEl.innerHTML = '';
    for (let i = 1; i <= state.total_rounds; i++) {
        const pip = document.createElement('span');
        pip.className = 'pip';
        const played = history.find((r) => r.round === i);
        if (played) pip.classList.add(`win-${played.winner}`);
        else if (i === state.current_round && !state.all_rounds_complete) pip.classList.add('is-current');
        roundPipsEl.appendChild(pip);
    }
}

// Light formatting: escape everything, then allow **bold** headings.
function renderReasoning(el, text) {
    const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    el.innerHTML = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    el.className = 'reasoning-text';
    void el.offsetWidth;
    el.classList.add('is-fresh');
    el.scrollTop = 0;
}

function updateRoundLog(history) {
    logEmptyEl.hidden = history.length > 0;
    if (statsBody.children.length === history.length) return;

    statsBody.innerHTML = '';
    // Newest round first
    [...history].reverse().forEach((round) => {
        const row = document.createElement('li');
        row.className = 'log-row';

        const num = el('span', 'log-num', 'R' + round.round);
        const gpt = logPick('gpt', round.gpt_choice, round.gpt_time, round.winner === 'gpt');
        const result = el(
            'span',
            `log-result winner-${round.winner}`,
            round.winner === 'draw' ? 'Draw' : PLAYERS[round.winner].name + ' wins'
        );
        const claude = logPick('claude', round.claude_choice, round.claude_time, round.winner === 'claude');
        const clock = el('span', 'log-clock', round.time);

        row.append(num, gpt, result, claude, clock);
        statsBody.appendChild(row);
    });
}

function logPick(key, choice, seconds, isWinner) {
    const wrap = el('span', `log-pick ${key}${key === 'claude' ? ' right' : ''}${isWinner ? ' is-winner' : ''}`);
    const info = CHOICES[choice];
    wrap.appendChild(el('span', 'log-emoji', info ? info.emoji : '❔'));
    const text = el('span', 'log-pick-text');
    text.appendChild(el('span', 'log-choice', info ? info.label : choice));
    text.appendChild(el('span', 'log-time', formatSeconds(seconds)));
    wrap.appendChild(text);
    return wrap;
}

// ---------- Utilities ----------
function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function formatSeconds(value) {
    const n = Number(value) || 0;
    return n.toFixed(n >= 10 ? 1 : 2) + 's';
}

async function getJSON(url) {
    const response = await fetch(url);
    return parseResponse(response);
}

async function postJSON(url, body) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
    });
    return parseResponse(response);
}

async function parseResponse(response) {
    let data;
    try {
        data = await response.json();
    } catch (e) {
        throw new Error(`Server returned ${response.status} ${response.statusText}`);
    }
    if (!response.ok && !data.error) {
        data.error = `Server returned ${response.status}`;
    }
    return data;
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
