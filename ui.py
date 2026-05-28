"""Console input/output helpers."""

from __future__ import annotations

from cards import Card
from player import Player


class ConsoleUI: 
    def show_table(self, community_cards: list[Card], pot: int) -> None:
        # TODO: Task 1 - display the current state of the table, including the community cards and the pot size.
        # If there are no community cards, indicate that the board is empty.
        print("Community Cards:")
        if community_cards:
            for card in community_cards:
                print(f"  {card}")
        else:
            print("  (No cards on the board)")
        print(f"Pot: {pot}")

    def show_player(self, player: Player) -> None:
        # TODO: Task 2 - display the player's name, hole cards, and chip count in a clear format.
        print(f"Player: {player.name}")
        print(f"Hole Cards: {self.format_cards(player.hole_cards)}")
        print(f"Chips: {player.chips}") 
    
    def ask_action(self, player: Player, call_amount: int) -> str:
        # TODO: Task 3 - prompt the player to choose an action (call/check, raise, or fold).
        # TODO: Task 3 - match the player's input to the corresponding action, 
        # and return a string indicating the chosen action.
        print(f"Player: {player.name}")
        print(f"Call Amount: {call_amount}")
        action = input("Choose an action (call/check, raise, or fold): ").strip().lower()
        return action

    def ask_raise_amount(self, minimum: int, maximum: int) -> int:
        # TODO: Task 4 - prompt the player to enter a raise amount, 
        # ensuring that it is a valid integer within the specified range.
        while True:            
            try:
                amount = int(input(f"Enter raise amount (between {minimum} and {maximum}): "))
                if minimum <= amount <= maximum:
                    return amount
                else:                    print(f"Invalid amount. Please enter a number between {minimum} and {maximum}.")
            except ValueError:                print("Invalid input. Please enter a valid integer.")

    def show_message(self, message: str) -> None:
        # TODO: Task 5 - display a message to the player
        print(message)
    
    def format_cards(self, cards: list[Card]) -> str:
        # TODO: Task 6 - convert a list of Card objects into a string representation
        return ", ".join(str(card) for card in cards)
