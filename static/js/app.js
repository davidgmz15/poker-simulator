/**
 * Poker Academy - Frontend JavaScript
 * Interactive poker learning experience
 */

// ============================================
// STATE MANAGEMENT
// ============================================

const state = {
    gameState: null,
    heroFolded: false,
    settings: {
        numPlayers: 6,
        startingStack: 1000,
        bigBlind: 10,
        heroPosition: 5
    }
};

// ============================================
// DOM ELEMENTS
// ============================================

const elements = {
    // Buttons
    newHandBtn: document.getElementById('newHandBtn'),
    settingsBtn: document.getElementById('settingsBtn'),
    foldBtn: document.getElementById('foldBtn'),
    checkBtn: document.getElementById('checkBtn'),
    callBtn: document.getElementById('callBtn'),
    raiseBtn: document.getElementById('raiseBtn'),
    dealFlopBtn: document.getElementById('dealFlopBtn'),
    dealTurnBtn: document.getElementById('dealTurnBtn'),
    dealRiverBtn: document.getElementById('dealRiverBtn'),
    getAdviceBtn: document.getElementById('getAdviceBtn'),
    
    // Displays
    potAmount: document.getElementById('potAmount'),
    potOddsDisplay: document.getElementById('potOddsDisplay'),
    potOddsPercent: document.getElementById('potOddsPercent'),
    potOddsBar: document.getElementById('potOddsBar'),
    equityDisplay: document.getElementById('equityDisplay'),
    equitySubtext: document.getElementById('equitySubtext'),
    equityGauge: document.getElementById('equityGauge'),
    requiredEquityMarker: document.getElementById('requiredEquityMarker'),
    decisionDisplay: document.getElementById('decisionDisplay'),
    decisionEV: document.getElementById('decisionEV'),
    decisionReasoning: document.getElementById('decisionReasoning'),
    
    // Cards
    communityCards: document.getElementById('communityCards'),
    heroCards: document.getElementById('heroCards'),
    heroHandStrength: document.getElementById('heroHandStrength'),
    
    // Hero Info
    heroPosition: document.getElementById('heroPosition'),
    heroStack: document.getElementById('heroStack'),
    
    // Outs
    flushDrawOuts: document.getElementById('flushDrawOuts'),
    straightDrawOuts: document.getElementById('straightDrawOuts'),
    pairOuts: document.getElementById('pairOuts'),
    totalOuts: document.getElementById('totalOuts'),
    
    // Seats
    seatsContainer: document.getElementById('seatsContainer'),
    streetIndicator: document.getElementById('streetIndicator'),
    
    // Raise controls
    raiseSlider: document.getElementById('raiseSlider'),
    raiseAmount: document.getElementById('raiseAmount'),
    callAmount: document.getElementById('callAmount'),
    
    // Chat
    chatMessages: document.getElementById('chatMessages'),
    rangeDisplay: document.getElementById('rangeDisplay'),
    
    // Modal
    settingsModal: document.getElementById('settingsModal'),
    closeSettings: document.getElementById('closeSettings'),
    saveSettings: document.getElementById('saveSettings'),
    numPlayers: document.getElementById('numPlayers'),
    startingStack: document.getElementById('startingStack'),
    bigBlind: document.getElementById('bigBlind'),
    heroPositionSelect: document.getElementById('heroPosition')
};

// ============================================
// API FUNCTIONS
// ============================================

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`/api/${endpoint}`, options);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { error: error.message };
    }
}

async function startNewHand() {
    // Reset folded state for new hand
    state.heroFolded = false;
    
    const result = await apiCall('new-hand', 'POST', {
        num_players: state.settings.numPlayers,
        hero_position: state.settings.heroPosition,
        starting_stack: state.settings.startingStack,
        big_blind: state.settings.bigBlind
    });
    
    if (!result.error) {
        state.gameState = result;
        updateUI();
        addChatMessage('coach', `New hand dealt! You're in the **${result.hero.position}** position with **${formatCards(result.hole_cards)}**. ${getHandDescription(result)}`);
    }
    
    return result;
}

