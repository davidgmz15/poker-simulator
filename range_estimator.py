"""
Range Estimator - Estimate opponent hand ranges based on position and actions
"""
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
from poker_engine import Card, RANKS, SUITS, create_deck


class Position(Enum):
    UTG = 0        # Under the Gun (first to act)
    UTG1 = 1       # UTG+1
    MP = 2         # Middle Position
    MP1 = 3        # Middle Position +1
    CO = 4         # Cutoff
    BTN = 5        # Button (dealer)
    SB = 6         # Small Blind
    BB = 7         # Big Blind


class Action(Enum):
    FOLD = 0
    LIMP = 1       # Call the big blind preflop
    CALL = 2       # Call a raise
    RAISE = 3      # Standard raise (2-3x)
    THREE_BET = 4  # Re-raise
    FOUR_BET = 5   # Re-re-raise
    ALL_IN = 6     # Shove
    CHECK = 7      # Check
    BET = 8        # Initial bet


# ============================================================
# PREFLOP RANGES BY POSITION
# ============================================================

# These ranges are approximations based on standard tight-aggressive play
# Format: set of hand notations like "AA", "AKs", "T9o"

PREFLOP_RANGES = {
    # UTG - Tightest position, only premium hands
    Position.UTG: {
        'open_raise': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88',
            'AKs', 'AQs', 'AJs', 'ATs', 'KQs',
            'AKo', 'AQo'
        },
        'three_bet': {
            'AA', 'KK', 'QQ', 'AKs', 'AKo'
        },
        'limp': set()  # Never limp from UTG
    },
    
    # Middle Position - Slightly wider
    Position.MP: {
        'open_raise': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77',
            'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'KQs', 'KJs', 'QJs', 'JTs',
            'AKo', 'AQo', 'AJo', 'KQo'
        },
        'three_bet': {
            'AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo', 'AQs'
        },
        'limp': set()
    },
    
    # Cutoff - Wide opening range
    Position.CO: {
        'open_raise': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55',
            'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'Q9s', 'JTs', 'J9s', 'T9s', '98s', '87s', '76s',
            'AKo', 'AQo', 'AJo', 'ATo', 'KQo', 'KJo', 'QJo', 'JTo'
        },
        'three_bet': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AQs', 'AJs', 'AKo', 'AQo',
            # Some bluffs
            'A5s', 'A4s', '76s', '65s'
        },
        'limp': set()
    },
    
    # Button - Widest stealing range
    Position.BTN: {
        'open_raise': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
            'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s',
            'QJs', 'QTs', 'Q9s', 'Q8s', 'JTs', 'J9s', 'J8s', 'T9s', 'T8s', '98s', '97s', '87s', '86s', '76s', '75s', '65s', '64s', '54s',
            'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o',
            'KQo', 'KJo', 'KTo', 'QJo', 'QTo', 'JTo', 'J9o', 'T9o', '98o'
        },
        'three_bet': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', 'AKs', 'AQs', 'AJs', 'ATs', 'AKo', 'AQo', 'AJo',
            # Bluffs
            'A5s', 'A4s', 'A3s', '76s', '65s', '54s', 'K9s'
        },
        'limp': set()  # Button should never limp
    },
    
    # Small Blind
    Position.SB: {
        'open_raise': {  # If folded to SB
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44',
            'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'JTs', 'T9s', '98s', '87s', '76s',
            'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'KQo', 'KJo', 'QJo'
        },
        'three_bet': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AQs', 'AKo',
            # Polarized 3-bets
            '99', '88', 'AJs', 'A5s', 'A4s'
        },
        'limp': {
            '22', '33', '44', '55', '66', '77',
            '54s', '65s', '76s', '87s', '98s', 'T9s', 'J9s',
            'A2s', 'A3s', 'A4s', 'A5s'
        }
    },
    
    # Big Blind
    Position.BB: {
        'open_raise': set(),  # BB doesn't open raise
        'three_bet': {
            'AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AQs', 'AJs', 'AKo', 'AQo',
            # Defend with 3-bets
            '99', '88', 'ATs', 'KQs', 'A5s', 'A4s'
        },
        'call': {  # Defending range vs steal
            'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
            'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
            'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s',
            'QJs', 'QTs', 'Q9s', 'Q8s', 'JTs', 'J9s', 'J8s', 'T9s', 'T8s', '98s', '97s', '87s', '86s', '76s', '75s', '65s', '64s', '54s', '53s', '43s',
            'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'KQo', 'KJo', 'KTo', 'QJo', 'QTo', 'JTo', 'T9o', '98o', '87o'
        },
        'limp': set()
    }
}

