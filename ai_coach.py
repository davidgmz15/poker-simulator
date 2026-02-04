"""
AI Coach - Strategic explanations powered by AI
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

# OpenAI integration - loaded lazily to avoid slow startup
# Set OPENAI_API_KEY environment variable to enable
OPENAI_AVAILABLE = False
_openai_client = None

def _get_openai_client():
    """Lazily load OpenAI client to avoid slow imports at startup"""
    global OPENAI_AVAILABLE, _openai_client
    if _openai_client is not None:
        return _openai_client
    
    import os
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=api_key)
        OPENAI_AVAILABLE = True
        return _openai_client
    except Exception:
        return None


@dataclass
class GameState:
    """Represents the current state of the game for AI analysis"""
    hole_cards: List[str]
    board: List[str]
    pot_size: float
    to_call: float
    stack_size: float
    position: str
    street: str  # preflop, flop, turn, river
    num_opponents: int
    pot_odds: Dict
    equity: float
    outs: int
    draws: Dict
    opponent_ranges: List[Dict]
    is_preflop_aggressor: bool
    previous_actions: List[str]


class AICoach:
    """AI-powered poker coach that explains strategy"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = None
    
    @property
    def client(self):
        """Lazily initialize OpenAI client on first use"""
        if self._client is None:
            self._client = _get_openai_client()
        return self._client
    
    def get_strategic_advice(self, game_state: GameState) -> Dict:
        """
        Get comprehensive strategic advice for the current situation.
        """
        # Build context for the AI
        context = self._build_context(game_state)
        
        if self.client:
            # Use OpenAI for advanced analysis
            return self._get_ai_advice(context, game_state)
        else:
            # Fall back to rule-based advice
            return self._get_rule_based_advice(game_state)
    
    def _build_context(self, state: GameState) -> str:
        """Build a context string describing the current situation"""
        
        context = f"""
POKER SITUATION ANALYSIS:

Your Hand: {' '.join(state.hole_cards)}
Board: {' '.join(state.board) if state.board else 'No cards yet (preflop)'}
Street: {state.street.upper()}
Position: {state.position}

POT & BETTING:
- Pot Size: ${state.pot_size:.2f}
- Amount to Call: ${state.to_call:.2f}
- Your Stack: ${state.stack_size:.2f}

MATH:
- Pot Odds: {state.pot_odds.get('display', 'N/A')} ({state.pot_odds.get('percentage', 0):.1f}% required equity)
- Your Equity: {state.equity:.1f}%
- Outs: {state.outs}

DRAWS:
"""
        for draw_type, draw_info in state.draws.items():
            if draw_info and draw_info is not False:
                context += f"- {draw_type}: {draw_info}\n"
        
        context += f"""
OPPONENTS:
- Number of opponents: {state.num_opponents}
- You are {'the preflop aggressor' if state.is_preflop_aggressor else 'not the preflop aggressor'}

OPPONENT RANGES (estimated):
"""
        for i, opp_range in enumerate(state.opponent_ranges):
            if opp_range:
                context += f"- Opponent {i+1}: {opp_range.get('description', 'Unknown')} (~{opp_range.get('percentage', '?')}% of hands)\n"
        
        return context
    
    def _get_ai_advice(self, context: str, state: GameState) -> Dict:
        """Get advice from OpenAI"""
        
        system_prompt = """You are an expert poker coach helping a player learn the mathematical and strategic aspects of Texas Hold'em poker. 

Your role is to:
1. Explain the current situation clearly
2. Break down the math (pot odds vs equity)
3. Recommend the best action with reasoning
4. Explain what opponent ranges might be
5. Discuss position and aggression factors
6. Provide a clear recommendation

Be concise but thorough. Use simple language a beginner can understand while still providing depth for intermediate players. Always tie your advice back to the math when possible."""

        user_prompt = f"""{context}

Based on this situation, please provide:
1. A quick situation summary
2. The mathematical analysis (is this a profitable call/fold/raise?)
3. Strategic considerations (position, opponent tendencies, board texture)
4. Your recommended action and why
5. What to watch for on future streets

Keep the response focused and actionable."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            advice_text = response.choices[0].message.content
            
            return {
                'success': True,
                'advice': advice_text,
                'source': 'ai',
                'context': context
            }
            
        except Exception as e:
            # Fall back to rule-based if API fails
            rule_based = self._get_rule_based_advice(state)
            rule_based['api_error'] = str(e)
            return rule_based
    
    def _get_rule_based_advice(self, state: GameState) -> Dict:
        """Provide rule-based advice when AI is not available"""
        
        advice_parts = []
        
        # 1. Situation Summary
        advice_parts.append("**SITUATION SUMMARY**")
        advice_parts.append(f"You hold {' '.join(state.hole_cards)} on the {state.street} from {state.position}.")
        if state.board:
            advice_parts.append(f"Board: {' '.join(state.board)}")
        advice_parts.append("")
        
        # 2. Mathematical Analysis
        advice_parts.append("**MATHEMATICAL ANALYSIS**")
        
        pot_odds_pct = state.pot_odds.get('percentage', 0)
        equity = state.equity
        
        if state.to_call > 0:
            advice_parts.append(f"• Pot Odds: {state.pot_odds.get('display', 'N/A')} = {pot_odds_pct:.1f}% required equity")
            advice_parts.append(f"• Your Equity: {equity:.1f}%")
            
            ev = (equity / 100) * (state.pot_size + state.to_call) - (1 - equity / 100) * state.to_call
            
            if equity > pot_odds_pct:
                diff = equity - pot_odds_pct
                advice_parts.append(f"• You have +{diff:.1f}% equity advantage - PROFITABLE CALL")
                advice_parts.append(f"• Expected Value: +${ev:.2f} per call in the long run")
            else:
                diff = pot_odds_pct - equity
                advice_parts.append(f"• You need {diff:.1f}% more equity - UNPROFITABLE CALL")
                advice_parts.append(f"• Expected Value: ${ev:.2f} per call in the long run")
        else:
            advice_parts.append("• Free to see the next card - always check when free!")
        
        advice_parts.append("")
        
        # 3. Draw Analysis
        if state.outs > 0:
            advice_parts.append("**DRAWING ANALYSIS**")
            advice_parts.append(f"• Outs: {state.outs}")
            
            if state.draws.get('flush_draw'):
                advice_parts.append("• Flush draw (9 outs)")
            if state.draws.get('open_ended_straight_draw'):
                advice_parts.append("• Open-ended straight draw (8 outs)")
            if state.draws.get('gutshot_straight_draw'):
                advice_parts.append("• Gutshot straight draw (4 outs)")
            if state.draws.get('overcards'):
                advice_parts.append(f"• Overcards: {len(state.draws['overcards'])} ({len(state.draws['overcards']) * 3} outs)")
            
            # Rule of 4 and 2
            if state.street == 'flop':
                quick_equity = state.outs * 4
                advice_parts.append(f"• Rule of 4: {state.outs} outs × 4 = ~{quick_equity}% to hit by river")
            elif state.street == 'turn':
                quick_equity = state.outs * 2
                advice_parts.append(f"• Rule of 2: {state.outs} outs × 2 = ~{quick_equity}% to hit on river")
            
            advice_parts.append("")
        
        # 4. Position Analysis
        advice_parts.append("**POSITION ANALYSIS**")
        
        position_advice = {
            'BTN': "You're on the Button - best position! You act last postflop, giving you maximum information.",
            'CO': "You're in the Cutoff - great position. Consider stealing if folded to you.",
            'MP': "Middle Position - play solid hands. Many players still to act.",
            'UTG': "Under the Gun - earliest position. Only play premium hands here.",
            'SB': "Small Blind - worst position postflop. Be cautious without strong hands.",
            'BB': "Big Blind - you have position in the betting order but are OOP postflop."
        }
        
        advice_parts.append(f"• {position_advice.get(state.position, 'Consider your position relative to opponents.')}")
        
        if state.is_preflop_aggressor:
            advice_parts.append("• You were the preflop aggressor - consider a continuation bet.")
        else:
            advice_parts.append("• You called preflop - be more cautious without a strong hand.")
        
        advice_parts.append("")
        
        # 5. Recommendation
        advice_parts.append("**RECOMMENDATION**")
        
        if state.to_call == 0:
            if equity > 50:
                advice_parts.append("**BET** - You likely have the best hand. Build the pot.")
            else:
                advice_parts.append("**CHECK** - Free card, see what develops.")
        elif equity > pot_odds_pct + 15:
            advice_parts.append("**RAISE** - Strong equity advantage. Build the pot or take it now.")
        elif equity > pot_odds_pct + 5:
            advice_parts.append("**CALL** - Profitable call based on pot odds.")
        elif equity > pot_odds_pct - 5:
            implied_odds_good = state.stack_size > state.pot_size * 5
            if implied_odds_good:
                advice_parts.append("**CALL (marginal)** - Close decision, but good implied odds if you hit.")
            else:
                advice_parts.append("**FOLD** - Marginally unprofitable. Save your chips for better spots.")
        else:
            advice_parts.append("**FOLD** - The math doesn't support a call here.")
        
        advice_parts.append("")
        
        # 6. Key Takeaway
        advice_parts.append("💡 **KEY LEARNING**")
        
        if equity > pot_odds_pct:
            advice_parts.append(f"When your equity ({equity:.1f}%) exceeds the pot odds requirement ({pot_odds_pct:.1f}%), calling is mathematically profitable over time, even if you lose this specific hand.")
        else:
            advice_parts.append(f"When pot odds require {pot_odds_pct:.1f}% equity but you only have {equity:.1f}%, folding preserves your stack for better opportunities.")
        
        return {
            'success': True,
            'advice': '\n'.join(advice_parts),
            'source': 'rule_based',
            'math_summary': {
                'pot_odds_pct': pot_odds_pct,
                'equity': equity,
                'is_profitable': equity > pot_odds_pct,
                'ev_per_call': (equity / 100) * (state.pot_size + state.to_call) - (1 - equity / 100) * state.to_call if state.to_call > 0 else 0
            }
        }
    
    def explain_concept(self, concept: str) -> str:
        """Explain a poker concept"""
        
        concepts = {
            'pot_odds': """
