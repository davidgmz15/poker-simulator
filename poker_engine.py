"""
Poker Engine - Core calculations for pot odds, equity, and hand evaluation
"""
import random
from itertools import combinations
from collections import Counter
from enum import Enum
from typing import List, Tuple, Optional, Dict, Set

# Card constants
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
SUITS = ['H', 'D', 'C', 'S']
RANK_VALUES = {r: i for i, r in enumerate(RANKS)}

class HandRank(Enum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.value = RANK_VALUES[rank]
    
    def __repr__(self):
        return f"{self.rank}-{self.suit}"
    
    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit
    
    def __hash__(self):
        return hash((self.rank, self.suit))
    
    @classmethod
    def from_string(cls, s: str) -> 'Card':
        """Parse card from string like 'A-H' or '10-S'"""
        parts = s.split('-')
        return cls(parts[0], parts[1])


def create_deck() -> List[Card]:
    """Create a standard 52-card deck"""
    return [Card(r, s) for r in RANKS for s in SUITS]


def evaluate_hand(cards: List[Card]) -> Tuple[HandRank, List[int]]:
    """
    Evaluate the best 5-card hand from the given cards.
    Returns (HandRank, tiebreaker_values) where tiebreaker_values
    are used to compare hands of the same rank.
    """
    if len(cards) < 5:
        return (HandRank.HIGH_CARD, [0])
    
    best_hand = None
    best_tiebreaker = None
    
    for combo in combinations(cards, 5):
        hand_rank, tiebreaker = _evaluate_five_cards(list(combo))
        if best_hand is None or (hand_rank.value, tiebreaker) > (best_hand.value, best_tiebreaker):
            best_hand = hand_rank
            best_tiebreaker = tiebreaker
    
    return (best_hand, best_tiebreaker)


def _evaluate_five_cards(cards: List[Card]) -> Tuple[HandRank, List[int]]:
    """Evaluate exactly 5 cards"""
    values = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    
    is_flush = len(set(suits)) == 1
    
    # Check for straight (including wheel: A-2-3-4-5)
    is_straight = False
    straight_high = 0
    
    unique_values = sorted(set(values), reverse=True)
    if len(unique_values) == 5:
        if unique_values[0] - unique_values[4] == 4:
            is_straight = True
            straight_high = unique_values[0]
        # Check for wheel (A-2-3-4-5)
        elif unique_values == [12, 3, 2, 1, 0]:  # A, 5, 4, 3, 2
            is_straight = True
            straight_high = 3  # 5-high straight
    
    # Count ranks
    rank_counts = Counter(values)
    counts = sorted(rank_counts.values(), reverse=True)
    
    # Get values sorted by count then by value
    sorted_by_count = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    kickers = [v for v, c in sorted_by_count]
    
    # Determine hand rank
    if is_straight and is_flush:
        if straight_high == 12:  # Royal Flush
            return (HandRank.ROYAL_FLUSH, [straight_high])
        return (HandRank.STRAIGHT_FLUSH, [straight_high])
    
    if counts == [4, 1]:
        return (HandRank.FOUR_OF_A_KIND, kickers)
    
    if counts == [3, 2]:
        return (HandRank.FULL_HOUSE, kickers)
    
    if is_flush:
        return (HandRank.FLUSH, values)
    
    if is_straight:
        return (HandRank.STRAIGHT, [straight_high])
    
    if counts == [3, 1, 1]:
        return (HandRank.THREE_OF_A_KIND, kickers)
    
    if counts == [2, 2, 1]:
        return (HandRank.TWO_PAIR, kickers)
    
    if counts == [2, 1, 1, 1]:
        return (HandRank.PAIR, kickers)
    
    return (HandRank.HIGH_CARD, values)


def compare_hands(hand1: Tuple[HandRank, List[int]], hand2: Tuple[HandRank, List[int]]) -> int:
    """
    Compare two evaluated hands.
    Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie
    """
    if hand1[0].value > hand2[0].value:
        return 1
    elif hand1[0].value < hand2[0].value:
        return -1
    else:
        # Same rank, compare tiebreakers
        for v1, v2 in zip(hand1[1], hand2[1]):
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0


# ============================================================
# POT ODDS CALCULATION
# ============================================================

def calculate_pot_odds(pot_size: float, call_amount: float) -> Dict:
    """
    Calculate pot odds for a given situation.
    
    Returns dict with:
    - ratio: pot odds as X:1 (e.g., 5.0 means 5:1)
    - percentage: pot odds as percentage
    - required_equity: minimum equity needed to break even
    """
    if call_amount <= 0:
        return {
            'ratio': 0,  # No call needed
            'percentage': 0,
            'required_equity': 0,
            'display': 'Free check'
        }
    
    ratio = pot_size / call_amount
    percentage = (call_amount / (pot_size + call_amount)) * 100
    required_equity = percentage
    
    return {
        'ratio': round(ratio, 2),
        'percentage': round(percentage, 1),
        'required_equity': round(required_equity, 1),
        'display': f"{ratio:.1f}:1"
    }


# ============================================================
# EQUITY CALCULATION
# ============================================================

def count_outs(hole_cards: List[Card], board: List[Card]) -> Dict:
    """
    Count outs - cards that would improve the hand.
    
    NOTE: This calculation only uses information available to the player:
    - Their hole cards
    - The community board
    
    We assume all unseen cards (52 - hole cards - board) could potentially
    come on future streets. This is how a real player would calculate outs
    since they don't know what opponents hold or what's been mucked.
    
    Returns detailed breakdown of outs.
    """
    current_eval = evaluate_hand(hole_cards + board)
    current_rank = current_eval[0]
    
    outs = {
        'total': 0,
        'to_straight': [],
        'to_flush': [],
        'to_pair': [],
        'to_two_pair': [],
        'to_trips': [],
        'to_full_house': [],
        'to_quads': [],
        'overcards': []
    }
    
    # Only use cards we KNOW about - our hole cards and the board
    known_cards = set(hole_cards + board)
    
    # All other cards in the deck are potential outs
    # (we don't know what opponents have or what's been mucked)
    full_deck = create_deck()
    unknown_cards = [c for c in full_deck if c not in known_cards]
    
    for card in unknown_cards:
        new_hand = hole_cards + board + [card]
        new_eval = evaluate_hand(new_hand)
        
        if new_eval[0].value > current_rank.value or \
           (new_eval[0].value == current_rank.value and new_eval[1] > current_eval[1]):
            outs['total'] += 1
            
            # Categorize the out
            if new_eval[0] == HandRank.STRAIGHT or new_eval[0] == HandRank.STRAIGHT_FLUSH:
                if current_rank != HandRank.STRAIGHT:
                    outs['to_straight'].append(card)
            elif new_eval[0] == HandRank.FLUSH:
                if current_rank != HandRank.FLUSH:
                    outs['to_flush'].append(card)
            elif new_eval[0] == HandRank.FOUR_OF_A_KIND:
                outs['to_quads'].append(card)
            elif new_eval[0] == HandRank.FULL_HOUSE:
                if current_rank.value < HandRank.FULL_HOUSE.value:
                    outs['to_full_house'].append(card)
            elif new_eval[0] == HandRank.THREE_OF_A_KIND:
                outs['to_trips'].append(card)
            elif new_eval[0] == HandRank.TWO_PAIR:
                if current_rank.value < HandRank.TWO_PAIR.value:
                    outs['to_two_pair'].append(card)
            elif new_eval[0] == HandRank.PAIR:
                outs['to_pair'].append(card)
    
    return outs


def calculate_equity_monte_carlo(
    hole_cards: List[Card],
    board: List[Card],
    num_opponents: int,
    num_simulations: int = 10000,
    opponent_ranges: Optional[List[List[Tuple[Card, Card]]]] = None
) -> Dict:
    """
    Calculate equity using Monte Carlo simulation.
    
    This runs many random simulations to estimate win/tie percentages.
    More accurate than rule-of-4-and-2 for complex situations.
    """
    deck = create_deck()
    known_cards = set(hole_cards + board)
    remaining_deck = [c for c in deck if c not in known_cards]
    
    wins = 0
    ties = 0
    total = 0
    
    cards_to_deal = 5 - len(board)
    
    for _ in range(num_simulations):
        random.shuffle(remaining_deck)
        
        # Complete the board
        sim_board = board + remaining_deck[:cards_to_deal]
        deck_after_board = remaining_deck[cards_to_deal:]
        
        # Deal opponent hands
        opponent_hands = []
        idx = 0
        for i in range(num_opponents):
            if opponent_ranges and i < len(opponent_ranges) and opponent_ranges[i]:
                # Use specified range
                opp_hand = random.choice(opponent_ranges[i])
                opponent_hands.append(list(opp_hand))
            else:
                # Random hand from remaining deck
                opponent_hands.append([deck_after_board[idx], deck_after_board[idx + 1]])
                idx += 2
        
        # Evaluate all hands
        hero_eval = evaluate_hand(hole_cards + sim_board)
        hero_wins = True
        hero_ties = False
        
        for opp_hand in opponent_hands:
            opp_eval = evaluate_hand(opp_hand + sim_board)
            result = compare_hands(hero_eval, opp_eval)
            
            if result < 0:
                hero_wins = False
                break
            elif result == 0:
                hero_ties = True
        
        if hero_wins and not hero_ties:
            wins += 1
        elif hero_wins and hero_ties:
            ties += 1
        
        total += 1
    
    win_pct = (wins / total) * 100
    tie_pct = (ties / total) * 100
    equity = win_pct + (tie_pct / 2)  # Ties split the pot
    
    return {
        'equity': round(equity, 1),
        'win_percentage': round(win_pct, 1),
        'tie_percentage': round(tie_pct, 1),
        'simulations': total
    }


def calculate_equity_rule_of_4_and_2(outs: int, street: str) -> Dict:
    """
    Quick equity estimation using the Rule of 4 and 2.
    
    - On the flop (2 cards to come): multiply outs by 4
    - On the turn (1 card to come): multiply outs by 2
    
    This is less accurate but much faster than Monte Carlo.
    """
    if street == 'flop':
        multiplier = 4
        equity = min(outs * multiplier, 100)
        cards_to_come = 2
    elif street == 'turn':
        multiplier = 2
        equity = min(outs * multiplier, 100)
        cards_to_come = 1
    else:
        equity = 0
        multiplier = 0
        cards_to_come = 0
    
    return {
        'equity': equity,
        'outs': outs,
        'multiplier': multiplier,
        'cards_to_come': cards_to_come,
        'method': 'Rule of 4 and 2'
    }


def analyze_multiway_vs_headsup(hole_cards: List[Card], board: List[Card]) -> Dict:
    """
    Analyze how a hand's equity changes with number of opponents.
    Some hands play better multiway, others heads-up.
    """
    results = {}
    
    for num_opps in [1, 2, 3, 5, 8]:
        equity_data = calculate_equity_monte_carlo(
            hole_cards, board, num_opps, num_simulations=5000
        )
        results[num_opps] = equity_data['equity']
    
    # Determine hand type preference
    headsup_equity = results[1]
    multiway_equity = results[5]
    
    if headsup_equity > multiway_equity * 1.3:
        preference = "Plays better heads-up"
        reason = "High card strength dominates with fewer opponents"
    elif multiway_equity > headsup_equity * 0.8:
        preference = "Plays well multiway"
        reason = "Drawing hands and suited connectors thrive multiway"
    else:
        preference = "Neutral"
        reason = "Performs similarly regardless of opponents"
    
    return {
        'equity_by_opponents': results,
        'preference': preference,
        'reason': reason
    }


# ============================================================
# DECISION ANALYSIS - COMBINING POT ODDS AND EQUITY
# ============================================================

def analyze_decision(
    pot_size: float,
    call_amount: float,
    equity: float,
    stack_size: float
) -> Dict:
    """
    Analyze whether a call is +EV (profitable long-term).
    
    A call is profitable when: equity > required_equity (from pot odds)
    """
    pot_odds = calculate_pot_odds(pot_size, call_amount)
    required_equity = pot_odds['required_equity']
    
    # Calculate expected value
    pot_after_call = pot_size + call_amount
    ev = (equity / 100) * pot_after_call - (1 - equity / 100) * call_amount
    
    # Calculate pot odds in percentage terms for comparison
    is_profitable = equity > required_equity
    
    # Determine recommended action
    if call_amount == 0:
        action = "CHECK"
        reasoning = "Free to see the next card"
    elif is_profitable:
        equity_advantage = equity - required_equity
        if equity_advantage > 20:
            action = "RAISE"
            reasoning = f"Strong +EV spot! Equity ({equity:.1f}%) far exceeds required ({required_equity:.1f}%)"
        elif equity_advantage > 10:
            action = "CALL"
            reasoning = f"Profitable call. Equity ({equity:.1f}%) comfortably beats required ({required_equity:.1f}%)"
        else:
            action = "CALL (marginal)"
            reasoning = f"Slightly +EV. Equity ({equity:.1f}%) just above required ({required_equity:.1f}%)"
    else:
        equity_deficit = required_equity - equity
        if equity_deficit > 15:
            action = "FOLD"
            reasoning = f"Clear fold. Equity ({equity:.1f}%) well below required ({required_equity:.1f}%)"
        else:
            action = "FOLD (close)"
            reasoning = f"Marginal fold. Equity ({equity:.1f}%) slightly below required ({required_equity:.1f}%)"
    
    # Consider implied odds
    implied_odds_factor = stack_size / pot_size if pot_size > 0 else 0
    implied_odds_note = ""
    if implied_odds_factor > 5 and not is_profitable:
        implied_odds_note = "However, deep stacks suggest good implied odds if you hit."
    
    return {
        'pot_odds': pot_odds,
        'equity': equity,
        'required_equity': required_equity,
        'is_profitable': is_profitable,
        'expected_value': round(ev, 2),
        'recommended_action': action,
        'reasoning': reasoning,
        'implied_odds_note': implied_odds_note
    }


# ============================================================
# DRAW DETECTION
# ============================================================

def detect_draws(hole_cards: List[Card], board: List[Card]) -> Dict:
    """
    Detect various draws (flush draws, straight draws, etc.)
    """
    all_cards = hole_cards + board
    values = sorted([c.value for c in all_cards])
    suits = [c.suit for c in all_cards]
    
    draws = {
        'flush_draw': False,
        'flush_draw_suit': None,
        'flush_draw_outs': 0,
        'open_ended_straight_draw': False,
        'gutshot_straight_draw': False,
        'straight_outs': 0,
        'overcards': [],
        'overcard_outs': 0
    }
    
    # Flush draw detection
    suit_counts = Counter(suits)
    for suit, count in suit_counts.items():
        if count == 4:
            draws['flush_draw'] = True
            draws['flush_draw_suit'] = suit
            draws['flush_draw_outs'] = 9  # 13 - 4 = 9 remaining of that suit
    
    # Straight draw detection
    unique_values = sorted(set(values))
    
    # Check for open-ended straight draw (4 consecutive cards)
    for i in range(len(unique_values) - 3):
        if unique_values[i+3] - unique_values[i] == 3:
            # Check if both ends are open
            low_open = unique_values[i] > 0  # Not at bottom
            high_open = unique_values[i+3] < 12  # Not at top (A)
            if low_open and high_open:
                draws['open_ended_straight_draw'] = True
                draws['straight_outs'] = 8
                break
    
    # Check for gutshot (4 cards with one gap)
    if not draws['open_ended_straight_draw']:
        for i in range(len(unique_values) - 3):
            window = unique_values[i:i+4]
            if max(window) - min(window) == 4:  # One gap in 5-card window
                draws['gutshot_straight_draw'] = True
                draws['straight_outs'] = 4
                break
    
    # Overcards (cards higher than board)
    if board:
        board_max = max(c.value for c in board)
        for card in hole_cards:
            if card.value > board_max:
                draws['overcards'].append(card)
        draws['overcard_outs'] = len(draws['overcards']) * 3  # ~3 outs per overcard
    
    # Total drawing outs (accounting for overlap)
    total_outs = draws['flush_draw_outs'] + draws['straight_outs'] + draws['overcard_outs']
    # Subtract overlap if both flush and straight draw
    if draws['flush_draw'] and (draws['open_ended_straight_draw'] or draws['gutshot_straight_draw']):
        total_outs -= 2  # Approximate overlap
    
    draws['total_drawing_outs'] = total_outs
    
    return draws


# ============================================================
# HAND STRENGTH CLASSIFICATION
# ============================================================

def classify_preflop_hand(hole_cards: List[Card]) -> Dict:
    """
    Classify a preflop hand by strength and playability.
    """
    c1, c2 = hole_cards
    
    is_pair = c1.rank == c2.rank
    is_suited = c1.suit == c2.suit
    high_card = max(c1.value, c2.value)
    low_card = min(c1.value, c2.value)
    gap = high_card - low_card
    
    # Hand notation (e.g., "AKs", "QQ", "T9o")
    rank_chars = {10: 'T', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
    r1 = rank_chars.get(c1.value + 2, str(c1.value + 2)) if c1.value >= 8 else RANKS[c1.value]
    r2 = rank_chars.get(c2.value + 2, str(c2.value + 2)) if c2.value >= 8 else RANKS[c2.value]
    
    if is_pair:
        notation = f"{r1}{r2}"
    else:
        suffix = 's' if is_suited else 'o'
        if c1.value > c2.value:
            notation = f"{r1}{r2}{suffix}"
        else:
            notation = f"{r2}{r1}{suffix}"
    
    # Classify strength tier
    if is_pair and high_card >= 10:  # JJ+
        tier = "Premium"
        strength = "Very Strong"
    elif high_card == 12 and low_card == 11:  # AK
        tier = "Premium"
        strength = "Very Strong"
    elif is_pair and high_card >= 7:  # 77-TT
        tier = "Strong"
        strength = "Strong"
    elif high_card >= 11 and low_card >= 9 and is_suited:  # Suited broadways
        tier = "Strong"
        strength = "Strong"
    elif is_pair:  # Small pairs
        tier = "Speculative"
        strength = "Medium"
    elif is_suited and gap <= 2 and high_card >= 6:  # Suited connectors
        tier = "Speculative"
        strength = "Medium (drawing hand)"
    elif high_card == 12:  # Ax
        tier = "Playable"
        strength = "Medium"
    else:
        tier = "Weak"
        strength = "Weak"
    
    # Multiway preference
    if is_pair and high_card <= 8:
        multiway_pref = "Prefers multiway (set mining)"
    elif is_suited and gap <= 3:
        multiway_pref = "Prefers multiway (drawing potential)"
    elif high_card >= 11 and low_card >= 9:
        multiway_pref = "Prefers heads-up (high card value)"
    else:
        multiway_pref = "Neutral"
    
    return {
        'notation': notation,
        'is_pair': is_pair,
        'is_suited': is_suited,
        'tier': tier,
        'strength': strength,
        'multiway_preference': multiway_pref
    }


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def cards_from_strings(card_strings: List[str]) -> List[Card]:
    """Convert list of card strings to Card objects"""
    return [Card.from_string(s) for s in card_strings]


def get_remaining_deck(hole_cards: List[Card], board: List[Card]) -> List[Card]:
    """Get remaining cards in deck"""
    known = set(hole_cards + board)
    return [c for c in create_deck() if c not in known]