# Add UTG1 and MP1 as aliases
PREFLOP_RANGES[Position.UTG1] = PREFLOP_RANGES[Position.UTG]
PREFLOP_RANGES[Position.MP1] = PREFLOP_RANGES[Position.MP]


# ============================================================
# BET SIZING ANALYSIS
# ============================================================

def analyze_bet_sizing(bet_size: float, pot_size: float) -> Dict:
    """
    Analyze what a bet size tells us about the opponent's hand.
    """
    if pot_size <= 0:
        return {'analysis': 'No pot yet'}
    
    bet_ratio = bet_size / pot_size
    
    if bet_ratio < 0.33:
        return {
            'sizing': 'Small (< 1/3 pot)',
            'typical_range': 'Wide range - blocking bet, thin value, or weak draw',
            'polarization': 'Merged (mixture of value and bluffs)',
            'strength_indicator': 'Usually weak to medium'
        }
    elif bet_ratio < 0.5:
        return {
            'sizing': 'Small-Medium (1/3 - 1/2 pot)',
            'typical_range': 'Moderate strength or drawing hands',
            'polarization': 'Slightly merged',
            'strength_indicator': 'Medium'
        }
    elif bet_ratio < 0.75:
        return {
            'sizing': 'Medium (1/2 - 3/4 pot)',
            'typical_range': 'Standard value bet or semi-bluff',
            'polarization': 'Balanced',
            'strength_indicator': 'Medium to strong'
        }
    elif bet_ratio <= 1.0:
        return {
            'sizing': 'Large (3/4 - pot)',
            'typical_range': 'Strong value or big draw',
            'polarization': 'Starting to polarize',
            'strength_indicator': 'Strong'
        }
    elif bet_ratio <= 1.5:
        return {
            'sizing': 'Overbet (pot - 1.5x pot)',
            'typical_range': 'Very strong or bluff',
            'polarization': 'Polarized',
            'strength_indicator': 'Very strong or air'
        }
    else:
        return {
            'sizing': 'Massive overbet (> 1.5x pot)',
            'typical_range': 'Nuts or complete bluff',
            'polarization': 'Extremely polarized',
            'strength_indicator': 'Nuts or nothing'
        }


# ============================================================
# RANGE ESTIMATION
# ============================================================

def hand_to_notation(hole_cards: List[Card]) -> str:
    """Convert hole cards to standard notation (e.g., AKs, QJo, TT)"""
    c1, c2 = hole_cards
    
    # Rank characters
    rank_map = {'10': 'T', '11': 'J', '12': 'Q', '13': 'K', '14': 'A'}
    
    def get_rank_char(card):
        val = card.value
        if val >= 8:  # T or higher
            return rank_map.get(str(val + 2), RANKS[val])
        return RANKS[val]
    
    r1 = get_rank_char(c1)
    r2 = get_rank_char(c2)
    
    is_pair = c1.rank == c2.rank
    is_suited = c1.suit == c2.suit
    
    if is_pair:
        return f"{r1}{r2}"
    
    # Put higher card first
    if c1.value > c2.value:
        notation = f"{r1}{r2}"
    else:
        notation = f"{r2}{r1}"
    
    return notation + ('s' if is_suited else 'o')