**POT ODDS EXPLAINED**

Pot odds are the ratio between the current pot size and the cost of a call.

**Formula:** Pot Odds = Pot Size ÷ Call Amount

**Example:**
- Pot is $100, opponent bets $50
- You need to call $50 to win $150 (pot + their bet)
- Pot Odds = $150 ÷ $50 = 3:1

**As a percentage:**
- You need to win 1 out of every 4 times to break even
- That's 25% equity required

**Why it matters:**
If your hand wins more than 25% of the time, calling is profitable!
""",
            
            'equity': """
**EQUITY EXPLAINED**

Equity is your share of the pot based on your probability of winning.

**Example:**
- You have a flush draw (9 outs)
- On the flop, you'll hit by the river about 35% of the time
- Your equity is 35%

**The Rule of 4 and 2:**
- On the flop: Outs × 4 = approximate % to hit by river
- On the turn: Outs × 2 = approximate % to hit on river

**Common draws:**
- Flush draw: 9 outs = ~35% (flop) / ~18% (turn)
- Open-ended straight: 8 outs = ~32% (flop) / ~16% (turn)
- Gutshot straight: 4 outs = ~16% (flop) / ~8% (turn)
- Overcards: 6 outs = ~24% (flop) / ~12% (turn)
""",
            
            'implied_odds': """
