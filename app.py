"""
Poker Simulator - Flask Backend API
A comprehensive poker learning tool with real-time statistics and AI coaching
"""
import os
import random
from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from typing import List, Dict, Optional
import json

from poker_engine import (
    Card, create_deck, evaluate_hand, compare_hands, HandRank,
    calculate_pot_odds, calculate_equity_monte_carlo, calculate_equity_rule_of_4_and_2,
    count_outs, detect_draws, classify_preflop_hand, analyze_decision,
    cards_from_strings, analyze_multiway_vs_headsup
)
from range_estimator import (
    Position, Action, estimate_preflop_range, narrow_range_postflop,
    analyze_bet_sizing, get_position_info, format_range_grid, get_range_summary
)
from ai_coach import AICoach, create_game_state

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'poker-simulator-dev-key-change-in-prod')
CORS(app)

# Initialize AI Coach
ai_coach = AICoach()


# ============================================================
# GAME STATE MANAGEMENT
# ============================================================

class GameManager:
    """Manages the poker game state"""
    
    def __init__(self):
        self.reset_game()
    
    def reset_game(self):
        """Reset to a fresh game state"""
        self.deck = create_deck()
        random.shuffle(self.deck)
        self.deck_index = 0
        
        self.players = []
        self.hero_index = 0
        self.button_index = 0
        
        self.hole_cards = []
        self.board = []
        self.pot = 0
        self.current_bet = 0
        self.street = 'preflop'
        
        self.player_bets = []
        self.player_folded = []
        self.player_stacks = []
        self.player_positions = []
        self.player_ranges = []
        
        self.action_history = []
        self.is_preflop_aggressor = False
        
    def setup_hand(self, num_players: int = 6, hero_position: int = 0, starting_stack: float = 1000, 
                   big_blind: float = 10):
        """Setup a new hand"""
        self.reset_game()
        
        self.num_players = num_players
        self.hero_index = hero_position
        self.big_blind = big_blind
        self.small_blind = big_blind / 2
        
        # Setup players
        self.players = [f"Player {i+1}" for i in range(num_players)]
        self.players[hero_position] = "You"
        
        self.player_stacks = [starting_stack] * num_players
        self.player_bets = [0.0] * num_players
        self.player_folded = [False] * num_players
        
        # Assign positions based on button
        self.button_index = (hero_position - 1) % num_players
        self._assign_positions()
        
        # Post blinds
        sb_index = (self.button_index + 1) % num_players
        bb_index = (self.button_index + 2) % num_players
        
        self.player_stacks[sb_index] -= self.small_blind
        self.player_bets[sb_index] = self.small_blind
        
        self.player_stacks[bb_index] -= big_blind
        self.player_bets[bb_index] = big_blind
        
        self.pot = self.small_blind + big_blind
        self.current_bet = big_blind
        
        # Deal hole cards
        self._deal_hole_cards()
        
        # Initialize opponent ranges
        self._initialize_ranges()
        
        return self.get_state()
    
    def _assign_positions(self):
        """Assign position names to each player"""
        positions = []
        n = self.num_players
        
        # Standard position assignment for different table sizes
        if n == 2:
            position_names = [Position.BTN, Position.BB]
        elif n == 3:
            position_names = [Position.BTN, Position.SB, Position.BB]
        elif n == 4:
            position_names = [Position.BTN, Position.SB, Position.BB, Position.UTG]
        elif n == 5:
            position_names = [Position.BTN, Position.SB, Position.BB, Position.UTG, Position.CO]
        elif n == 6:
            position_names = [Position.BTN, Position.SB, Position.BB, Position.UTG, Position.MP, Position.CO]
        elif n == 7:
            position_names = [Position.BTN, Position.SB, Position.BB, Position.UTG, Position.UTG1, Position.MP, Position.CO]
        elif n == 8:
            position_names = [Position.BTN, Position.SB, Position.BB, Position.UTG, Position.UTG1, Position.MP, Position.MP1, Position.CO]
        else:
            position_names = [Position.BTN, Position.SB, Position.BB] + [Position.MP] * (n - 5) + [Position.CO, Position.BTN]
        
        for i in range(n):
            pos_index = (i - self.button_index) % n
            positions.append(position_names[pos_index] if pos_index < len(position_names) else Position.MP)
        
        self.player_positions = positions
    
    def _deal_hole_cards(self):
        """Deal 2 cards to each player"""
        for i in range(self.num_players):
            card1 = self.deck[self.deck_index]
            self.deck_index += 1
            card2 = self.deck[self.deck_index]
            self.deck_index += 1
            
            if i == self.hero_index:
                self.hole_cards = [card1, card2]
    
    def _initialize_ranges(self):
        """Initialize opponent ranges based on position"""
        self.player_ranges = []
        for i in range(self.num_players):
            if i == self.hero_index:
                self.player_ranges.append(None)  # We know our exact cards
            else:
                pos = self.player_positions[i]
                # Start with a wide range, will narrow based on actions
                range_data = estimate_preflop_range(pos, Action.CALL)
                self.player_ranges.append(range_data)
    
    def deal_flop(self):
        """Deal the flop (3 community cards)"""
        if self.street != 'preflop':
            return None
        
        # Burn card
        self.deck_index += 1
        
        # Deal 3 cards
        for _ in range(3):
            self.board.append(self.deck[self.deck_index])
            self.deck_index += 1
        
        self.street = 'flop'
        self._reset_betting_round()
        return self.get_state()
    
    def deal_turn(self):
        """Deal the turn (4th community card)"""
        if self.street != 'flop':
            return None
        
        # Burn card
        self.deck_index += 1
        
        # Deal 1 card
        self.board.append(self.deck[self.deck_index])
        self.deck_index += 1
        
        self.street = 'turn'
        self._reset_betting_round()
        return self.get_state()
    
    def deal_river(self):
        """Deal the river (5th community card)"""
        if self.street != 'turn':
            return None
        
        # Burn card
        self.deck_index += 1
        
        # Deal 1 card
        self.board.append(self.deck[self.deck_index])
        self.deck_index += 1
        
        self.street = 'river'
        self._reset_betting_round()
        return self.get_state()
    
    def _reset_betting_round(self):
        """Reset bets for a new betting round"""
        self.player_bets = [0.0] * self.num_players
        self.current_bet = 0
    
    def process_action(self, player_index: int, action: str, amount: float = 0):
        """Process a player action"""
        # Check if lists are initialized
        if not self.player_folded or player_index >= len(self.player_folded):
            return None
        
        if self.player_folded[player_index]:
            return None
        
        action = action.lower()
        
        if action == 'fold':
            self.player_folded[player_index] = True
            self.action_history.append({
                'player': player_index,
                'action': 'fold',
                'street': self.street
            })
            
            # Update opponent range to exclude strong hands
            if player_index != self.hero_index and self.player_ranges[player_index]:
                pos = self.player_positions[player_index]
                self.player_ranges[player_index] = estimate_preflop_range(pos, Action.FOLD)
        
        elif action == 'check':
            self.action_history.append({
                'player': player_index,
                'action': 'check',
                'street': self.street
            })
        
        elif action == 'call':
            call_amount = min(self.current_bet - self.player_bets[player_index], 
                            self.player_stacks[player_index])
            self.player_stacks[player_index] -= call_amount
            self.player_bets[player_index] += call_amount
            self.pot += call_amount
            
            self.action_history.append({
                'player': player_index,
                'action': 'call',
                'amount': call_amount,
                'street': self.street
            })
            
            # Update range for calling
            if player_index != self.hero_index and self.player_ranges[player_index]:
                pos = self.player_positions[player_index]
                self.player_ranges[player_index] = estimate_preflop_range(pos, Action.CALL, Action.RAISE)
        
        elif action in ['bet', 'raise']:
            bet_amount = amount
            
            # Calculate how much more they need to put in
            additional = bet_amount - self.player_bets[player_index]
            if additional > self.player_stacks[player_index]:
                additional = self.player_stacks[player_index]
                bet_amount = self.player_bets[player_index] + additional
            
            self.player_stacks[player_index] -= additional
            self.player_bets[player_index] = bet_amount
            self.pot += additional
            self.current_bet = bet_amount
            
            # Track preflop aggressor
            if self.street == 'preflop' and player_index == self.hero_index:
                self.is_preflop_aggressor = True
            
            self.action_history.append({
                'player': player_index,
                'action': action,
                'amount': bet_amount,
                'street': self.street
            })
            
            # Update range for raising
            if player_index != self.hero_index and self.player_ranges[player_index]:
                pos = self.player_positions[player_index]
                if self.current_bet > self.big_blind * 3:
                    self.player_ranges[player_index] = estimate_preflop_range(pos, Action.THREE_BET)
                else:
                    self.player_ranges[player_index] = estimate_preflop_range(pos, Action.RAISE)
        
        # After hero acts, simulate opponent actions
        if player_index == self.hero_index:
            self._simulate_opponents()
        
        return self.get_state()
    
    def _simulate_opponents(self):
        """Simulate opponent actions after hero acts"""
        import random
        
        # Get active opponents (not folded, not hero)
        for i in range(self.num_players):
            if i == self.hero_index or self.player_folded[i]:
                continue
            
            to_call = self.current_bet - self.player_bets[i]
            
            if to_call <= 0:
                # No bet to call - check or bet
                if random.random() < 0.2:  # 20% chance to bet
                    bet_size = random.choice([2, 3, 4]) * self.big_blind
                    bet_size = min(bet_size, self.player_stacks[i])
                    if bet_size > 0:
                        self._opponent_action(i, 'bet', bet_size)
                else:
                    self._opponent_action(i, 'check', 0)
            else:
                # Facing a bet - fold, call, or raise
                pot_odds = self.pot / to_call if to_call > 0 else 100
                
                # Simple decision logic based on pot odds
                rand = random.random()
                if pot_odds > 3:  # Good odds
                    if rand < 0.7:
                        self._opponent_action(i, 'call', 0)
                    elif rand < 0.85:
                        raise_to = self.current_bet * 2.5
                        raise_to = min(raise_to, self.player_stacks[i] + self.player_bets[i])
                        self._opponent_action(i, 'raise', raise_to)
                    else:
                        self._opponent_action(i, 'fold', 0)
                elif pot_odds > 1.5:  # Okay odds
                    if rand < 0.5:
                        self._opponent_action(i, 'call', 0)
                    elif rand < 0.65:
                        raise_to = self.current_bet * 2.5
                        raise_to = min(raise_to, self.player_stacks[i] + self.player_bets[i])
                        self._opponent_action(i, 'raise', raise_to)
                    else:
                        self._opponent_action(i, 'fold', 0)
                else:  # Bad odds
                    if rand < 0.3:
                        self._opponent_action(i, 'call', 0)
                    elif rand < 0.4:
                        raise_to = self.current_bet * 3
                        raise_to = min(raise_to, self.player_stacks[i] + self.player_bets[i])
                        self._opponent_action(i, 'raise', raise_to)
                    else:
                        self._opponent_action(i, 'fold', 0)
    
    def _opponent_action(self, player_index: int, action: str, amount: float):
        """Process an opponent's action (internal, no recursion)"""
        if self.player_folded[player_index]:
            return
        
        if action == 'fold':
            self.player_folded[player_index] = True
            self.action_history.append({
                'player': player_index,
                'action': 'fold',
                'street': self.street
            })
            if self.player_ranges[player_index]:
                pos = self.player_positions[player_index]
                self.player_ranges[player_index] = estimate_preflop_range(pos, Action.FOLD)
        
        elif action == 'check':
            self.action_history.append({
                'player': player_index,
                'action': 'check',
                'street': self.street
            })
        
        elif action == 'call':
            call_amount = min(self.current_bet - self.player_bets[player_index], 
                            self.player_stacks[player_index])
            self.player_stacks[player_index] -= call_amount
            self.player_bets[player_index] += call_amount
            self.pot += call_amount
            self.action_history.append({
                'player': player_index,
                'action': 'call',
                'amount': call_amount,
                'street': self.street
            })
            if self.player_ranges[player_index]:
                pos = self.player_positions[player_index]
                self.player_ranges[player_index] = estimate_preflop_range(pos, Action.CALL, Action.RAISE)
        
        elif action in ['bet', 'raise']:
            additional = amount - self.player_bets[player_index]
            if additional > self.player_stacks[player_index]:
                additional = self.player_stacks[player_index]
                amount = self.player_bets[player_index] + additional
            
            self.player_stacks[player_index] -= additional
            self.player_bets[player_index] = amount
            self.pot += additional
            self.current_bet = amount
            self.action_history.append({
                'player': player_index,
                'action': action,
                'amount': amount,
                'street': self.street
            })
            if self.player_ranges[player_index]:
                pos = self.player_positions[player_index]
                if self.current_bet > self.big_blind * 3:
                    self.player_ranges[player_index] = estimate_preflop_range(pos, Action.THREE_BET)
                else:
                    self.player_ranges[player_index] = estimate_preflop_range(pos, Action.RAISE)
    
    def _serialize_outs(self, outs_data: Dict) -> Dict:
        """Convert Card objects in outs data to strings for JSON"""
        serialized = {}
        for key, value in outs_data.items():
            if isinstance(value, list):
                # Convert Card objects to strings
                serialized[key] = [f"{c.rank}-{c.suit}" if hasattr(c, 'rank') else str(c) for c in value]
            else:
                serialized[key] = value
        return serialized
    
    def _serialize_draws(self, draws_data: Dict) -> Dict:
        """Convert Card objects in draws data to strings for JSON"""
        serialized = {}
        for key, value in draws_data.items():
            if isinstance(value, list):
                # Convert Card objects to strings
                serialized[key] = [f"{c.rank}-{c.suit}" if hasattr(c, 'rank') else str(c) for c in value]
            else:
                serialized[key] = value
        return serialized
    
    def get_state(self) -> Dict:
        """Get the current game state with all statistics"""
        
        # Return empty state if no hand has been started
        if not self.player_bets or not self.hole_cards:
            return {
                'hole_cards': [],
                'board': [],
                'pot': 0,
                'to_call': 0,
                'current_bet': 0,
                'street': 'preflop',
                'hero': {
                    'name': 'You',
                    'stack': 0,
                    'bet': 0,
                    'position': 'BTN',
                    'position_info': {}
                },
                'opponents': [],
                'statistics': {
                    'pot_odds': {'ratio': 0, 'percentage': 0, 'required_equity': 0, 'display': '-'},
                    'equity': {'equity': 0, 'win_percentage': 0, 'tie_percentage': 0},
                    'outs': {'total': 0},
                    'draws': {},
                    'decision': {'recommended_action': '-', 'expected_value': 0, 'reasoning': 'Start a new hand'},
                    'hand_classification': {}
                },
                'active_players': 0,
                'is_preflop_aggressor': False,
                'action_history': []
            }
        
        # Format cards for JSON
        hole_card_strs = [f"{c.rank}-{c.suit}" for c in self.hole_cards]
        board_strs = [f"{c.rank}-{c.suit}" for c in self.board]
        
        # Calculate to_call amount for hero
        to_call = max(0, self.current_bet - self.player_bets[self.hero_index])
        hero_stack = self.player_stacks[self.hero_index]
        
        # Calculate pot odds
        pot_odds = calculate_pot_odds(self.pot, to_call)
        
        # Count active opponents
        active_opponents = sum(1 for i, f in enumerate(self.player_folded) 
                              if not f and i != self.hero_index)
        
        # Calculate equity using Monte Carlo
        equity_data = {'equity': 0, 'win_percentage': 0, 'tie_percentage': 0}
        outs_data = {'total': 0}
        draws_data = {}
        
        if self.hole_cards:
            if active_opponents > 0:
                equity_data = calculate_equity_monte_carlo(
                    self.hole_cards, self.board, active_opponents,
                    num_simulations=5000
                )
            else:
                equity_data = {'equity': 100, 'win_percentage': 100, 'tie_percentage': 0}
            
            # Count outs and detect draws
            if self.board:
                # Count outs using only information available to the player
                # (hole cards + board - we don't know opponent cards)
                outs_data = count_outs(self.hole_cards, self.board)
                draws_data = detect_draws(self.hole_cards, self.board)
                
                # Convert Card objects to strings for JSON serialization
                outs_data = self._serialize_outs(outs_data)
                draws_data = self._serialize_draws(draws_data)
        
        # Analyze decision
        decision = analyze_decision(
            self.pot, to_call, equity_data['equity'], hero_stack
        )
        
        # Classify preflop hand
        hand_class = {}
        if self.hole_cards:
            hand_class = classify_preflop_hand(self.hole_cards)
        
        # Get hero position info
        hero_position = self.player_positions[self.hero_index] if self.player_positions else Position.BTN
        position_info = get_position_info(hero_position)
        
        # Compile opponent information
        opponents = []
        for i in range(self.num_players):
            if i != self.hero_index:
                opp = {
                    'name': self.players[i],
                    'stack': self.player_stacks[i],
                    'bet': self.player_bets[i],
                    'folded': self.player_folded[i],
                    'position': self.player_positions[i].name if self.player_positions else 'Unknown',
                    'range': self.player_ranges[i] if self.player_ranges else None
                }
                
                # Convert range set to list for JSON
                if opp['range'] and 'range' in opp['range']:
                    opp['range']['range'] = list(opp['range']['range'])
                
                opponents.append(opp)
        
        return {
            'hole_cards': hole_card_strs,
            'board': board_strs,
            'pot': self.pot,
            'to_call': to_call,
            'current_bet': self.current_bet,
            'street': self.street,
            'hero': {
                'name': 'You',
                'stack': hero_stack,
                'bet': self.player_bets[self.hero_index],
                'position': hero_position.name,
                'position_info': position_info
            },
            'opponents': opponents,
            'statistics': {
                'pot_odds': pot_odds,
                'equity': equity_data,
                'outs': outs_data,
                'draws': draws_data,
                'decision': decision,
                'hand_classification': hand_class
            },
            'active_players': self.num_players - sum(self.player_folded),
            'is_preflop_aggressor': self.is_preflop_aggressor,
            'action_history': self.action_history
        }