def estimate_preflop_range(
    position: Position,
    action: Action,
    facing_action: Optional[Action] = None
) -> Dict:
    """
    Estimate a player's range based on position and action.
    """
    pos_ranges = PREFLOP_RANGES.get(position, PREFLOP_RANGES[Position.MP])
    
    if action == Action.FOLD:
        return {
            'range': set(),
            'description': 'Player folded',
            'hand_count': 0,
            'percentage': 0
        }
    
    if action == Action.RAISE or action == Action.BET:
        if facing_action in [Action.RAISE, Action.THREE_BET]:
            range_set = pos_ranges.get('three_bet', set())
            desc = f"3-bet range from {position.name}"
        else:
            range_set = pos_ranges.get('open_raise', set())
            desc = f"Open raise range from {position.name}"
    
    elif action == Action.THREE_BET:
        range_set = pos_ranges.get('three_bet', set())
        desc = f"3-bet range from {position.name}"
    
    elif action == Action.FOUR_BET:
        # Very narrow 4-bet range
        range_set = {'AA', 'KK', 'QQ', 'AKs', 'AKo'}
        desc = f"4-bet range (very narrow)"
    
    elif action == Action.ALL_IN:
        # Depends on stack depth, but generally strong
        range_set = {'AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo', 'AQs'}
        desc = "All-in range (typically premium)"
    
    elif action == Action.CALL:
        if facing_action == Action.RAISE:
            range_set = pos_ranges.get('call', pos_ranges.get('open_raise', set()))
            desc = f"Calling range from {position.name}"
        else:
            range_set = pos_ranges.get('open_raise', set())
            desc = f"Calling range from {position.name}"
    
    elif action == Action.LIMP:
        range_set = pos_ranges.get('limp', set())
        if not range_set:
            # Limping usually weak players with speculative hands
            range_set = {
                '22', '33', '44', '55', '66', '77', '88',
                '54s', '65s', '76s', '87s', '98s', 'T9s',
                'A2s', 'A3s', 'A4s', 'A5s', 'K9s', 'Q9s', 'J9s',
                'A9o', 'KTo', 'QTo', 'JTo'
            }
        desc = f"Limp range from {position.name} (passive/weak)"
    
    else:
        range_set = pos_ranges.get('open_raise', set())
        desc = f"Estimated range from {position.name}"
    
    # Calculate percentage of all hands
    # Total combos: 1326 (52 choose 2)
    # Pairs: 6 combos each, suited: 4 combos each, offsuit: 12 combos each
    total_combos = 0
    for hand in range_set:
        if len(hand) == 2:  # Pair
            total_combos += 6
        elif hand.endswith('s'):
            total_combos += 4
        else:  # offsuit
            total_combos += 12
    
    percentage = (total_combos / 1326) * 100
    
    return {
        'range': range_set,
        'description': desc,
        'hand_count': len(range_set),
        'combo_count': total_combos,
        'percentage': round(percentage, 1)
    }


def narrow_range_postflop(
    preflop_range: Set[str],
    board: List[Card],
    action: Action,
    bet_size: float = 0,
    pot_size: float = 0
) -> Dict:
    """
    Narrow a player's range based on postflop action.
    This is a simplified model - real range analysis is more complex.
    """
    board_values = [c.value for c in board]
    board_suits = [c.suit for c in board]
    
    # Check for board texture
    is_monotone = len(set(board_suits)) == 1
    is_two_tone = len(set(board_suits)) == 2
    is_paired = len(set(board_values)) < len(board_values)
    high_card = max(board_values) if board_values else 0
    is_connected = max(board_values) - min(board_values) <= 4 if len(board_values) >= 3 else False
    
    # Get bet sizing analysis
    sizing = analyze_bet_sizing(bet_size, pot_size) if bet_size > 0 and pot_size > 0 else None
    
    narrowed_range = set()
    removed_hands = set()
    
    for hand in preflop_range:
        # Parse hand notation
        is_pair = len(hand) == 2
        is_suited = hand.endswith('s')
        
        # For simplicity, keep hands that likely connect with board
        # This is a simplified heuristic
        
        if action in [Action.BET, Action.RAISE, Action.THREE_BET, Action.ALL_IN]:
            # Aggressive action - narrow to strong hands and bluffs
            if is_pair and hand[0] in 'AKQJT98':
                narrowed_range.add(hand)
            elif hand.startswith('A'):
                narrowed_range.add(hand)
            elif is_suited and 'K' in hand or 'Q' in hand:
                narrowed_range.add(hand)
            elif is_monotone and is_suited:
                # Could have flush draw
                narrowed_range.add(hand)
            else:
                removed_hands.add(hand)
        
        elif action == Action.CALL:
            # Calling - medium strength or draws
            narrowed_range.add(hand)  # Keep most hands when calling
        
        elif action == Action.CHECK:
            # Checking - weak or trapping
            narrowed_range.add(hand)
        
        elif action == Action.FOLD:
            # Remove strong hands from range on fold
            if not (is_pair and hand[0] in 'AKQJT') and not hand.startswith('AK'):
                narrowed_range.add(hand)
    
    if not narrowed_range:
        narrowed_range = preflop_range
    
    return {
        'range': narrowed_range,
        'removed': removed_hands,
        'board_texture': {
            'monotone': is_monotone,
            'two_tone': is_two_tone,
            'paired': is_paired,
            'connected': is_connected,
            'high_card': RANKS[high_card] if high_card else 'None'
        },
        'bet_sizing_analysis': sizing
    }


