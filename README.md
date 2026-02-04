# 🎰 Poker Academy - Learn the Math Behind the Game

A comprehensive poker learning simulator that teaches players the mathematical and statistical aspects of Texas Hold'em poker. Built with Python/Flask backend and a beautiful, modern web interface.

![Poker Academy](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 📊 Real-Time Statistics
- **Pot Odds Calculator**: Instantly see the ratio between pot size and your call amount
- **Equity Calculator**: Monte Carlo simulation calculates your winning percentage
- **Outs Counter**: Automatic detection of flush draws, straight draws, and more
- **Rule of 4 and 2**: Quick equity estimation using standard poker math

### 🎯 Decision Analysis
- **Profitable Call Detection**: Combines pot odds and equity to show if a call is +EV
- **Expected Value Display**: See exactly how much you gain/lose per decision over time
- **Optimal Action Recommendations**: FOLD, CALL, CHECK, or RAISE suggestions with reasoning

### 🎴 Opponent Range Estimation
- **Position-Based Ranges**: Estimates opponent hand ranges based on table position
- **Action-Based Narrowing**: Ranges adjust based on raises, calls, and folds
- **Bet Sizing Analysis**: Learn what different bet sizes typically indicate

### 🤖 AI Coach
- **Strategic Explanations**: Get detailed breakdowns of each decision point
- **Concept Teaching**: Learn pot odds, equity, implied odds, position, and ranges
- **OpenAI Integration**: Optional GPT-4 powered analysis for deeper insights
- **Rule-Based Fallback**: Works without API key using comprehensive poker knowledge

### 🎨 Beautiful Interface
- **Immersive Poker Table**: Felt-textured table with realistic card designs
- **Real-Time Updates**: All statistics update as the hand progresses
- **Responsive Design**: Works on desktop and tablet
- **Dark Casino Theme**: Easy on the eyes for long study sessions

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project**:
   ```bash
   cd Poker-Simulator
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open your browser** and go to:
   ```
   http://localhost:5001
   ```

### Optional: Enable AI Coach with OpenAI

For advanced AI-powered explanations:

1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
2. Set the environment variable:
   ```bash
   export OPENAI_API_KEY=sk-your-key-here
   ```
3. Restart the application

## 🎮 How to Use

### Starting a Hand
1. Click **"New Hand"** or press `N`
2. Configure players/stakes in **Settings** (⚙️)
3. Your cards appear at the bottom of the table

### Reading the Statistics

**Left Panel - Statistics:**
- **Pot Odds**: Shows the ratio (e.g., 3:1) and required equity to call profitably
- **Equity**: Your win percentage based on Monte Carlo simulation
- **Outs**: Counts cards that improve your hand
- **Optimal Play**: Recommended action with expected value

**Right Panel - AI Coach:**
- Click **"Get Strategic Advice"** for detailed analysis
- Click concept buttons to learn poker fundamentals
- Opponent ranges update based on their actions

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `N` | New Hand |
| `F` | Fold |
| `C` | Check/Call |
| `R` | Raise |
| `D` | Deal next street |
| `A` | Get AI Advice |

## 📚 Poker Concepts Explained

### Pot Odds
The ratio of the current pot to the cost of calling. If the pot is $100 and you need to call $20, your pot odds are 5:1. You need to win 1 in 6 times (16.7%) to break even.

### Equity
Your share of the pot based on probability of winning. Calculated using Monte Carlo simulation (running thousands of random scenarios).

### The Rule of 4 and 2
Quick equity estimation:
- **Flop** (2 cards to come): Multiply outs × 4
- **Turn** (1 card to come): Multiply outs × 2

Example: Flush draw = 9 outs × 4 = 36% on the flop

### Combining Pot Odds & Equity
**If your equity > required equity from pot odds → CALL is profitable**

Example:
- Pot odds: 3:1 (need 25% equity)
- Your equity: 35%
- Decision: CALL (you have 10% edge)

## 🏗️ Project Structure

```
Poker-Simulator/
├── app.py              # Flask backend API
├── poker_engine.py     # Core calculations (equity, pot odds, hand evaluation)
├── range_estimator.py  # Opponent range estimation
├── ai_coach.py         # AI coaching module
├── poker.py            # Original basic simulator
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Main HTML template
└── static/
    ├── css/
    │   └── style.css   # Styling
    └── js/
        └── app.js      # Frontend JavaScript
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/new-hand` | POST | Start a new hand |
| `/api/deal/<street>` | POST | Deal flop/turn/river |
| `/api/action` | POST | Process player action |
| `/api/ai-advice` | POST | Get AI coaching advice |
| `/api/explain/<concept>` | GET | Explain a poker concept |
| `/api/calculate-equity` | POST | Calculate equity for cards |
| `/api/estimate-range` | POST | Estimate opponent range |
| `/api/state` | GET | Get current game state |

## 🎓 Learning Path

1. **Start Simple**: Play hands and observe the pot odds display
2. **Compare Numbers**: Notice when equity beats required equity
3. **Study Decisions**: Read the AI coach explanations
4. **Learn Ranges**: Watch how opponent ranges narrow
5. **Practice Concepts**: Use the concept buttons to review

## 🤝 Contributing

Contributions welcome! Ideas for improvement:
- Hand history tracking and review
- Tournament mode with increasing blinds
- Pre-set training scenarios
- Multi-table support
- Mobile app version

## 📄 License

MIT License - feel free to use, modify, and distribute.

---

**Happy Learning! 🎰♠️♥️♦️♣️**

*Remember: Poker is a game of skill over the long run. Understanding the math is the foundation of winning play.*