async function dealStreet(street) {
    const result = await apiCall(`deal/${street}`, 'POST');
    
    if (!result.error) {
        state.gameState = result;
        updateUI();
        
        const streetName = street.charAt(0).toUpperCase() + street.slice(1);
        addChatMessage('coach', `**${streetName}** dealt: ${formatCards(result.board.slice(-getNewCards(street)))}. ${getStreetAnalysis(result)}`);
    }
    
    return result;
}

async function processAction(action, amount = 0) {
    // Check if we've folded this hand
    if (state.heroFolded) {
        addChatMessage('coach', "You've already folded this hand. Click **New Hand** to play again.");
        return { error: 'Already folded' };
    }
    
    // Remember action count before
    const prevActionCount = state.gameState?.action_history?.length || 0;
    
    const result = await apiCall('action', 'POST', {
        action,
        amount
    });
    
    if (result.error) {
        addChatMessage('coach', `Action error: ${result.error}`);
    } else {
        state.gameState = result;
        
        // Track if hero folded
        if (action === 'fold') {
            state.heroFolded = true;
            addChatMessage('coach', "You folded. Click **New Hand** to play again.");
        } else {
            // Show what happened (hero action + opponent responses)
            const newActions = result.action_history.slice(prevActionCount);
            if (newActions.length > 0) {
                const actionSummary = summarizeActions(newActions, result.opponents);
                if (actionSummary) {
                    addChatMessage('coach', actionSummary);
                }
            }
        }
        
        // Check if betting round is complete
        checkBettingRoundComplete(result);
        
        updateUI();
    }
    
    return result;
}

function summarizeActions(actions, opponents) {
    if (!actions || actions.length === 0) return null;
    
    const parts = [];
    
    for (const act of actions) {
        const playerIdx = act.player;
        let playerName;
        
        // Find player name
        if (playerIdx === 0) {
            playerName = 'You';
        } else {
            const opp = opponents.find((o, i) => i === playerIdx - 1);
            playerName = opp ? opp.name : `Player ${playerIdx + 1}`;
        }
        
        if (act.action === 'fold') {
            parts.push(`**${playerName}** folds`);
        } else if (act.action === 'check') {
            parts.push(`**${playerName}** checks`);
        } else if (act.action === 'call') {
            parts.push(`**${playerName}** calls $${act.amount}`);
        } else if (act.action === 'bet') {
            parts.push(`**${playerName}** bets $${act.amount}`);
        } else if (act.action === 'raise') {
            parts.push(`**${playerName}** raises to $${act.amount}`);
        }
    }
    
    return parts.join(' • ');
}

function checkBettingRoundComplete(result) {
    // Count active players (not folded)
    const activePlayers = result.active_players;
    
    if (activePlayers <= 1) {
        addChatMessage('coach', "🏆 **Hand over!** All opponents folded. Click **New Hand** to continue.");
        state.heroFolded = true; // Disable actions
        return;
    }
    
    // Check if we can deal next street
    const street = result.street;
    if (street === 'preflop') {
        addChatMessage('coach', "Preflop action complete. Click **Deal Flop** to see the flop.");
    } else if (street === 'flop') {
        addChatMessage('coach', "Flop action complete. Click **Deal Turn** to see the turn.");
    } else if (street === 'turn') {
        addChatMessage('coach', "Turn action complete. Click **Deal River** to see the river.");
    } else if (street === 'river') {
        addChatMessage('coach', "🏁 **Showdown!** Hand is complete. Click **New Hand** to play again.");
        state.heroFolded = true; // Disable actions after showdown
    }
}

async function getAIAdvice() {
    elements.getAdviceBtn.disabled = true;
    elements.getAdviceBtn.textContent = '🔄 Analyzing...';
    
    const result = await apiCall('ai-advice', 'POST');
    
    elements.getAdviceBtn.disabled = false;
    elements.getAdviceBtn.textContent = '🎯 Get Strategic Advice';
    
    if (!result.error && result.advice) {
        addChatMessage('coach', result.advice);
    }
    
    return result;
}

