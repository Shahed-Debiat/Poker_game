"""Five-card hand evaluator used to rank Texas Hold'em showdowns."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum 
from itertools import combinations
from cards import Card


class HandCategory(IntEnum):
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8


@dataclass(frozen=True, order=True)
class HandRank:
    category: HandCategory
    _label: str

    @property
    def label(self) -> str:
        return self.category.name.replace('_', ' ').title()
    pass


class HandEvaluator:
    def best_rank(self, cards: list[Card]) -> HandRank:
        if len(cards) < 5:
            raise ValueError("At least five cards required!")
        return max(self._rank_five(list(combo)) for combo in combinations(cards, 5))

    def _rank_five(self, cards: list[Card]) -> HandRank:
        ranks = sorted([card.rank for card in cards], reverse=True)
        counts = Counter(card.rank for card in cards)
        groups = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
        is_flush = len(set(card.suit for card in cards)) == 1
        straight_high = self._straight_high(ranks)

        if is_flush and straight_high:
            return HandRank(HandCategory.STRAIGHT_FLUSH, (straight_high,))
        if groups[0][1] == 4:
            return HandRank(HandCategory.FOUR_OF_A_KIND, tuple(r for r, _ in groups))
        if groups[0][1] == 3 and groups[1][1] == 2:
            return HandRank(HandCategory.FULL_HOUSE, tuple(r for r, _ in groups))
        if is_flush:
            return HandRank(HandCategory.FLUSH, tuple(ranks))
        if straight_high:
            return HandRank(HandCategory.STRAIGHT, (straight_high,))
        if groups[0][1] == 3:
            return HandRank(HandCategory.THREE_OF_A_KIND, tuple(r for r, _ in groups))
        if groups[0][1] == 2 and groups[1][1] == 2:
            return HandRank(HandCategory.TWO_PAIR, tuple(r for r, _ in groups))
        if groups[0][1] == 2:
            return HandRank(HandCategory.ONE_PAIR, tuple(r for r, _ in groups))
        return HandRank(HandCategory.HIGH_CARD, tuple(ranks))

    def _straight_high(self, ranks: list[int]) -> int | None:
        unique = sorted(set(ranks), reverse=True)
        if set([14, 2, 3, 4, 5]).issubset(set(unique)):
            return 5
        for i in range(len(unique) - 4):
            window = unique[i:i + 5]
            if window[0] - window[4] == 4 and len(window) == 5:
                return window[0]
        return None

if __name__ == "__main__":
    from cards import Card, Rank, Suit

    evaluator = HandEvaluator()

    # Straight Flush: 9-10-J-Q-K of Hearts
    sf = [Card(Rank.NINE, Suit.HEARTS), Card(Rank.TEN, Suit.HEARTS),
          Card(Rank.JACK, Suit.HEARTS), Card(Rank.QUEEN, Suit.HEARTS),
          Card(Rank.KING, Suit.HEARTS)]

    # Four of a Kind: four Aces + King
    foak = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.ACE, Suit.CLUBS), Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS)]

    # Full House: three Kings + two Queens
    fh = [Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.DIAMONDS),
          Card(Rank.KING, Suit.CLUBS), Card(Rank.QUEEN, Suit.HEARTS),
          Card(Rank.QUEEN, Suit.DIAMONDS)]

    # Flush: A-J-9-6-2 of Spades
    fl = [Card(Rank.ACE, Suit.SPADES), Card(Rank.JACK, Suit.SPADES),
          Card(Rank.NINE, Suit.SPADES), Card(Rank.SIX, Suit.SPADES),
          Card(Rank.TWO, Suit.SPADES)]

    # Straight: 5-6-7-8-9
    st = [Card(Rank.FIVE, Suit.HEARTS), Card(Rank.SIX, Suit.DIAMONDS),
          Card(Rank.SEVEN, Suit.CLUBS), Card(Rank.EIGHT, Suit.SPADES),
          Card(Rank.NINE, Suit.HEARTS)]

    # Three of a Kind: three Jacks
    toak = [Card(Rank.JACK, Suit.HEARTS), Card(Rank.JACK, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS), Card(Rank.THREE, Suit.SPADES),
            Card(Rank.TWO, Suit.HEARTS)]

    # Two Pair: Aces and Kings
    tp = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.ACE, Suit.DIAMONDS),
          Card(Rank.KING, Suit.HEARTS), Card(Rank.KING, Suit.DIAMONDS),
          Card(Rank.TWO, Suit.CLUBS)]

    # One Pair: pair of Queens
    op = [Card(Rank.QUEEN, Suit.HEARTS), Card(Rank.QUEEN, Suit.DIAMONDS),
          Card(Rank.ACE, Suit.CLUBS), Card(Rank.KING, Suit.SPADES),
          Card(Rank.TWO, Suit.HEARTS)]

    # High Card: A-K-Q-J-9
    hc = [Card(Rank.ACE, Suit.HEARTS), Card(Rank.KING, Suit.DIAMONDS),
          Card(Rank.QUEEN, Suit.CLUBS), Card(Rank.JACK, Suit.SPADES),
          Card(Rank.NINE, Suit.HEARTS)]

    hands = [sf, foak, fh, fl, st, toak, tp, op, hc]
    expected = ["Straight Flush", "Four Of A Kind", "Full House", "Flush",
                "Straight", "Three Of A Kind", "Two Pair", "One Pair", "High Card"]

    for hand, exp in zip(hands, expected):
        result = evaluator.best_rank(hand)
        status = "OK" if result.label == exp else "FAIL"
        print(f"{status}: expected {exp}, got {result.label}")