# Global game manager instance
game = GameManager()


# ============================================================
# API ROUTES
# ============================================================

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/new-hand', methods=['POST'])
def new_hand():
    """Start a new hand"""
    data = request.get_json() or {}
    
    num_players = data.get('num_players', 6)
    hero_position = data.get('hero_position', 0)
    starting_stack = data.get('starting_stack', 1000)
    big_blind = data.get('big_blind', 10)
    
    state = game.setup_hand(num_players, hero_position, starting_stack, big_blind)
    return jsonify(state)


@app.route('/api/deal/<street>', methods=['POST'])
def deal_street(street):
    """Deal the next street"""
    if street == 'flop':
        state = game.deal_flop()
    elif street == 'turn':
        state = game.deal_turn()
    elif street == 'river':
        state = game.deal_river()
    else:
        return jsonify({'error': 'Invalid street'}), 400
    
    if state is None:
        return jsonify({'error': 'Cannot deal that street yet'}), 400
    
    return jsonify(state)


@app.route('/api/action', methods=['POST'])
def process_action():
    """Process a player action"""
    data = request.get_json()
    
    # Always use hero_index for player actions from the frontend
    player_index = game.hero_index
    action = data.get('action', 'check')
    amount = data.get('amount', 0)
    
    # Check if hero has already folded
    if game.player_folded and game.player_folded[player_index]:
        return jsonify({'error': 'You have already folded this hand'}), 400
    
    state = game.process_action(player_index, action, amount)
    
    if state is None:
        return jsonify({'error': 'Invalid action'}), 400
    
    return jsonify(state)