async function explainConcept(concept) {
    const result = await apiCall(`explain/${concept}`, 'GET');
    
    if (!result.error && result.explanation) {
        addChatMessage('coach', result.explanation);
    }
    
    return result;
}

// ============================================
// UI UPDATE FUNCTIONS
// ============================================

function updateUI() {
    const gs = state.gameState;
    if (!gs) return;
    
    // Update pot
    elements.potAmount.textContent = `$${gs.pot}`;
    
    // Update street indicator
    elements.streetIndicator.querySelector('.street-name').textContent = gs.street.toUpperCase();
    
    // Update hero info
    elements.heroPosition.textContent = gs.hero.position;
    elements.heroStack.textContent = `$${gs.hero.stack}`;
    
    // Update hero cards
    updateHeroCards(gs.hole_cards);
    
    // Update community cards
    updateCommunityCards(gs.board, gs.street);
    
    // Update opponent seats
    updateSeats(gs.opponents);
    
    // Update statistics
    updateStatistics(gs.statistics);
    
    // Update action buttons
    updateActionButtons(gs);
    
    // Update deal buttons
    updateDealButtons(gs.street);
    
    // Update hand strength
    updateHandStrength(gs);
    
    // Update opponent ranges
    updateRanges(gs.opponents);
}

function updateHeroCards(cards) {
    const container = elements.heroCards;
    container.innerHTML = '';
    
    cards.forEach((card, index) => {
        const cardEl = createCardElement(card, true);
        cardEl.style.animationDelay = `${index * 0.1}s`;
        container.appendChild(cardEl);
    });
}

function updateCommunityCards(board, street) {
    const container = elements.communityCards;
    container.innerHTML = '';
    
    for (let i = 0; i < 5; i++) {
        if (i < board.length) {
            const cardEl = createCardElement(board[i]);
            cardEl.classList.add('revealed');
            cardEl.style.animationDelay = `${i * 0.1}s`;
            container.appendChild(cardEl);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'card card-placeholder';
            container.appendChild(placeholder);
        }
    }
}

function createCardElement(cardStr, isHero = false) {
    const [rank, suit] = cardStr.split('-');
    const suitSymbols = { H: '♥', D: '♦', C: '♣', S: '♠' };
    const suitClasses = { H: 'hearts', D: 'diamonds', C: 'clubs', S: 'spades' };
    
    const card = document.createElement('div');
    card.className = `card ${suitClasses[suit]}${isHero ? ' hero-card' : ''}`;
    
    card.innerHTML = `
        <span class="card-rank">${rank}</span>
        <span class="card-suit">${suitSymbols[suit]}</span>
        <span class="card-rank-bottom">${rank}</span>
    `;
    
    return card;
}

function updateSeats(opponents) {
    const container = elements.seatsContainer;
    container.innerHTML = '';
    
    const numOpponents = opponents.length;
    const positions = getSeatPositions(numOpponents);
    
    opponents.forEach((opp, index) => {
        const seat = document.createElement('div');
        seat.className = 'seat';
        seat.style.left = positions[index].x;
        seat.style.top = positions[index].y;
        
        seat.innerHTML = `
            <div class="seat-cards">
                <div class="card card-placeholder" style="width: 28px; height: 40px;"></div>
                <div class="card card-placeholder" style="width: 28px; height: 40px;"></div>
            </div>
            <div class="seat-info ${opp.folded ? 'folded' : ''}">
                <div class="seat-position">${opp.position}</div>
                <div class="seat-name">${opp.name}</div>
                <div class="seat-stack">$${opp.stack}</div>
                ${opp.bet > 0 ? `<div class="seat-bet">Bet: $${opp.bet}</div>` : ''}
            </div>
        `;
        
        container.appendChild(seat);
    });
}

