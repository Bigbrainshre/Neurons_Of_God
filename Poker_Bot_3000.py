'''
Simple example pokerbot, written in Python.
'''
from pkbot.actions import ActionFold, ActionCall, ActionCheck, ActionRaise, ActionBid
from pkbot.states import GameInfo, PokerState
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot
import eval7
import random


class Player(BaseBot):
    '''
    A pokerbot.
    '''

    def __init__(self) -> None:
        '''
        Called when a new game starts. Called exactly once.
        '''

        # PREMIUM hands — raise large (60% of max raise)
        self.premium_hands = {
            ('A', 'A', False),
            ('K', 'K', False),
            ('Q', 'Q', False),
            ('J', 'J', False),
            ('A', 'K', False),
        }

        # STRONG hands — raise medium (35% of max raise)
        self.strong_hands = {
            ('T', 'T', False),
            ('9', '9', False),
            ('A', 'Q', False),
            ('A', 'J', True),
            ('A', 'T', True),
            ('K', 'Q', False),
        }

        # PLAYABLE hands — call (no raise)
        self.playable_hands = {
            ('8', '8', False),
            ('7', '7', False),
            ('6', '6', False),
            ('5', '5', False),
            ('4', '4', False),
            ('3', '3', False),
            ('2', '2', False),
            ('A', '9', True),
            ('A', '8', True),
            ('A', '7', True),
            ('A', '6', True),
            ('A', '5', True),
            ('A', '4', True),
            ('A', '3', True),
            ('A', '2', True),
            ('K', 'J', True),
            ('K', 'T', True),
            ('Q', 'J', True),
            ('J', 'T', True),
            ('T', '9', True),
            ('9', '8', True),
            ('8', '7', True),
        }

        # Bucket rank ordering (strongest → weakest)
        # open_ended (1.5) sits between weak_pair (1) and high_pair (3)
        self.BUCKET_VALUE = {
            'monster':     5,
            'flush_draw':  4,
            'high_pair':   3,
            'open_ended':  1.5,
            'gutshot':     1,
            'weak_pair':   1,
            'air':         0,
        }

        # Define threshold hand for post-flop
        threshold_cards = [
            eval7.Card('3s'),
            eval7.Card('5d'),
            eval7.Card('4h'),
            eval7.Card('7c'),
            eval7.Card('7d')
        ]
        self.play_threshold = eval7.evaluate(threshold_cards)

        pass

    def _safe_raise(self, current_state, fraction, use_pot=False):
        """
        Calculates and returns a legal raise action.

        If use_pot=True  → fraction is applied to current pot size (pot-based sizing)
        If use_pot=False → fraction is applied to max_raise (stack-based sizing, preflop only)

        Always clamps between min_raise and max_raise.
        Falls back to ActionCall if raise is not possible.
        """
        min_raise, max_raise = current_state.raise_bounds

        if use_pot:
            desired = int(fraction * current_state.pot)
        else:
            desired = int(fraction * max_raise)

        if desired < min_raise:
            return ActionCall()

        amount = min(desired, max_raise)

        if current_state.can_act(ActionRaise):
            return ActionRaise(amount)

        return ActionCall()

    # =========================================================================
    # OPPONENT HAND EVALUATION — REVEALED CARD LOGIC
    # =========================================================================

    def estimate_opp_flop_bucket(self, current_state: PokerState) -> str:
        """
        Estimates the opponent's flop bucket given one revealed hole card.
        Iterates all ~46 remaining cards as candidate second hole card,
        tallies bucket counts, returns most frequent (ties broken by BUCKET_VALUE).
        """
        revealed_card = current_state.opp_revealed_cards[0]
        flop_cards    = current_state.board[:3]

        seen = set(current_state.my_hand) | set(flop_cards) | {revealed_card}

        ranks     = '23456789TJQKA'
        suits     = 'shdc'
        full_deck = [r + s for r in ranks for s in suits]
        remaining = [c for c in full_deck if c not in seen]

        bucket_counts = {b: 0 for b in self.BUCKET_VALUE}

        class _MockState:
            pass

        mock = _MockState()
        mock.board = flop_cards

        for candidate in remaining:
            mock.my_hand = [revealed_card, candidate]
            bucket = self.evaluate_flop_bucket(mock)
            bucket_counts[bucket] += 1

        best_bucket = max(
            bucket_counts,
            key=lambda b: (bucket_counts[b], self.BUCKET_VALUE[b])
        )
        return best_bucket

    def estimate_opp_turn_strength(self, current_state: PokerState) -> float:
        """
        Estimates opponent's turn strength by mapping their flop bucket
        onto the play_threshold numeric scale.
        monster → ~2x play_threshold, air → 0.
        """
        SCALE_FACTOR = 2.0

        opp_bucket     = self.estimate_opp_flop_bucket(current_state)
        bucket_val     = self.BUCKET_VALUE[opp_bucket]
        opp_turn_score = (bucket_val / 5.0) * self.play_threshold * SCALE_FACTOR
        return opp_turn_score

    def estimate_opp_river_strength(self, current_state: PokerState) -> float:
        """
        Estimates opponent's river strength by averaging eval7 score
        across all ~44 possible second hole cards.
        """
        revealed_card = eval7.Card(current_state.opp_revealed_cards[0])
        board         = [eval7.Card(c) for c in current_state.board]

        seen = set(current_state.my_hand) | set(current_state.board) | {str(revealed_card)}

        ranks     = '23456789TJQKA'
        suits     = 'shdc'
        full_deck = [eval7.Card(r + s) for r in ranks for s in suits]
        remaining = [c for c in full_deck if str(c) not in seen]

        total = sum(
            eval7.evaluate([revealed_card, candidate] + board)
            for candidate in remaining
        )
        return total / len(remaining)

    # =========================================================================
    # END OPPONENT EVALUATION
    # =========================================================================

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        my_bankroll          = game_info.bankroll
        time_bank            = game_info.time_bank
        round_num            = game_info.round_num
        my_cards             = current_state.my_hand
        opp_revealed_cards   = current_state.opp_revealed_cards
        big_blind            = current_state.is_bb
        pass

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        my_delta           = current_state.payoff
        street             = current_state.street
        my_cards           = current_state.my_hand
        opp_revealed_cards = current_state.opp_revealed_cards

    def evaluate_hand(self, current_state: PokerState) -> int:
        """
        Returns integer strength of current hand using eval7.
        Higher value = stronger hand.
        """
        hole  = [eval7.Card(card) for card in current_state.my_hand]
        board = [eval7.Card(card) for card in current_state.board]
        if len(hole) + len(board) < 5:
            return 0
        return eval7.evaluate(hole + board)

    def evaluate_turn_equity(self, current_state: PokerState, skip_card: str = None) -> float:
        """
        TURN equity approximation.
        For each possible river card, evaluates full hand with hole card
        contribution multiplier applied.
        Returns average adjusted score.
        """
        hole  = [eval7.Card(c) for c in current_state.my_hand]
        board = [eval7.Card(c) for c in current_state.board]

        seen = set(str(c) for c in hole + board)
        if skip_card:
            seen.add(skip_card)

        ranks     = '23456789TJQKA'
        suits     = 'shdc'
        full_deck = [eval7.Card(r + s) for r in ranks for s in suits]
        remaining = [c for c in full_deck if str(c) not in seen]

        total = 0

        for river_card in remaining:
            full_board = board + [river_card]
            full_hand  = hole + full_board
            raw_score  = eval7.evaluate(full_hand)

            use_count       = 0
            best_full_score = raw_score

            for i in range(2):
                test_hand  = [hole[1 - i]] + full_board
                test_score = eval7.evaluate(test_hand)
                if test_score < best_full_score:
                    use_count += 1

            if use_count == 2:
                multiplier = 1.25
            elif use_count == 1:
                multiplier = 1.10
            else:
                multiplier = 0.90

            total += raw_score * multiplier

        return total / len(remaining)

    def evaluate_flop_bucket(self, current_state) -> str:
        """
        Evaluates hand strength on the flop and returns a bucket string.
        Buckets: monster, flush_draw, high_pair, open_ended, gutshot, weak_pair, air
        """
        FACE_RANKS = {'T', 'J', 'Q', 'K', 'A'}
        RANK_ORDER = '23456789TJQKA'

        hole        = current_state.my_hand
        board       = current_state.board[:3]

        hole_ranks  = [c[0] for c in hole]
        hole_suits  = [c[1] for c in hole]
        board_ranks = [c[0] for c in board]
        board_suits = [c[1] for c in board]

        all_ranks   = hole_ranks + board_ranks
        all_suits   = hole_suits + board_suits

        rank_counts = {}
        for r in all_ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1

        # ── MONSTER ──────────────────────────────────────────────────────────

        # Set (three of a kind using a hole card)
        for r in hole_ranks:
            if rank_counts[r] == 3:
                return 'monster'

        # Two pair using both hole cards
        if hole_ranks[0] != hole_ranks[1]:
            if rank_counts[hole_ranks[0]] == 2 and rank_counts[hole_ranks[1]] == 2:
                return 'monster'

        # Overpair (pocket pair higher than all board cards)
        if hole_ranks[0] == hole_ranks[1]:
            highest_board = max(board_ranks, key=lambda r: RANK_ORDER.index(r))
            if RANK_ORDER.index(hole_ranks[0]) > RANK_ORDER.index(highest_board):
                return 'monster'

        # ── HIGH PAIR ────────────────────────────────────────────────────────

        highest_board = max(board_ranks, key=lambda r: RANK_ORDER.index(r))
        if highest_board in hole_ranks:
            if any(r in FACE_RANKS for r in hole_ranks):
                return 'high_pair'
            return 'weak_pair'

        # ── FLUSH DRAW ───────────────────────────────────────────────────────

        suit_counts = {}
        for s in all_suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        if any(v == 4 for v in suit_counts.values()):
            return 'flush_draw'

        # ── STRAIGHT DRAWS ───────────────────────────────────────────────────

        rank_values = sorted(set(RANK_ORDER.index(r) for r in all_ranks))
        rank_value_set = set(rank_values)

        for low in range(9):
            window = set(range(low, low + 5))
            hits   = len(window & rank_value_set)
            gaps   = window - rank_value_set

            if hits == 4:
                # Open-ended: gap must be at one of the two ends of the window
                if min(gaps) == low or max(gaps) == low + 4:
                    return 'open_ended'
                else:
                    return 'gutshot'

        # ── WEAK PAIR ────────────────────────────────────────────────────────

        for r in hole_ranks:
            if rank_counts[r] == 2:
                return 'weak_pair'

        return 'air'

    def classify_preflop_hand(self, current_state: PokerState) -> str:
        """
        Classifies hole cards into 'premium', 'strong', 'playable', or 'fold'.
        """
        card1, card2 = current_state.my_hand[0], current_state.my_hand[1]
        rank1, suit1 = card1[0], card1[1]
        rank2, suit2 = card2[0], card2[1]
        suited       = (suit1 == suit2)

        rank_order = 'AKQJT98765432'
        if rank_order.index(rank1) > rank_order.index(rank2):
            rank1, rank2 = rank2, rank1

        def matches(tier_set):
            if (rank1, rank2, False) in tier_set:
                return True
            if suited and (rank1, rank2, True) in tier_set:
                return True
            return False

        if matches(self.premium_hands):
            return 'premium'
        if matches(self.strong_hands):
            return 'strong'
        if matches(self.playable_hands):
            return 'playable'
        return 'fold'

    def get_move(self, game_info: GameInfo, current_state: PokerState) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:
        '''
        Central dispatcher — routes every street to its dedicated handler.
        '''

        # ── AUCTION ───────────────────────────────────────────────────────────
        if current_state.street == 'auction':
            tier = self.classify_preflop_hand(current_state)

            if tier == 'premium':
                v = random.uniform(0.15, 0.20)
            elif tier == 'strong':
                v = random.uniform(0.15, 0.20)
            elif tier == 'playable':
                v = random.uniform(0.08, 0.12)
            else:
                v = random.uniform(0.04, 0.07)

            bid = max(10, int(v * current_state.my_chips))
            return ActionBid(bid)

        # ── STREET DISPATCH ───────────────────────────────────────────────────
        if current_state.street == 'pre-flop':
            return self._handle_preflop(current_state)

        if current_state.street == 'flop':
            return self._handle_flop(current_state)

        if current_state.street == 'turn':
            return self._handle_turn(current_state)

        if current_state.street == 'river':
            return self._handle_river(current_state)

        return ActionCall()

    def _handle_flop(self, current_state: PokerState):
        """
        Flop logic. Uses pot-based raise sizing.
        """
        my_chips = current_state.my_chips
        cost     = current_state.cost_to_call

        # ── REVEALED CARD BRANCH ──────────────────────────────────────────────
        if current_state.opp_revealed_cards:
            our_bucket = self.evaluate_flop_bucket(current_state)
            opp_bucket = self.estimate_opp_flop_bucket(current_state)

            our_val = self.BUCKET_VALUE[our_bucket]
            opp_val = self.BUCKET_VALUE[opp_bucket]

            abs_raise_fraction = our_val / 5.0

            # ── OPP HAS AIR ───────────────────────────────────────────────────
            if opp_bucket == 'air':
                if our_val >= 2:
                    if current_state.can_act(ActionRaise):
                        return self._safe_raise(current_state, abs_raise_fraction, use_pot=True)
                    return ActionCall()
                elif our_val == 1:
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if cost <= 0.15 * my_chips:
                        return ActionCall()
                    return ActionFold()
                else:
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionFold):
                        return ActionFold()
                    return ActionCall()

            # ── OPP HAS A REAL HAND ───────────────────────────────────────────
            ratio = our_val / opp_val

            if ratio > 1.5:
                if our_val >= 2 and current_state.can_act(ActionRaise):
                    return self._safe_raise(current_state, abs_raise_fraction, use_pot=True)
                return ActionCall()
            elif ratio > 1.1:
                if our_val >= 2 and current_state.can_act(ActionRaise):
                    return self._safe_raise(current_state, abs_raise_fraction * 0.6, use_pot=True)
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if cost <= 0.20 * my_chips:
                    return ActionCall()
                return ActionFold()
            elif ratio >= 0.9:
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if cost <= 0.15 * my_chips:
                    return ActionCall()
                return ActionFold()
            else:
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if current_state.can_act(ActionFold):
                    return ActionFold()
                return ActionCall()

        # ── NO REVEALED CARD BRANCH ───────────────────────────────────────────
        bucket = self.evaluate_flop_bucket(current_state)

        if bucket == 'monster':
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.70, use_pot=True)
            return ActionCall()

        elif bucket == 'flush_draw':
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.40, use_pot=True)
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.50 * my_chips:
                return ActionCall()
            return ActionFold()

        elif bucket == 'high_pair':
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.35, use_pot=True)
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.20 * my_chips:
                return ActionCall()
            return ActionFold()

        elif bucket == 'open_ended':
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.30, use_pot=True)
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.15 * my_chips:
                return ActionCall()
            return ActionFold()

        elif bucket == 'gutshot':
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.15, use_pot=True)
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.10 * my_chips:
                return ActionCall()
            return ActionFold()

        elif bucket == 'weak_pair':
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.15 * my_chips:
                return ActionCall()
            return ActionFold()

        else:  # air
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if current_state.can_act(ActionFold):
                return ActionFold()
            return ActionCall()

    def _handle_turn(self, current_state: PokerState):
        """
        Turn logic. Uses pot-based raise sizing.
        """
        my_chips = current_state.my_chips
        cost     = current_state.cost_to_call

        # ── REVEALED CARD BRANCH ──────────────────────────────────────────────
        if current_state.opp_revealed_cards:
            our_score = self.evaluate_turn_equity(current_state)
            opp_score = self.estimate_opp_turn_strength(current_state)

            abs_raise_fraction = min(1.0, max(0.0, (our_score - self.play_threshold) / self.play_threshold))
            we_have_something  = our_score >= 0.8 * self.play_threshold

            if opp_score == 0:
                if abs_raise_fraction > 0:
                    if current_state.can_act(ActionRaise):
                        return self._safe_raise(current_state, abs_raise_fraction, use_pot=True)
                    return ActionCall()
                elif we_have_something:
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if cost <= 0.15 * my_chips:
                        return ActionCall()
                    return ActionFold()
                else:
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionFold):
                        return ActionFold()
                    return ActionCall()

            ratio = our_score / opp_score

            if ratio > 1.5:
                if abs_raise_fraction > 0 and current_state.can_act(ActionRaise):
                    return self._safe_raise(current_state, abs_raise_fraction, use_pot=True)
                return ActionCall()
            elif ratio > 1.1:
                if abs_raise_fraction > 0 and current_state.can_act(ActionRaise):
                    return self._safe_raise(current_state, abs_raise_fraction * 0.6, use_pot=True)
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if cost <= 0.20 * my_chips:
                    return ActionCall()
                return ActionFold()
            elif ratio >= 0.9:
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if cost <= 0.15 * my_chips:
                    return ActionCall()
                return ActionFold()
            else:
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if current_state.can_act(ActionFold):
                    return ActionFold()
                return ActionCall()

        # ── NO REVEALED CARD BRANCH ───────────────────────────────────────────
        avg_score = self.evaluate_turn_equity(current_state)

        if avg_score >= 1.4 * self.play_threshold:
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.65, use_pot=True)
            return ActionCall()

        elif avg_score >= self.play_threshold:
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.35, use_pot=True)
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.20 * my_chips:
                return ActionCall()
            return ActionFold()

        elif avg_score >= 0.8 * self.play_threshold:
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.15 * my_chips:
                return ActionCall()
            return ActionFold()

        else:
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if current_state.can_act(ActionFold):
                return ActionFold()
            return ActionCall()

    def _handle_river(self, current_state: PokerState):
        """
        River logic. Uses pot-based raise sizing.
        Hole card contribution multiplier applied in no-revealed branch.
        """
        my_chips = current_state.my_chips
        cost     = current_state.cost_to_call

        # ── REVEALED CARD BRANCH ──────────────────────────────────────────────
        if current_state.opp_revealed_cards:
            our_score = self.evaluate_hand(current_state)
            opp_score = self.estimate_opp_river_strength(current_state)

            abs_raise_fraction = min(1.0, max(0.0, (our_score - self.play_threshold) / self.play_threshold))
            we_have_something  = our_score >= 0.8 * self.play_threshold

            if opp_score == 0:
                if abs_raise_fraction > 0:
                    if current_state.can_act(ActionRaise):
                        return self._safe_raise(current_state, abs_raise_fraction, use_pot=True)
                    return ActionCall()
                elif we_have_something:
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if cost <= 0.15 * my_chips:
                        return ActionCall()
                    return ActionFold()
                else:
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionFold):
                        return ActionFold()
                    return ActionCall()

            ratio = our_score / opp_score

            if ratio > 1.5:
                if abs_raise_fraction > 0 and current_state.can_act(ActionRaise):
                    return self._safe_raise(current_state, abs_raise_fraction, use_pot=True)
                return ActionCall()
            elif ratio > 1.1:
                if abs_raise_fraction > 0 and current_state.can_act(ActionRaise):
                    return self._safe_raise(current_state, abs_raise_fraction * 0.6, use_pot=True)
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if cost <= 0.20 * my_chips:
                    return ActionCall()
                return ActionFold()
            elif ratio >= 0.9:
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if cost <= 0.15 * my_chips:
                    return ActionCall()
                return ActionFold()
            else:
                if current_state.can_act(ActionCheck):
                    return ActionCheck()
                if current_state.can_act(ActionFold):
                    return ActionFold()
                return ActionCall()

        # ── NO REVEALED CARD BRANCH ───────────────────────────────────────────
        hole  = [eval7.Card(c) for c in current_state.my_hand]
        board = [eval7.Card(c) for c in current_state.board]

        full_hand       = hole + board
        raw_score       = eval7.evaluate(full_hand)
        best_full_score = raw_score
        use_count       = 0

        for i in range(2):
            test_score = eval7.evaluate([hole[1 - i]] + board)
            if test_score < best_full_score:
                use_count += 1

        if use_count == 2:
            multiplier = 1.25
        elif use_count == 1:
            multiplier = 1.10
        else:
            multiplier = 0.90

        score = raw_score * multiplier

        if score >= self.play_threshold * 1.4:
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.60, use_pot=True)
            return ActionCall()

        elif score >= self.play_threshold:
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.30, use_pot=True)
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.20 * my_chips:
                return ActionCall()
            return ActionFold()

        else:
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= 0.10 * my_chips:
                return ActionCall()
            if current_state.can_act(ActionFold):
                return ActionFold()
            return ActionCall()

    def _handle_preflop(self, current_state: PokerState):
        """
        Pre-flop logic. Uses stack-based raise sizing (pot too small to be meaningful).
        """
        tier     = self.classify_preflop_hand(current_state)
        my_chips = current_state.my_chips
        cost     = current_state.cost_to_call

        SNAP_CALL_LIMIT  = 0.20 * my_chips
        CHEAP_CALL_LIMIT = 0.05 * my_chips

        if tier == 'premium':
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.60)
            return ActionCall()

        elif tier == 'strong':
            if current_state.can_act(ActionRaise):
                return self._safe_raise(current_state, 0.35)
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= SNAP_CALL_LIMIT:
                return ActionCall()
            return ActionFold()

        elif tier == 'playable':
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= SNAP_CALL_LIMIT:
                return ActionCall()
            return ActionFold()

        else:
            if current_state.can_act(ActionCheck):
                return ActionCheck()
            if cost <= CHEAP_CALL_LIMIT:
                return ActionCall()
            if current_state.can_act(ActionFold):
                return ActionFold()
            return ActionCall()


if __name__ == '__main__':
    run_bot(Player(), parse_args())