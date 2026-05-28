"""Main Texas Hold'em game loop."""

from __future__ import annotations

from cards import Deck
from evaluator import HandEvaluator
from player import Player
from table import Table
from ui import ConsoleUI


class TexasHoldemGame:
    def __init__(self, players: list[Player], small_blind: int = 5, big_blind: int = 10) -> None:
        # TODO: Task 1 - check that there are at least 2 players, and if so, 
        if len(self.players) < 2:
            raise ValueError("Texas Hold'em requires at least 2 players.")
        
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.table = Table()
        self.evaluator = HandEvaluator()
        self.ui = ConsoleUI()

    def play_hand(self) -> None:
        # TODO: Task 2 - implement the main game loop for a single hand of Texas Hold'em, following the 
        deck = Deck()
        deck.shuffle()
        
        self.table.reset()
        for player in self.players:
            player.reset()
            
        # Deal two cards to each player
        for _ in range(2):
            for player in self.players:
                player.receive_card(deck.deal())
                
        self._post_blinds()
        self._show_human_cards()
        
        # Pre-flop betting round
        self._betting_round("Pre-flop")
        
        # Flop (3 cards)
        if not self._only_one_player_left():
            self._deal_community(deck, 3, "Flop")
            self._betting_round("Flop")
            
        # Turn (1 card)
        if not self._only_one_player_left():
            self._deal_community(deck, 1, "Turn")
            self._betting_round("Turn")
            
        # River (1 card)
        if not self._only_one_player_left():
            self._deal_community(deck, 1, "River")
            self._betting_round("River")
            
        self._showdown()

        
    def _post_blinds(self) -> None:
        # TODO: Task 3 - have the first two players post the small and big blinds, 
        sb_player = self.players[0]
        bb_player = self.players[1]
        
        sb_player.chips -= self.small_blind
        bb_player.chips -= self.big_blind
        
        self.table.pot += self.small_blind + self.big_blind
        
        print(f"{sb_player.name} posts {self.small_blind}; {bb_player.name} posts {self.big_blind}")
        
    def _show_human_cards(self) -> None:
        # TODO: Task 4 - display the hole cards of all human players, e.g. "Alice: AH KH"
        for player in self.players:
            if player.is_human:
                cards_str = " ".join(str(card) for card in player.cards)
                print(f"{player.name}: {cards_str}")

    def _deal_community(self, deck: Deck, count: int, street: str) -> None:
        # TODO: Task 5 - stop if one player remains, deal the specified number of community 
        if self._only_one_player_left():
            return
            
        new_cards = [deck.deal() for _ in range(count)]
        self.table.community_cards.extend(new_cards)
        print(f"\n-- {street} --")
        
    def _betting_round(self, street: str) -> None:
        # TODO: Task 6 - implement the betting round for the specified street, where each 
        if self._only_one_player_left():
            return

        player_bets = {p: 0 for p in self.players if p.is_active}
        
        if street == "Pre-flop":
            if self.players[0].is_active: 
                player_bets[self.players[0]] = self.small_blind
            if self.players[1].is_active: 
                player_bets[self.players[1]] = self.big_blind
            current_max_bet = self.big_blind
            start_index = 2 % len(self.players)
        else:
            current_max_bet = 0
            start_index = 0

        acted_players = set()

        while True:
            active_players = [p for p in self.players if p.is_active]
            if len(active_players) <= 1:
                break

            # Verify if all active players have matched the current maximum bet and acted
            all_settled = True
            for p in active_players:
                if p not in acted_players or player_bets.get(p, 0) != current_max_bet:
                    all_settled = False
                    break
            if all_settled:
                break

            for i in range(len(self.players)):
                idx = (start_index + i) % len(self.players)
                player = self.players[idx]

                if not player.is_active:
                    continue

                if player in acted_players and player_bets.get(player, 0) == current_max_bet:
                    if all(player_bets.get(p, 0) == current_max_bet for p in self.players if p.is_active):
                        break

                call_amount = current_max_bet - player_bets.get(player, 0)

                if player.is_human:
                    action = self.ui.get_action(player, call_amount)
                else:
                    action = self._bot_action(player, call_amount)

                acted_players.add(player)

                if action == "fold":
                    player.is_active = False
                    print(f"{player.name} folds.")
                elif action == "raise":
                    raise_amount = self.big_blind
                    total_new_bet = current_max_bet + raise_amount
                    additional_chips = total_new_bet - player_bets.get(player, 0)

                    if player.chips >= additional_chips:
                        player.chips -= additional_chips
                        self.table.pot += additional_chips
                        player_bets[player] = total_new_bet
                        current_max_bet = total_new_bet
                        print(f"{player.name} raises to {total_new_bet}.")
                    else:
                        action = "call"  # Fallback to call if chips are insufficient to raise

                if action in ("call", "check"):
                    if call_amount == 0:
                        print(f"{player.name} checks.")
                    else:
                        amount_to_pay = min(call_amount, player.chips)
                        player.chips -= amount_to_pay
                        self.table.pot += amount_to_pay
                        player_bets[player] = player_bets.get(player, 0) + amount_to_pay
                        print(f"{player.name} calls {amount_to_pay}.")

            start_index = 0  # Subsequent iterations start from the absolute standard position

    def _bot_action(self, player: Player, call_amount: int) -> str:
        # TODO: Task 7 - implement a simple bot strategy based on the 
        if call_amount == 0:
            return "check"
        elif call_amount > player.chips * 0.5:
            return "fold"
        else:
            return "call"

    def _showdown(self) -> None:
        # TODO: Task 8 - if only one player remains, they win the pot; 
        active_players = [p for p in self.players if p.is_active]

        if len(active_players) == 1:
            winner = active_players[0]
            winner.chips += self.table.pot
            print(f"{winner.name} wins the pot of {self.table.pot}!")
            self.table.pot = 0
            return

        best_player = None
        best_score = -1

        for player in active_players:
            # Evaluate using both hole cards and table community cards
            score = self.evaluator.evaluate(player.cards + self.table.community_cards)
            if score > best_score:
                best_score = score
                best_player = player

        if best_player:
            best_player.chips += self.table.pot
            print(f"{best_player.name} wins the showdown with a pot of {self.table.pot}!")
            self.table.pot = 0

    def _only_one_player_left(self) -> bool:
        # TODO: Task 9 - return True if only one player is still active and False otherwise
        return len([p for p in self.players if p.is_active]) == 1