function getSeatPositions(numOpponents) {
    // Position seats around the elliptical table
    const positions = [];
    const centerX = 50;
    const centerY = 50;
    const radiusX = 42;
    const radiusY = 35;
    
    for (let i = 0; i < numOpponents; i++) {
        // Distribute evenly around top half of table
        const angle = Math.PI + (Math.PI * (i + 1)) / (numOpponents + 1);
        const x = centerX + radiusX * Math.cos(angle);
        const y = centerY + radiusY * Math.sin(angle);
        positions.push({ x: `${x}%`, y: `${y}%` });
    }
    
    return positions;
}

function updateStatistics(stats) {
    // Pot Odds
    const potOdds = stats.pot_odds;
    elements.potOddsDisplay.textContent = potOdds.display || '-';
    elements.potOddsPercent.textContent = potOdds.percentage > 0 
        ? `Need ${potOdds.required_equity}% equity to call`
        : 'No bet to call';
    elements.potOddsBar.style.width = `${Math.min(potOdds.percentage * 2, 100)}%`;
    
    // Equity
    const equity = stats.equity;
    elements.equityDisplay.textContent = `${equity.equity}%`;
    elements.equityDisplay.className = 'stat-main equity-value ' + getEquityClass(equity.equity);
    elements.equitySubtext.textContent = `Win: ${equity.win_percentage}% | Tie: ${equity.tie_percentage}%`;
    
    // Equity gauge
    const gaugeWidth = 100 - equity.equity;
    elements.equityGauge.style.width = `${gaugeWidth}%`;
    
    // Required equity marker
    const requiredEquity = stats.pot_odds.required_equity || 0;
    elements.requiredEquityMarker.style.left = `${requiredEquity}%`;
    
    // Outs
    const draws = stats.draws;
    const outs = stats.outs;
    
    updateOutItem('flushDrawOuts', draws.flush_draw ? draws.flush_draw_outs : 0, draws.flush_draw);
    updateOutItem('straightDrawOuts', draws.straight_outs || 0, draws.open_ended_straight_draw || draws.gutshot_straight_draw);
    updateOutItem('pairOuts', (draws.overcard_outs || 0), draws.overcards?.length > 0);
    updateOutItem('totalOuts', outs.total || draws.total_drawing_outs || 0, true);
    
    // Decision
    const decision = stats.decision;
    updateDecision(decision);
}

function updateOutItem(elementId, count, isActive) {
    const element = document.getElementById(elementId);
    const countEl = element.querySelector('.out-count');
    countEl.textContent = count || '-';
    
    if (isActive && count > 0) {
        element.classList.add('active');
    } else {
        element.classList.remove('active');
    }
}

function getEquityClass(equity) {
    if (equity >= 50) return 'high';
    if (equity >= 30) return 'medium';
    return 'low';
}

function updateDecision(decision) {
    const display = elements.decisionDisplay;
    const actionEl = display.querySelector('.decision-action');
    
    const action = decision.recommended_action || '-';
    actionEl.textContent = action;
    
    // Remove old classes
    display.classList.remove('fold', 'call', 'raise', 'check');
    
    // Add appropriate class
    if (action.includes('FOLD')) {
        display.classList.add('fold');
    } else if (action.includes('CALL')) {
        display.classList.add('call');
    } else if (action.includes('RAISE')) {
        display.classList.add('raise');
    } else if (action.includes('CHECK')) {
        display.classList.add('check');
    }
    
    elements.decisionEV.textContent = `EV: ${decision.expected_value >= 0 ? '+' : ''}$${decision.expected_value}`;
    elements.decisionReasoning.textContent = decision.reasoning || '';
}

function updateActionButtons(gs) {
    const toCall = gs.to_call;
    const canCheck = toCall === 0;
    
    // Disable all actions if hero has folded
    if (state.heroFolded) {
        elements.foldBtn.disabled = true;
        elements.checkBtn.disabled = true;
        elements.callBtn.disabled = true;
        elements.raiseBtn.disabled = true;
        elements.raiseSlider.disabled = true;
        return;
    }
    
    elements.foldBtn.disabled = false;
    elements.checkBtn.disabled = !canCheck;
    elements.callBtn.disabled = canCheck;
    elements.raiseBtn.disabled = false;
    elements.raiseSlider.disabled = false;
    
    elements.callAmount.textContent = `$${toCall}`;
    
    // Update raise slider
    const minRaise = Math.max(gs.current_bet * 2, state.settings.bigBlind);
    const maxRaise = gs.hero.stack;
    elements.raiseSlider.min = minRaise;
    elements.raiseSlider.max = maxRaise;
    elements.raiseSlider.value = Math.min(minRaise * 2, maxRaise);
    elements.raiseAmount.textContent = `$${elements.raiseSlider.value}`;
}

