'use strict';

const byId = (id) => document.getElementById(id);
const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));
const formatReasoning = (value) => escapeHTML(value).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
const shortName = (name) => String(name).replace('Claude ', '').replace(/-(Sol|Luna|Astra)$/, ' $1');
const modelName = (game, side) => game[`${side}_display_name`].split(' · ')[0];
const effortName = (value) => ({ xhigh: 'Extra high' }[value] || value.charAt(0).toUpperCase() + value.slice(1));
const choices = { rock: '🪨 Rock', paper: '📄 Paper', scissors: '✂️ Scissors' };
const outcomes = ['gpt', 'draw', 'claude'];
let games = [];
let selectedEffort = 'all';

function counts(rounds) {
    return rounds.reduce((sum, round) => {
        sum[round.winner] += 1;
        return sum;
    }, { gpt: 0, claude: 0, draw: 0 });
}

function groupGames(list) {
    const groups = new Map();
    for (const game of list) {
        const key = `${game.gpt_model}/${game.claude_model}`;
        if (!groups.has(key)) groups.set(key, {
            gpt: shortName(modelName(game, 'gpt')),
            claude: shortName(modelName(game, 'claude')),
            rounds: [],
        });
        groups.get(key).rounds.push(...game.round_history);
    }
    return [...groups.values()];
}

function render() {
    const filtered = games.filter((game) => selectedEffort === 'all' ||
        (game.gpt_effort === selectedEffort && game.claude_effort === selectedEffort));
    const rounds = filtered.flatMap((game) => game.round_history);
    byId('archive-count').textContent = `${filtered.length} saved game${filtered.length === 1 ? '' : 's'}`;
    byId('results-content').hidden = !rounds.length;
    byId('results-status').hidden = !!rounds.length;
    if (!rounds.length) {
        byId('results-status').textContent = games.length ? 'No games at this reasoning level yet.' :
            'A clean slate. Play a game and your results will appear here.';
        return;
    }
    const scores = counts(rounds);
    const percent = (n) => `${Math.round(n / rounds.length * 100)}% of rounds`;
    const stats = [
        ['Rounds played', rounds.length, `${filtered.filter((g) => g.all_rounds_complete).length} completed games`, ''],
        ['GPT wins', scores.gpt, percent(scores.gpt), 'gpt-stat'],
        ['Claude wins', scores.claude, percent(scores.claude), 'claude-stat'],
        ['Draws', scores.draw, percent(scores.draw), ''],
    ];
    byId('results-stats').innerHTML = stats.map(([label, value, note, className]) =>
        `<dl class="result-stat ${className}"><dt>${label}</dt><dd>${value}</dd><small>${note}</small></dl>`).join('');
    renderRing(rounds.length, scores);
    const groups = groupGames(filtered);
    byId('matchup-bars').innerHTML = groups.map((group) => {
        const score = counts(group.rounds);
        const description = `${group.gpt} vs ${group.claude}: GPT ${score.gpt} wins, Claude ${score.claude} wins, ${score.draw} draws`;
        return `<div class="matchup-row"><div class="matchup-names"><span>${escapeHTML(group.gpt)} <small>vs</small> ${escapeHTML(group.claude)}</span><small>${group.rounds.length} rounds</small></div>
            <div class="outcome-bar" role="img" aria-label="${escapeHTML(description)}">${outcomes.filter((key) => score[key]).map((key) =>
                `<span class="outcome-${key}" style="flex-grow:${score[key]}" title="${key === 'draw' ? 'Draws' : key === 'gpt' ? 'GPT wins' : 'Claude wins'}: ${score[key]}">${score[key]}</span>`).join('')}</div></div>`;
    }).join('');
    renderPace(groups);
    byId('games-list').innerHTML = [...filtered].reverse().map(renderGame).join('');
}

function renderRing(total, score) {
    let offset = 0;
    const arcs = outcomes.filter((key) => score[key]).map((key) => {
        const size = score[key] / total * 100;
        const arc = `<circle cx="110" cy="110" r="90" pathLength="100" fill="none" stroke="var(--${key})" stroke-width="18" stroke-dasharray="${size} ${100 - size}" stroke-dashoffset="${-offset}"/>`;
        offset += size;
        return arc;
    }).join('');
    byId('outcome-ring').innerHTML = `<svg viewBox="0 0 220 220" role="img" aria-label="GPT ${score.gpt} wins, Claude ${score.claude} wins, ${score.draw} draws"><circle cx="110" cy="110" r="90" fill="none" stroke="var(--fill)" stroke-width="18"/>${arcs}</svg><div class="ring-label" aria-hidden="true"><strong>${total}</strong><span>rounds on record</span></div>`;
}