**IMPLIED ODDS EXPLAINED** 💰

Implied odds account for money you might win on future streets if you hit your hand.

**When they matter:**
- Deep stacks (lots of money behind)
- Hidden draws (opponent won't see it coming)
- Strong draws that make the nuts

**Example:**
- You have a gutshot (4 outs, ~8% to hit)
- Pot odds only give you 5:1 (need 17%)
- BUT if you hit, opponent might pay off big
- With deep stacks, you have good implied odds

**Caution:**
Don't overestimate implied odds when:
- Opponent is tight and will fold if you hit
- The board is obvious (like 4 to a flush)
- Stacks are shallow
""",
            
            'position': """
**POSITION EXPLAINED**

Position refers to where you sit relative to the dealer button.

**Why position matters:**
1. Information - acting last means seeing what others do first
2. Control - you can size bets based on opponent actions
3. Free cards - you can check behind to see free cards

**Positions (best to worst):**
1. **Button (BTN)** - BEST! Act last on every postflop street
2. **Cutoff (CO)** - Second best, good for stealing
3. **Middle Position (MP)** - Play solid hands
4. **Under the Gun (UTG)** - WORST! Play only premium hands
5. **Blinds (SB/BB)** - Forced bets, out of position postflop

**Key insight:**
Play MORE hands in position, FEWER hands out of position.
""",
            
            'ranges': """
**HAND RANGES EXPLAINED**

A range is all the possible hands someone could have based on their actions.

**Building ranges:**
1. Start with preflop position (UTG is tight, BTN is wide)
2. Consider the action (raise, call, limp)
3. Narrow based on postflop actions

**Example:**
- UTG raises → Strong range (top 10% of hands)
- Button calls → Medium-wide range
- UTG bets flop → Narrows to hands that connect or bluffs

**Range notation:**
- AA, KK = pocket pairs
- AKs = Ace-King suited
- AKo = Ace-King offsuit
- 22+ = all pairs 22 and above
- ATs+ = AT suited and better (AJ, AQ, AK)

**Thinking in ranges beats thinking in specific hands!**
"""
        }
        
        return concepts.get(concept.lower(), f"Concept '{concept}' not found. Try: pot_odds, equity, implied_odds, position, ranges")


def create_game_state(
    hole_cards: List[str],
    board: List[str],
    pot_size: float,
    to_call: float,
    stack_size: float,
    position: str,
    street: str,
    num_opponents: int,
    pot_odds: Dict,
    equity: float,
    outs: int,
    draws: Dict,
    opponent_ranges: List[Dict] = None,
    is_preflop_aggressor: bool = False,
    previous_actions: List[str] = None
) -> GameState:
    """Helper function to create a GameState object"""
    
    return GameState(
        hole_cards=hole_cards,
        board=board,
        pot_size=pot_size,
        to_call=to_call,
        stack_size=stack_size,
        position=position,
        street=street,
        num_opponents=num_opponents,
        pot_odds=pot_odds,
        equity=equity,
        outs=outs,
        draws=draws,
        opponent_ranges=opponent_ranges or [],
        is_preflop_aggressor=is_preflop_aggressor,
        previous_actions=previous_actions or []
    )