@app.route('/api/ai-advice', methods=['POST'])
def get_ai_advice():
    """Get AI coaching advice for the current situation"""
    data = request.get_json() or {}
    
    state = game.get_state()
    
    # Create GameState object for AI coach
    game_state = create_game_state(
        hole_cards=state['hole_cards'],
        board=state['board'],
        pot_size=state['pot'],
        to_call=state['to_call'],
        stack_size=state['hero']['stack'],
        position=state['hero']['position'],
        street=state['street'],
        num_opponents=len([o for o in state['opponents'] if not o['folded']]),
        pot_odds=state['statistics']['pot_odds'],
        equity=state['statistics']['equity']['equity'],
        outs=state['statistics']['outs']['total'],
        draws=state['statistics']['draws'],
        opponent_ranges=[o['range'] for o in state['opponents']],
        is_preflop_aggressor=state['is_preflop_aggressor'],
        previous_actions=[a['action'] for a in state['action_history']]
    )
    
    advice = ai_coach.get_strategic_advice(game_state)
    return jsonify(advice)


@app.route('/api/explain/<concept>', methods=['GET'])
def explain_concept(concept):
    """Explain a poker concept"""
    explanation = ai_coach.explain_concept(concept)
    return jsonify({'concept': concept, 'explanation': explanation})


