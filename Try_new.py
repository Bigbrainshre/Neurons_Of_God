"""
GPT-Bot candidate — optimized, conservative, and fast.

Key features:
- preflop table (instant)
- adaptive Monte-Carlo equity (flop/turn) with per-hand budget
- SPR-aware push/fold (when stacks are shallow)
- small opponent-aware adjustments (based on recent auction/hands we observe)
- heavy caching (eval7_cached) and string->Card precompute
- conservative pot-aware sizing to increase realized value and reduce catastrophic losses

Drop this file in and run: python engine.py
"""

from pkbot.actions import ActionFold, ActionCall, ActionCheck, ActionRaise, ActionBid
from pkbot.states import GameInfo, PokerState
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot

import eval7
import random
from functools import lru_cache
from typing import List, Tuple

RANK_ORDER = '23456789TJQKA'
SUITS = 'shdc'


# -------------------------
# Cached evaluator (global LRU)
# -------------------------
@lru_cache(maxsize=250_000)
def eval7_cached(cards_tuple: Tuple[str, ...]) -> int:
    """Evaluate a tuple of card strings (sorted canonical order)."""
    return eval7.evaluate([eval7.Card(c) for c in cards_tuple])


# -------------------------
# Utility: canonical tuple (faster than sorting many times)
# -------------------------
def canonical_tuple_from_strings(strs: List[str]) -> Tuple[str, ...]:
    # We create a canonical key by sorting by rank index then suit index.
    # This is deterministic and usually fast (tiny list).
    def key_fn(s):
        return (RANK_ORDER.index(s[0]), SUITS.index(s[1]))
    return tuple(sorted(strs, key=key_fn))