function updateDealButtons(street) {
    elements.dealFlopBtn.disabled = street !== 'preflop';
    elements.dealTurnBtn.disabled = street !== 'flop';
    elements.dealRiverBtn.disabled = street !== 'turn';
}

function updateHandStrength(gs) {
    const handClass = gs.statistics.hand_classification;
    let strengthText = '-';
    
    if (handClass && handClass.notation) {
        strengthText = `${handClass.notation} (${handClass.tier})`;
    }
    
    elements.heroHandStrength.querySelector('.hand-name').textContent = strengthText;
}

function updateRanges(opponents) {
    const container = elements.rangeDisplay;
    
    if (!opponents || opponents.every(o => !o.range)) {
        container.innerHTML = '<p class="range-placeholder">Opponent ranges will update based on their actions.</p>';
        return;
    }
    
    let html = '';
    opponents.forEach((opp, index) => {
        if (opp.range && !opp.folded) {
            html += `
                <div class="range-item">
                    <div class="range-player">${opp.name} (${opp.position})</div>
                    <div class="range-percentage">${opp.range.percentage}% of hands</div>
                    <div class="range-hands">${formatRange(opp.range.range)}</div>
                </div>
            `;
        }
    });
    
    container.innerHTML = html || '<p class="range-placeholder">All opponents have folded.</p>';
}

function formatRange(range) {
    if (!range || !Array.isArray(range)) return '-';
    
    // Group by type and show first few
    const pairs = range.filter(h => h.length === 2);
    const suited = range.filter(h => h.endsWith('s'));
    const offsuit = range.filter(h => h.endsWith('o'));
    
    let result = [];
    if (pairs.length > 0) result.push(`Pairs: ${pairs.slice(0, 5).join(', ')}${pairs.length > 5 ? '...' : ''}`);
    if (suited.length > 0) result.push(`Suited: ${suited.slice(0, 5).join(', ')}${suited.length > 5 ? '...' : ''}`);
    if (offsuit.length > 0) result.push(`Offsuit: ${offsuit.slice(0, 3).join(', ')}${offsuit.length > 3 ? '...' : ''}`);
    
    return result.join(' | ') || '-';
}

// ============================================
// CHAT FUNCTIONS
// ============================================