@app.route('/api/calculate-equity', methods=['POST'])
def calculate_equity():
    """Calculate equity for specific cards"""
    data = request.get_json()
    
    hole_cards_str = data.get('hole_cards', [])
    board_str = data.get('board', [])
    num_opponents = data.get('num_opponents', 1)
    
    try:
        hole_cards = cards_from_strings(hole_cards_str)
        board = cards_from_strings(board_str)
        
        equity_data = calculate_equity_monte_carlo(
            hole_cards, board, num_opponents, num_simulations=10000
        )
        
        # Also get multiway analysis
        multiway_data = analyze_multiway_vs_headsup(hole_cards, board)
        
        return jsonify({
            'equity': equity_data,
            'multiway_analysis': multiway_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/estimate-range', methods=['POST'])
def estimate_range():
    """Estimate opponent range"""
    data = request.get_json()
    
    position = data.get('position', 'BTN')
    action = data.get('action', 'raise')
    facing = data.get('facing_action')
    
    try:
        pos = Position[position.upper()]
        act = Action[action.upper()]
        facing_act = Action[facing.upper()] if facing else None
        
        range_data = estimate_preflop_range(pos, act, facing_act)
        
        # Convert set to list and add grid visualization
        range_data['range'] = list(range_data['range'])
        range_data['summary'] = get_range_summary(set(range_data['range']))
        
        return jsonify(range_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current game state"""
    return jsonify(game.get_state())


if __name__ == '__main__':
    # Using port 5001 to avoid conflict with macOS AirPlay Receiver on port 5000
    app.run(debug=True, host='0.0.0.0', port=5001)