# ============================================================
# RANGE VISUALIZATION
# ============================================================

def format_range_grid(range_set: Set[str]) -> str:
    """
    Create a visual grid representation of a range.
    """
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    
    grid = []
    header = "   " + " ".join(f"{r:>3}" for r in ranks)
    grid.append(header)
    
    for i, r1 in enumerate(ranks):
        row = f"{r1}: "
        for j, r2 in enumerate(ranks):
            if i == j:
                # Pocket pair
                hand = f"{r1}{r2}"
            elif i < j:
                # Suited (above diagonal)
                hand = f"{r1}{r2}s"
            else:
                # Offsuit (below diagonal)
                hand = f"{r2}{r1}o"
            
            if hand in range_set:
                row += "  ■ "
            else:
                row += "  · "
        grid.append(row)
    
    return "\n".join(grid)


def get_range_summary(range_set: Set[str]) -> Dict:
    """
    Get a summary of a range.
    """
    pairs = [h for h in range_set if len(h) == 2]
    suited = [h for h in range_set if h.endswith('s')]
    offsuit = [h for h in range_set if h.endswith('o')]
    
    # Calculate combo count
    combo_count = len(pairs) * 6 + len(suited) * 4 + len(offsuit) * 12
    percentage = (combo_count / 1326) * 100
    
    return {
        'pairs': sorted(pairs, key=lambda x: RANKS.index(x[0]) if x[0] in RANKS else 14, reverse=True),
        'suited': sorted(suited),
        'offsuit': sorted(offsuit),
        'combo_count': combo_count,
        'percentage': round(percentage, 1),
        'total_hands': len(range_set)
    }


# ============================================================
# POSITION ANALYSIS
# ============================================================

def get_position_info(position: Position) -> Dict:
    """
    Get information about a position.
    """
    info = {
        Position.UTG: {
            'name': 'Under the Gun',
            'abbreviation': 'UTG',
            'order': 1,
            'description': 'First to act preflop. Play very tight from here.',
            'recommended_range': '~8-10% of hands'
        },
        Position.UTG1: {
            'name': 'UTG+1',
            'abbreviation': 'UTG+1',
            'order': 2,
            'description': 'Second earliest position. Still play tight.',
            'recommended_range': '~10-12% of hands'
        },
        Position.MP: {
            'name': 'Middle Position',
            'abbreviation': 'MP',
            'order': 3,
            'description': 'Middle position. Can open up slightly.',
            'recommended_range': '~12-15% of hands'
        },
        Position.MP1: {
            'name': 'Middle Position +1',
            'abbreviation': 'MP+1',
            'order': 4,
            'description': 'Later middle position.',
            'recommended_range': '~15-18% of hands'
        },
        Position.CO: {
            'name': 'Cutoff',
            'abbreviation': 'CO',
            'order': 5,
            'description': 'Second best position. Good for stealing.',
            'recommended_range': '~20-25% of hands'
        },
        Position.BTN: {
            'name': 'Button',
            'abbreviation': 'BTN',
            'order': 6,
            'description': 'Best position! Act last postflop. Play wide.',
            'recommended_range': '~35-50% of hands'
        },
        Position.SB: {
            'name': 'Small Blind',
            'abbreviation': 'SB',
            'order': 7,
            'description': 'Forced bet, out of position postflop.',
            'recommended_range': 'Depends on action'
        },
        Position.BB: {
            'name': 'Big Blind',
            'abbreviation': 'BB',
            'order': 8,
            'description': 'Defends vs steals. Gets good pot odds.',
            'recommended_range': 'Wide defense range'
        }
    }
    
    return info.get(position, {})

