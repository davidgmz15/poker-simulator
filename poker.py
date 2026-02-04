import random
from enum import Enum

class Player:
    def __init__(self, name="", hand=None, stack=0):
        self.name = name
        self.hand = [] if hand is None else hand
        self.stack = stack

    def reset_hand(self):
        self.hand = []

class Pot:
    def __init__(self):
        self.size = 0
        self.highest_bet = 0

class Card:
    def __init__(self, suit=" ", rank=" "):
        self.suit = suit
        self.rank = rank

class Round(Enum):
    PreFlop = 0
    Flop = 1
    Turn = 2
    River = 3

deck = [
    "A-H","2-H","3-H","4-H","5-H","6-H","7-H","8-H","9-H","10-H","J-H","Q-H","K-H",
    "A-S","2-S","3-S","4-S","5-S","6-S","7-S","8-S","9-S","10-S","J-S","Q-S","K-S",
    "A-D","2-D","3-D","4-D","5-D","6-D","7-D","8-D","9-D","10-D","J-D","Q-D","K-D",
    "A-C","2-C","3-C","4-C","5-C","6-C","7-C","8-C","9-C","10-C","J-C","Q-C","K-C",
]

def shuffle_deck(deck):
    shuffled = deck[:]
    random.shuffle(shuffled)
    return shuffled

def deal_hands(shuffled, players):
    n = len(players)
    idx = 0
    for _ in range(2):
        for p in players:
            p.hand.append(shuffled[idx])
            idx += 1
    return shuffled[idx:]

def deal_board(remaining):
    # burn, flop(3), burn, turn, burn, river
    flop = remaining[1:4]
    turn = remaining[5]
    river = remaining[7]
    return flop, turn, river

def make_card(str_card):
    rank, suit = str_card.split("-")
    return Card(suit=suit, number=rank)

def print_board(cards):
    print("\n")
    print("-------     " * 5)
    print(f"|    {cards[0].suit}|     |    {cards[1].suit}|     |    {cards[2].suit}|     |    {cards[3].suit}|     |    {cards[4].suit}|")
    print(f"|  {cards[0].rank}  |     |  {cards[1].rank}  |     |  {cards[2].rank}  |     |  {cards[3].rank}  |     |  {cards[4].rank}  |")
    print(f"|{cards[0].suit}    |     |{cards[1].suit}    |     |{cards[2].suit}    |     |{cards[3].suit}    |     |{cards[4].suit}    |")
    print("-------     " * 5)

def reveal_count(rnd):
    if rnd == Round.PreFlop: return 0
    if rnd == Round.Flop:    return 3
    if rnd == Round.Turn:    return 4
    return 5

def betting_round(players, pot, rnd, start_idx=0, min_bet=1):
    n = len(players)
    active = [True] * n
    bets = [0] * n

    pot.highest_bet = 0
    min_raise = min_bet
    last_raiser = None

    i = start_idx
    first_pass = True

    print(f"\n{rnd.name} Betting Begins:\n")

    while True:
        if sum(active) == 1:
            break

        if not active[i]:
            i = (i + 1) % n
            continue

        to_call = pot.highest_bet - bets[i]
        p = players[i]
        print(f"{p.name} | stack={p.stack} | to_call={to_call} | pot={pot.size}")

        if pot.highest_bet == 0:
            action = input("Action: (c)heck (b)et (f)old: \n").strip().lower()
            if action == "f":
                active[i] = False
            elif action == "c":
                pass
            elif action == "b":
                amt = int(input(f"Bet amount (>= {min_bet}): "))
                if amt < min_bet or amt > p.stack:
                    print("Invalid bet.")
                    continue
                p.stack -= amt
                bets[i] += amt
                pot.size += amt
                pot.highest_bet = bets[i]
                last_raiser = i
                min_raise = amt
            else:
                print("Invalid action.")
                continue

        else:
            action = input("Action: (k)call (r)aise (f)old: \n").strip().lower()
            if action == "f":
                active[i] = False
            elif action == "k":
                paid = min(to_call, p.stack)
                p.stack -= paid
                bets[i] += paid
                pot.size += paid
            elif action == "r":
                old_highest = pot.highest_bet
                raise_to = int(input(f"Raise TO (>= {old_highest + min_raise}): "))
                if raise_to < old_highest + min_raise:
                    print("Raise too small.")
                    continue
                needed = raise_to - bets[i]
                if needed > p.stack:
                    print("Not enough chips.")
                    continue
                p.stack -= needed
                bets[i] += needed
                pot.size += needed
                pot.highest_bet = raise_to
                last_raiser = i
                min_raise = raise_to - old_highest
            else:
                print("Invalid action.")
                continue

        # termination
        if last_raiser is None:
            if not first_pass and i == start_idx:
                break
        else:
            if i == last_raiser:
                all_matched = True
                for j in range(n):
                    if active[j] and bets[j] < pot.highest_bet:
                        all_matched = False
                        break
                if all_matched:
                    break

        first_pass = False
        i = (i + 1) % n

    print(f"\nBetting round over | Pot: {pot.size}\n")
    return active

def main():
    print("Starting Texas Hold 'Em")
    print("-" * 27)

    num_players = int(input("How many players? "))
    players = []
    for i in range(num_players):
        name = input(f"Enter Player {i} name: ")
        stack = int(input(f"Enter Player {i} starting stack size: "))
        players.append(Player(name=name, stack=stack))

    while int(input("\nEnter 1 to begin, 0 to quit: ")) == 1:
        for p in players:
            p.reset_hand()

        shuffled = shuffle_deck(deck)
        remaining = deal_hands(shuffled, players)
        flop, turn, river = deal_board(remaining)
        board = flop[:] + [turn] + [river]

        pot = Pot()
        visible = [Card("?", "?") for _ in range(5)]

        for rnd in Round:
            k = reveal_count(rnd)
            for idx in range(k):
                visible[idx] = make_card(board[idx])

            print_board(visible)
            active = betting_round(players, pot, rnd)

            if sum(active) == 1:
                winner = active.index(True)
                players[winner].stack += pot.size
                print(f"{players[winner].name} wins {pot.size}!")
                break

        print("\nStacks:")
        for p in players:
            print(f"- {p.name}: {p.stack}")

if __name__ == "__main__":
    main()