# -------------------------
# Bot Implementation
# -------------------------
class Player(BaseBot):
    def __init__(self) -> None:
        # Preflop buckets: conservative baseline
        self.premium_hands = {"AA", "KK", "QQ", "JJ", "AKs", "AKo"}
        self.strong_hands = {"TT", "99", "AQs", "AJs", "KQs", "AQo"}
        self.playable_hands = {"88", "77", "66", "AJs", "KJs", "QJs", "ATs", "KTs", "QTs", "JTs", "T9s"}

        # baseline numeric strength (used for heuristics)
        threshold_cards = [
            eval7.Card('3s'), eval7.Card('5d'), eval7.Card('4h'), eval7.Card('7c'), eval7.Card('7d')
        ]
        self.play_threshold = eval7.evaluate(threshold_cards)

        # Monte Carlo defaults (conservative)
        self.default_flop_sims = 100
        self.default_turn_sims = 140
        self.min_sims = 20  # absolute minimum when time is tiny

        # per-hand resource budget (counts how many MC sims we've spent this hand)
        self.per_hand_sim_budget = 600  # total sims across decisions per hand
        self._sims_left = self.per_hand_sim_budget

        # caches for speed
        self._eq_cache = {}  # key -> equity
        # prebuild deck strings and card objects
        self._full_deck_strs = [r + s for r in RANK_ORDER for s in SUITS]
        self._str2card = {s: eval7.Card(s) for s in self._full_deck_strs}

        # small rolling history for opponent-aware tweaks
        self.recent_auction_outcomes: List[int] = []  # store our auction payoff deltas (last N)
        self.recent_hand_outcomes: List[int] = []     # store our payoff deltas
        self.history_limit = 200

    # -------------------------
    # Helpers
    # -------------------------
    def get_preflop_key(self, c1: str, c2: str) -> str:
        r1, s1 = c1[0], c1[1]
        r2, s2 = c2[0], c2[1]
        if RANK_ORDER.index(r1) < RANK_ORDER.index(r2):
            r1, r2 = r2, r1
            s1, s2 = s2, s1
        if r1 == r2:
            return r1 + r2
        return r1 + r2 + ('s' if s1 == s2 else 'o')

    def _make_remaining_strs(self, known: List[str]) -> List[str]:
        seen = set(known)
        return [c for c in self._full_deck_strs if c not in seen]

    def _eval_cached_for(self, card_strs: List[str]) -> int:
        key = canonical_tuple_from_strings(card_strs)
        return eval7_cached(key)

    # -------------------------
    # Adaptive Monte Carlo vs random single opponent
    # -------------------------
    def equity_vs_random(self, my_cards: List[str], board_cards: List[str], sims:int, time_bank: float=None) -> float:
        """
        Cheap Monte Carlo: samples opponent hole + board extras from remaining deck.
        Uses self._sims_left budget to avoid excessive per-hand work.
        Uses eval7_cached via canonical keys.
        """
        # clamp sims by remaining budget
        sims = min(sims, max(self.min_sims, self._sims_left))
        if sims <= 0:
            # fallback: coarse estimate via exact evaluation if possible else neutral 0.5
            if len(my_cards) + len(board_cards) >= 5:
                sc = canonical_tuple_from_strings(my_cards + board_cards)
                sc_val = eval7_cached(sc)
                # map ordinal to [0.01,0.99] around baseline
                val = min(0.99, max(0.01, sc_val / (self.play_threshold * 2.5)))
                return val
            return 0.5

        # adapt sims down if time_bank is low
        if time_bank is not None:
            if time_bank < 1.0:
                sims = max(self.min_sims, sims // 4)
            elif time_bank < 3.0:
                sims = max(self.min_sims, sims // 2)

        remaining = self._make_remaining_strs(my_cards + board_cards)
        if not remaining:
            # no unknowns
            if len(my_cards) + len(board_cards) >= 5:
                return self._eval_cached_for(my_cards + board_cards) / (self.play_threshold * 2.5)
            return 0.5

        wins = ties = 0
        need_board = 5 - len(board_cards)
        # use local variables for speed
        rem = remaining
        for _ in range(sims):
            # sample: first two for opp hole, rest for board extras
            sample_count = 2 + max(0, need_board)
            if sample_count >= len(rem):
                sample = rem[:]  # if small deck, use all
            else:
                sample = random.sample(rem, sample_count)
            opp_hole = sample[:2]
            extra_board = sample[2:2+need_board] if need_board > 0 else []
            new_board = board_cards + extra_board
            my_key = canonical_tuple_from_strings(my_cards + new_board)
            opp_key = canonical_tuple_from_strings(list(opp_hole) + new_board)
            my_score = eval7_cached(my_key)
            opp_score = eval7_cached(opp_key)
            if my_score > opp_score:
                wins += 1
            elif my_score == opp_score:
                ties += 1

        # consume budget
        self._sims_left -= sims
        eq = (wins + ties * 0.5) / sims
        return eq

    # -------------------------
    # Auction heuristic (very cheap)
    # -------------------------
    def auction_bid_value(self, current_state: PokerState, sims: int = 48) -> int:
        """
        Safer auction strategy:
        - Lower baseline bids for low/mediocre equity.
        - Mildly boost for good equity, but cap conservatively.
        - Reduce aggression if recent auction outcomes show net losses.
        """
        my_stack = current_state.my_chips
        pot = getattr(current_state, "pot", getattr(current_state, "pot_size", 0))
        cost = current_state.cost_to_call

        my_cards = list(current_state.my_hand)
        board_cards = list(current_state.board)

        # Quick equity estimate (cheap)
        base_sims = max(12, sims // 3)
        eq0 = self.equity_vs_random(my_cards, board_cards, base_sims, time_bank=getattr(current_state, "time_bank", None))

        # Aggression modifier based on recent auction performance.
        # If we've been losing auction payoffs, pull back; if winning steadily, tiny increase.
        aggression = 1.0
        if len(self.recent_auction_outcomes) >= 8:
            recent = self.recent_auction_outcomes[-20:]
            recent_avg = sum(recent) / len(recent)
            if recent_avg < 0:
                aggression *= 0.80   # pull back when auction results are negative
            elif recent_avg < 5:
                aggression *= 0.92   # slightly conservative if small positive/flat
            else:
                aggression *= 1.05   # a small push if doing well

        # Equity bands -> baseline fraction of stack to bid
        if eq0 < 0.52:
            base_frac = 0.05   # play cheap for marginal hands
        elif eq0 < 0.56:
            base_frac = 0.08
        elif eq0 < 0.60:
            base_frac = 0.10
        else:
            base_frac = 0.13   # only the good hands get this

        # Conservative conversion from equity to chip value (was more aggressive before)
        raw_value = eq0 * (pot + cost)
        # weigh stack-fraction more heavily; raw_value contributes but limited
        base_bid = max(int(base_frac * my_stack), int(raw_value * 0.20))

        bid = int(base_bid * aggression)

        # Tighter cap than before to avoid overbidding
        cap = max(5, int(0.12 * my_stack))  # ~12% of stack
        bid = max(3, min(bid, cap))

        return bid

    # -------------------------
    # Hand lifecycle hooks
    # -------------------------
    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        # reset per-hand sims budget
        self._sims_left = self.per_hand_sim_budget
        self._eq_cache.clear()
        return None

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        # store payoff (can be negative)
        try:
            payoff = int(current_state.payoff)
        except Exception:
            payoff = 0
        self.recent_hand_outcomes.append(payoff)
        if len(self.recent_hand_outcomes) > self.history_limit:
            self.recent_hand_outcomes.pop(0)
        # if auction happened and we have any metric (use opp_revealed_cards as proxy)
        if current_state.opp_revealed_cards:
            self.recent_auction_outcomes.append(payoff)
            if len(self.recent_auction_outcomes) > self.history_limit:
                self.recent_auction_outcomes.pop(0)
        return None

    # -------------------------
    # Safe raise helper: clamp to legal bounds
    # -------------------------
    def _safe_raise(self, current_state: PokerState, target: int):
        min_raise, max_raise = current_state.raise_bounds
        amount = max(min_raise, min(int(target), max_raise))
        if current_state.can_act(ActionRaise):
            return ActionRaise(amount)
        if current_state.can_act(ActionCall):
            return ActionCall()
        if current_state.can_act(ActionCheck):
            return ActionCheck()
        return ActionFold()

    # -------------------------
    # SPR helper: approximate stack-to-pot ratio
    # -------------------------
    def _spr(self, current_state: PokerState) -> float:
        pot = getattr(current_state, "pot", getattr(current_state, "pot_size", 0))
        effective_stack = min(current_state.my_chips, current_state.opp_chips if hasattr(current_state, 'opp_chips') else current_state.my_chips)
        if pot <= 0:
            return float('inf')
        return effective_stack / pot

    # -------------------------
    # Core decision function
    # -------------------------
    def get_move(self, game_info: GameInfo, current_state: PokerState):
        street = current_state.street
        pot = getattr(current_state, "pot", getattr(current_state, "pot_size", 0))
        cost = current_state.cost_to_call
        my_stack = current_state.my_chips

        # ---------- AUCTION ----------
        if street == "auction":
            bid = self.auction_bid_value(current_state, sims=48)
            if bid <= 0:
                # conservative exploratory bid
                bid = max(1, int(0.05 * my_stack))
            if current_state.can_act(ActionBid):
                return ActionBid(int(bid))
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            return ActionCall()

        # ---------- PRE-FLOP ----------
        if street == "pre-flop":
            key = self.get_preflop_key(current_state.my_hand[0], current_state.my_hand[1])
            # deep-stack exploit: if we've been winning tiny amounts (many small wins), increase raises slightly
            tweak = 1.0
            if len(self.recent_hand_outcomes) >= 20:
                avg_recent = sum(self.recent_hand_outcomes[-20:]) / 20.0
                if 0 < avg_recent < 10:
                    tweak = 1.05

            if key in self.premium_hands:
                if current_state.can_act(ActionRaise):
                    min_r, max_r = current_state.raise_bounds
                    raise_amt = max(min_r, int(0.60 * max_r * tweak))
                    return ActionRaise(raise_amt)
                if current_state.can_act(ActionCall):
                    return ActionCall()
                return ActionCheck()
            if key in self.strong_hands:
                if current_state.can_act(ActionRaise):
                    min_r, max_r = current_state.raise_bounds
                    raise_amt = max(min_r, int(0.35 * max_r * tweak))
                    return ActionRaise(raise_amt)
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if current_state.can_act(ActionCall):
                    return ActionCall()
            if key in self.playable_hands:
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if current_state.can_act(ActionCall):
                    if cost <= 0.08 * my_stack:
                        return ActionCall()
                    return ActionFold()
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if current_state.can_act(ActionFold):
                return ActionFold()
            if current_state.can_act(ActionCall):
                return ActionCall()
            return ActionFold()

        # ---------- POST-FLOP (flop/turn/river) ----------
        my_cards = list(current_state.my_hand)
        board_cards = list(current_state.board)
        time_bank = getattr(game_info, "time_bank", None)

        # SPR check for push/fold (aggressive but necessary when stacks are shallow)
        spr_val = self._spr(current_state)
        # compute equity
        if street == "flop":
            sims = self.default_flop_sims
            eq = self.equity_vs_random(my_cards, board_cards, sims, time_bank=time_bank)
        elif street == "turn":
            sims = self.default_turn_sims
            eq = self.equity_vs_random(my_cards, board_cards, sims, time_bank=time_bank)
        else:  # river
            # exact ordinal scaled
            sc = canonical_tuple_from_strings(my_cards + board_cards)
            my_score = eval7_cached(sc)
            eq = min(0.99, max(0.01, my_score / (self.play_threshold * 2.5)))

        # SPR push/fold rule: if SPR very low, push (all-in raise) when equity decent
        if spr_val <= 2.0:
            # conservative thresholds
            if eq >= 0.62 and current_state.can_act(ActionRaise):
                # shove = max legal raise (we expect this to be near all-in in many rulesets)
                min_r, max_r = current_state.raise_bounds
                return ActionRaise(max_r)
            if eq >= 0.50 and current_state.can_act(ActionCall):
                return ActionCall()
            if current_state.can_act(ActionFold):
                return ActionFold()

        # Pot odds basis
        effective_pot = pot + cost if (pot + cost) > 0 else 1.0
        pot_odds = cost / effective_pot
        margin = 0.03

        if eq + margin < pot_odds:
            if current_state.can_act(ActionFold):
                return ActionFold()
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            return ActionCall()

        # advantage metric (eq - 0.5)
        advantage = eq - 0.5

        # raise sizing scaled down a bit from aggressive version (value extraction but safer)
        if advantage > 0.28 and current_state.can_act(ActionRaise):
            if advantage > 0.42:
                target = int(0.9 * pot)
            elif advantage > 0.33:
                target = int(0.6 * pot)
            else:
                target = int(0.40 * pot)
            return self._safe_raise(current_state, target)

        if advantage > 0.08:
            if current_state.can_act(ActionCall):
                return ActionCall()
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            return ActionFold()

        # default conservative play
        if current_state.can_act(ActionCheck):
            return ActionCheck()
        if current_state.can_act(ActionCall):
            if cost <= 0.08 * my_stack:
                return ActionCall()
            if current_state.can_act(ActionFold):
                return ActionFold()
            return ActionCall()

        return ActionFold()


if __name__ == "__main__":
    run_bot(Player(), parse_args())