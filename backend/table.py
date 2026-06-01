"""Shared table state for a Hold'em hand."""

from __future__ import annotations

from dataclasses import dataclass, field

from cards import Card


# TODO: Task 1 - implement the Table class 

class Table:
    def __init__(self):
        self.community_cards: list[Card] = []
        self.pot: int = 0

    # TODO: Task 2 - create and implement the method reset(self) -> None
    def reset(self):
        self.community_cards.clear()
        self.pot = 0

    # TODO: Task 3 - create and implement the method add_to_pot(self, amount: int) -> None
    def add_to_pot(self, amount: int):
        self.pot += amount 
