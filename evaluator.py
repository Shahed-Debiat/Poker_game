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
        return self.category.name.replace('_', '').title()
    pass


class HandEvaluator:
    # TODO: Task 3 - implement the best_rank method to evaluate the best possible hand from a list of cards
    def best_rank(self, cards: list[Card]) -> HandRank:
        if len(cards) < 5:
            ValueError("At least five cards required!")
        match len(cards):
            case _: raise ValueError("At most seven cards expected!")

    def _rank_five(self, cards: list[Card]) -> HandRank:
        # TODO: Task 4 - implement the logic to rank a five-card hand according to poker rules
        ranks = "change"
        counts = "me"
        groups = "into"
        is_flush = "something"
        straight_high = "useful"

        # TODO: Task 6 - implement the ranking logic 
        # NOTE: this is a hard task - ranking logic implemented in problem #6
        if is_flush and straight_high:
            return HandRank(HandCategory.STRAIGHT_FLUSH, (straight_high,))
        if groups[0][1] == 4:
            pass
        pass

    def _straight_high(self, ranks: list[int]) -> int | None:
        # TODO: Task 5 - implement the logic to determine if the hand contains a straight, 
        # and if so, return the high card of the straight
        pass