function renderPace(groups) {
    const averages = groups.map((group) => ({ ...group,
        gptTime: group.rounds.reduce((sum, r) => sum + r.gpt_time, 0) / group.rounds.length,
        claudeTime: group.rounds.reduce((sum, r) => sum + r.claude_time, 0) / group.rounds.length,
    }));
    const max = Math.max(1, ...averages.flatMap((g) => [g.gptTime, g.claudeTime]));
    byId('pace-chart').innerHTML = averages.map((group) => `<div class="pace-group"><h3>${escapeHTML(group.gpt)} / ${escapeHTML(group.claude)}</h3>${['gpt', 'claude'].map((key) =>
        `<div class="pace-line"><span>${key === 'gpt' ? 'GPT' : 'Claude'}</span><div class="pace-track" aria-hidden="true"><span class="${key}-swatch" style="width:${group[`${key}Time`] / max * 100}%"></span></div><b>${group[`${key}Time`].toFixed(1)}s</b></div>`).join('')}</div>`).join('');
}

function renderGame(game) {
    const score = counts(game.round_history);
    const matched = game.gpt_effort === game.claude_effort;
    const effort = matched ? `${effortName(game.gpt_effort)} reasoning` :
        `GPT ${effortName(game.gpt_effort)} / Claude ${effortName(game.claude_effort)} reasoning`;
    const date = new Date(game.started_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    const title = `${shortName(modelName(game, 'gpt'))} vs ${shortName(modelName(game, 'claude'))}`;
    const draws = score.draw ? ` · ${score.draw} draw${score.draw === 1 ? '' : 's'}` : '';
    return `<details class="game-entry"><summary><span class="game-title">${escapeHTML(title)}<small>${escapeHTML(effort)} · ${escapeHTML(date)} · ${game.round_history.length}/${game.total_rounds} rounds${game.all_rounds_complete ? ' · Complete' : ' · Unfinished'}${draws}</small></span><span class="game-score" aria-label="GPT ${score.gpt}, Claude ${score.claude}, ${score.draw} draws"><span class="gpt-score">${score.gpt}</span> : <span class="claude-score">${score.claude}</span></span></summary>
        ${game.round_history.map((round) => `<article class="round-detail"><h4>Round ${round.round}<span>${round.winner === 'draw' ? 'Draw' : round.winner === 'gpt' ? 'GPT wins' : 'Claude wins'}</span></h4><div class="round-explanations">${['gpt', 'claude'].map((key) =>
            `<div class="round-player"><strong>${escapeHTML(modelName(game, key))} · ${choices[round[`${key}_choice`]]}</strong><small>${round[`${key}_time`].toFixed(2)}s</small><p>${formatReasoning(round[`${key}_reasoning`] || 'No explanation provided.')}</p></div>`).join('')}</div></article>`).join('')}</details>`;
}

async function loadResults() {
    byId('retry-results').hidden = true;
    byId('results-status').hidden = false;
    byId('results-status').textContent = 'Loading saved games…';
    try {
        const response = await fetch('/api/results', { cache: 'no-store' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Could not load results.');
        games = data.games;
        const available = [...new Set(games.filter((g) => g.gpt_effort === g.claude_effort).map((g) => g.gpt_effort))];
        for (const effort of available) {
            if (byId('effort-filters').querySelector(`[data-effort="${CSS.escape(effort)}"]`)) continue;
            const button = document.createElement('button');
            button.type = 'button';
            button.dataset.effort = effort;
            button.setAttribute('aria-pressed', 'false');
            button.textContent = effortName(effort);
            byId('effort-filters').append(button);
        }
        render();
    } catch (error) {
        byId('results-content').hidden = true;
        byId('results-status').textContent = error.message;
        byId('retry-results').hidden = false;
    }
}

byId('effort-filters').addEventListener('click', (event) => {
    const button = event.target.closest('button[data-effort]');
    if (!button) return;
    selectedEffort = button.dataset.effort;
    for (const item of byId('effort-filters').querySelectorAll('button')) {
        item.setAttribute('aria-pressed', String(item === button));
    }
    render();
});
byId('retry-results').addEventListener('click', loadResults);
loadResults();