function addChatMessage(type, content) {
    const container = elements.chatMessages;
    
    const message = document.createElement('div');
    message.className = `chat-message ${type}`;
    
    const avatar = type === 'coach' ? '🎓' : '👤';
    
    // Convert markdown-like syntax to HTML
    let htmlContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '</p><p>');
    
    message.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <p>${htmlContent}</p>
        </div>
    `;
    
    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function formatCards(cards) {
    if (!cards || cards.length === 0) return '-';
    
    const suitSymbols = { H: '♥', D: '♦', C: '♣', S: '♠' };
    
    return cards.map(card => {
        const [rank, suit] = card.split('-');
        return `${rank}${suitSymbols[suit]}`;
    }).join(' ');
}

function getNewCards(street) {
    switch (street) {
        case 'flop': return 3;
        case 'turn': return 1;
        case 'river': return 1;
        default: return 0;
    }
}

function getHandDescription(gs) {
    const handClass = gs.statistics.hand_classification;
    if (!handClass) return '';
    
    return `Your hand is classified as **${handClass.tier}** - ${handClass.strength}. ${handClass.multiway_preference}.`;
}

function getStreetAnalysis(gs) {
    const stats = gs.statistics;
    const equity = stats.equity.equity;
    const potOdds = stats.pot_odds;
    
    let analysis = `Your equity is now **${equity}%**. `;
    
    if (stats.draws.flush_draw) {
        analysis += `You have a **flush draw** (9 outs). `;
    }
    if (stats.draws.open_ended_straight_draw) {
        analysis += `You have an **open-ended straight draw** (8 outs). `;
    }
    if (stats.draws.gutshot_straight_draw) {
        analysis += `You have a **gutshot straight draw** (4 outs). `;
    }
    
    if (gs.to_call > 0) {
        const isProfitable = equity > potOdds.required_equity;
        analysis += isProfitable 
            ? `A call would be **profitable** here.`
            : `A call would be **unprofitable** based on pot odds.`;
    }
    
    return analysis;
}

// ============================================
// EVENT LISTENERS
// ============================================

// New Hand
elements.newHandBtn.addEventListener('click', startNewHand);

// Deal buttons
elements.dealFlopBtn.addEventListener('click', () => dealStreet('flop'));
elements.dealTurnBtn.addEventListener('click', () => dealStreet('turn'));
elements.dealRiverBtn.addEventListener('click', () => dealStreet('river'));

// Action buttons
elements.foldBtn.addEventListener('click', () => processAction('fold'));
elements.checkBtn.addEventListener('click', () => processAction('check'));
elements.callBtn.addEventListener('click', () => processAction('call'));
elements.raiseBtn.addEventListener('click', () => {
    const amount = parseInt(elements.raiseSlider.value);
    processAction('raise', amount);
});

// Raise slider
elements.raiseSlider.addEventListener('input', (e) => {
    elements.raiseAmount.textContent = `$${e.target.value}`;
});

// AI Advice
elements.getAdviceBtn.addEventListener('click', getAIAdvice);

// Concept buttons
document.querySelectorAll('.concept-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const concept = btn.dataset.concept;
        explainConcept(concept);
    });
});

// Settings Modal
elements.settingsBtn.addEventListener('click', () => {
    elements.settingsModal.classList.add('active');
});

elements.closeSettings.addEventListener('click', () => {
    elements.settingsModal.classList.remove('active');
});

elements.settingsModal.addEventListener('click', (e) => {
    if (e.target === elements.settingsModal) {
        elements.settingsModal.classList.remove('active');
    }
});

elements.saveSettings.addEventListener('click', () => {
    state.settings.numPlayers = parseInt(elements.numPlayers.value);
    state.settings.startingStack = parseInt(elements.startingStack.value);
    state.settings.bigBlind = parseInt(elements.bigBlind.value);
    state.settings.heroPosition = parseInt(elements.heroPositionSelect.value);
    
    elements.settingsModal.classList.remove('active');
    addChatMessage('coach', `Settings updated! ${state.settings.numPlayers} players, $${state.settings.startingStack} stacks, $${state.settings.bigBlind} big blind.`);
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    
    switch (e.key.toLowerCase()) {
        case 'n':
            startNewHand();
            break;
        case 'f':
            if (!elements.foldBtn.disabled) elements.foldBtn.click();
            break;
        case 'c':
            if (!elements.checkBtn.disabled) elements.checkBtn.click();
            else if (!elements.callBtn.disabled) elements.callBtn.click();
            break;
        case 'r':
            if (!elements.raiseBtn.disabled) elements.raiseBtn.click();
            break;
        case 'd':
            if (!elements.dealFlopBtn.disabled) elements.dealFlopBtn.click();
            else if (!elements.dealTurnBtn.disabled) elements.dealTurnBtn.click();
            else if (!elements.dealRiverBtn.disabled) elements.dealRiverBtn.click();
            break;
        case 'a':
            elements.getAdviceBtn.click();
            break;
    }
});

// ============================================
// INITIALIZATION
// ============================================

// Load initial state
(async function init() {
    // Check if there's an existing game state
    const state = await apiCall('state');
    if (state && state.hole_cards && state.hole_cards.length > 0) {
        state.gameState = state;
        updateUI();
    }
})();

console.log('🎰 Poker Academy loaded! Press N for new hand, F/C/R for actions, D to deal, A for advice.');

