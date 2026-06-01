"""Stateful Texas Hold'em game session — a state machine for the FastAPI layer."""
from __future__ import annotations

from typing import Optional

from cards import Deck
from evaluator import HandEvaluator
from player import Player
from table import Table


class GameSession:
    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self.small_blind = 5
        self.big_blind = 10

        self.players: list[Player] = [
            Player("You", chips=1000, is_human=True),
            Player("Ada Bot", chips=1000),
            Player("Grace Bot", chips=1000),
        ]
        self.table = Table()
        self.evaluator = HandEvaluator()
        self.messages: list[str] = []

        self.deck: Optional[Deck] = None
        self.phase: str = "idle"

        # Betting state
        self.player_bets: dict[int, int] = {}
        self.current_max_bet: int = 0
        self.acted_players: set[int] = set()
        self.action_queue: list[int] = []
        self.awaiting_action: bool = False
        self.current_call_amount: int = 0
        self.current_actor_idx: Optional[int] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start_hand(self) -> None:
        human = next(p for p in self.players if p.is_human)
        if human.chips <= 0:
            self.phase = "game_over"
            self.messages.append("You have no chips left. Start a new game!")
            return

        self.deck = Deck()
        self.table.reset()
        for player in self.players:
            player.reset_for_hand()

        for _ in range(2):
            for player in self.players:
                player.receive(self.deck.deal(1))

        self._post_blinds()
        self.phase = "pre_flop"
        self._start_betting_round(is_preflop=True)

    def submit_action(self, action: str) -> None:
        if not self.awaiting_action:
            return

        actor_idx = self.current_actor_idx
        call_amount = self.current_call_amount

        self.awaiting_action = False
        self.action_queue.pop(0)
        self._apply_action(actor_idx, action, call_amount)
        self._process_queue()

    def get_state(self) -> dict:
        reveal_all = self.phase in ("hand_complete", "showdown", "game_over")

        players_state = []
        for i, p in enumerate(self.players):
            if p.is_human:
                hole_cards = [str(c) for c in p.hole_cards]
            elif reveal_all and not p.folded and p.hole_cards:
                hole_cards = [str(c) for c in p.hole_cards]
            elif p.folded or not p.hole_cards:
                hole_cards = []
            else:
                hole_cards = ["??", "??"]

            players_state.append({
                "index": i,
                "name": p.name,
                "chips": p.chips,
                "is_human": p.is_human,
                "hole_cards": hole_cards,
                "folded": p.folded,
                "active": p.active,
                "is_current_actor": i == self.current_actor_idx and self.awaiting_action,
            })

        return {
            "game_id": self.game_id,
            "phase": self.phase,
            "awaiting_action": self.awaiting_action,
            "call_amount": self.current_call_amount if self.awaiting_action else 0,
            "community_cards": [str(c) for c in self.table.community_cards],
            "pot": self.table.pot,
            "players": players_state,
            "messages": self.messages[-40:],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post_blinds(self) -> None:
        sb, bb = self.players[0], self.players[1]
        sb_amt = min(self.small_blind, sb.chips)
        bb_amt = min(self.big_blind, bb.chips)
        sb.chips -= sb_amt
        bb.chips -= bb_amt
        self.table.pot += sb_amt + bb_amt
        self.messages.append(f"{sb.name} posts small blind {sb_amt}")
        self.messages.append(f"{bb.name} posts big blind {bb_amt}")

    def _start_betting_round(self, is_preflop: bool = False) -> None:
        self.player_bets = {i: 0 for i in range(len(self.players))}
        self.acted_players = set()
        self.awaiting_action = False

        if is_preflop:
            self.player_bets[0] = self.small_blind
            self.player_bets[1] = self.big_blind
            self.current_max_bet = self.big_blind
            start_idx = 2 % len(self.players)
        else:
            self.current_max_bet = 0
            start_idx = 0

        self.action_queue = []
        for i in range(len(self.players)):
            idx = (start_idx + i) % len(self.players)
            if self.players[idx].active:
                self.action_queue.append(idx)

        self._process_queue()

    def _process_queue(self) -> None:
        if self.phase in ("hand_complete", "showdown", "game_over"):
            return

        while self.action_queue:
            active_count = sum(1 for p in self.players if p.active)
            if active_count <= 1:
                self._end_hand()
                return

            actor_idx = self.action_queue[0]
            actor = self.players[actor_idx]

            if not actor.active:
                self.action_queue.pop(0)
                continue

            if (actor_idx in self.acted_players
                    and self.player_bets.get(actor_idx, 0) >= self.current_max_bet):
                self.action_queue.pop(0)
                continue

            call_amount = self.current_max_bet - self.player_bets.get(actor_idx, 0)

            if actor.is_human:
                self.awaiting_action = True
                self.current_actor_idx = actor_idx
                self.current_call_amount = call_amount
                return
            else:
                action = self._bot_action(actor, call_amount)
                self.action_queue.pop(0)
                self._apply_action(actor_idx, action, call_amount)

        # Queue exhausted — all active players settled
        active_count = sum(1 for p in self.players if p.active)
        if active_count <= 1:
            self._end_hand()
        else:
            self._advance_phase()

    def _apply_action(self, idx: int, action: str, call_amount: int) -> None:
        player = self.players[idx]

        if action == "fold":
            player.folded = True
            self.acted_players.add(idx)
            self.messages.append(f"{player.name} folds")
            return

        if action == "raise":
            raise_to = self.current_max_bet + self.big_blind
            additional = raise_to - self.player_bets.get(idx, 0)
            if player.chips >= additional:
                player.chips -= additional
                self.table.pot += additional
                self.player_bets[idx] = raise_to
                self.current_max_bet = raise_to
                self.acted_players.add(idx)
                self.messages.append(f"{player.name} raises to {raise_to}")
                # Rebuild queue so all other active players must re-act
                self.action_queue = [
                    (idx + i) % len(self.players)
                    for i in range(1, len(self.players))
                    if self.players[(idx + i) % len(self.players)].active
                ]
                return
            else:
                action = "call"

        # call / check
        if call_amount <= 0:
            self.messages.append(f"{player.name} checks")
        else:
            amount = min(call_amount, player.chips)
            player.chips -= amount
            self.table.pot += amount
            self.player_bets[idx] = self.player_bets.get(idx, 0) + amount
            self.messages.append(f"{player.name} calls {amount}")

        self.acted_players.add(idx)

    def _bot_action(self, player: Player, call_amount: int) -> str:
        if call_amount == 0:
            return "check"
        if call_amount > player.chips * 0.5:
            return "fold"
        return "call"

    def _advance_phase(self) -> None:
        if self.phase == "pre_flop":
            cards = self.deck.deal(3)
            self.table.community_cards.extend(cards)
            self.phase = "flop"
            self.messages.append(f"-- Flop: {' '.join(str(c) for c in self.table.community_cards)} --")
            self._start_betting_round()
        elif self.phase == "flop":
            card = self.deck.deal(1)
            self.table.community_cards.extend(card)
            self.phase = "turn"
            self.messages.append(f"-- Turn: {self.table.community_cards[-1]} --")
            self._start_betting_round()
        elif self.phase == "turn":
            card = self.deck.deal(1)
            self.table.community_cards.extend(card)
            self.phase = "river"
            self.messages.append(f"-- River: {self.table.community_cards[-1]} --")
            self._start_betting_round()
        elif self.phase == "river":
            self._showdown()

    def _showdown(self) -> None:
        self.phase = "showdown"
        active = [p for p in self.players if p.active]

        if len(active) == 1:
            winner = active[0]
            winner.chips += self.table.pot
            self.messages.append(f"{winner.name} wins {self.table.pot}!")
        else:
            best_player = None
            best_score = None
            for p in active:
                all_cards = p.hole_cards + self.table.community_cards
                if len(all_cards) >= 5:
                    score = self.evaluator.best_rank(all_cards)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_player = p
            if best_player:
                best_player.chips += self.table.pot
                label = best_score.label if best_score else "best hand"
                self.messages.append(f"{best_player.name} wins {self.table.pot} with {label}!")

        self.table.pot = 0
        self.phase = "hand_complete"

    def _end_hand(self) -> None:
        active = [p for p in self.players if p.active]
        if active:
            winner = active[0]
            winner.chips += self.table.pot
            self.messages.append(f"{winner.name} wins {self.table.pot}!")
        self.table.pot = 0
        self.phase = "hand_complete"
