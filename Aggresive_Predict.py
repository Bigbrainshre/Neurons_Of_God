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

        Arguments:
        Nothing.

        '''

        # Define threshold hand: Two Pair (7s and 3s)
        threshold_cards = [
            eval7.Card('3s'),
            eval7.Card('5d'),
            eval7.Card('4h'),
            eval7.Card('7c'),
            eval7.Card('7d')
        ]

        

        # Numeric strength of threshold
        self.play_threshold = eval7.evaluate(threshold_cards)
        # self.play_threshold = 500

        '''
        Returns:
        Nothing.
        '''
        pass

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_info: the GameInfo object.
        current_state: the PokerState object.

        Returns:
        Nothing.
        '''
        my_bankroll = game_info.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        # the total number of seconds your bot has left to play this game
        time_bank = game_info.time_bank
        round_num = game_info.round_num  # the round number from 1 to NUM_ROUNDS
        
        # your cards
        # is an array; eg: ['Ah', 'Kd'] for Ace of hearts and King of diamonds
        my_cards = current_state.my_hand

        # opponent's  revealed cards or [] if not revealed
        opp_revealed_cards = current_state.opp_revealed_cards
        
        big_blind = current_state.is_bb  # True if you are the big blind
        pass

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_info: the GameInfo object.
        current_state: the PokerState object.

        Returns:
        Nothing.
        '''
        my_delta = current_state.payoff  # your bankroll change from this round
        
        street = current_state.street  # 'pre-flop', 'flop', 'auction', 'turn', or 'river'
        # your cards
        # is an array; eg: ['Ah', 'Kd'] for Ace of hearts and King of diamonds
        my_cards = current_state.my_hand

        # opponent's revealed cards or [] if not revealed
        opp_revealed_cards = current_state.opp_revealed_cards


    def evaluate_expected_from_cards(self, known_cards: list[eval7.Card]) -> float:
        """
        Takes a list of eval7.Card objects.
        Completes to 7 cards using rank iteration.
        """

        total_known = len(known_cards)

        if total_known >= 7:
            return eval7.evaluate(known_cards)

        missing = 7 - total_known
        ranks = '23456789TJQKA'

        rank_count = {r: 0 for r in ranks}
        for card in known_cards:
            rank_count[str(card)[0]] += 1

        rank_cards = {r: eval7.Card(r + 's') for r in ranks}

        total = 0
        count = 0

        if missing == 1:
            for r1 in ranks:
                if rank_count[r1] >= 4:
                    continue
                total += eval7.evaluate(known_cards + [rank_cards[r1]])
                count += 1

        elif missing == 2:
            for r1 in ranks:
                if rank_count[r1] >= 4:
                    continue
                rank_count[r1] += 1
                for r2 in ranks:
                    if rank_count[r2] >= 4:
                        continue
                    total += eval7.evaluate(known_cards + [rank_cards[r1], rank_cards[r2]])
                    count += 1
                rank_count[r1] -= 1

        elif missing == 3:
            for r1 in ranks:
                if rank_count[r1] >= 4:
                    continue
                rank_count[r1] += 1
                for r2 in ranks:
                    if rank_count[r2] >= 4:
                        continue
                    rank_count[r2] += 1
                    for r3 in ranks:
                        if rank_count[r3] >= 4:
                            continue
                        total += eval7.evaluate(
                            known_cards + [rank_cards[r1], rank_cards[r2], rank_cards[r3]]
                        )
                        count += 1
                    rank_count[r2] -= 1
                rank_count[r1] -= 1

        return total / count if count else 0


    def evaluate_hand(self, current_state: PokerState) -> float:
            """
            Deterministic expected strength.
            Respects max 4 cards per rank.
            Assumes at most 3 cards missing.
            """

            known_cards = [eval7.Card(c) for c in current_state.my_hand] + \
                        [eval7.Card(c) for c in current_state.board]

            total_known = len(known_cards)

            if total_known >= 7:
                return eval7.evaluate(known_cards)

            missing = 7 - total_known
            ranks = '23456789TJQKA'

            # Count rank usage
            rank_count = {r: 0 for r in ranks}
            for card in known_cards:
                rank_count[str(card)[0]] += 1

            rank_cards = {r: eval7.Card(r + 's') for r in ranks}

            total = 0
            count = 0

            if missing == 1:
                for r1 in ranks:
                    if rank_count[r1] >= 4:
                        continue

                    total += eval7.evaluate(known_cards + [rank_cards[r1]])
                    count += 1

            elif missing == 2:
                for r1 in ranks:
                    if rank_count[r1] >= 4:
                        continue

                    rank_count[r1] += 1

                    for r2 in ranks:
                        if rank_count[r2] >= 4:
                            continue

                        total += eval7.evaluate(
                            known_cards + [rank_cards[r1], rank_cards[r2]]
                        )
                        count += 1

                    rank_count[r1] -= 1

            elif missing == 3:
                for r1 in ranks:
                    if rank_count[r1] >= 4:
                        continue

                    rank_count[r1] += 1

                    for r2 in ranks:
                        if rank_count[r2] >= 4:
                            continue

                        rank_count[r2] += 1

                        for r3 in ranks:
                            if rank_count[r3] >= 4:
                                continue

                            total += eval7.evaluate(
                                known_cards + [
                                    rank_cards[r1],
                                    rank_cards[r2],
                                    rank_cards[r3],
                                ]
                            )
                            count += 1

                        rank_count[r2] -= 1

                    rank_count[r1] -= 1

            else:
                return 0

            return total / count if count > 0 else 0
    

    def get_move(self, game_info: GameInfo, current_state: PokerState) -> ActionFold | ActionCall | ActionCheck | ActionRaise | ActionBid:
            """
            Tuned version:
            - Controlled aggression
            - Requires solid edge before raising
            - Smaller scaling factor
            - Much less spew
            """

            strength = self.evaluate_hand(current_state)

            # ---------------- AUCTION PHASE ----------------
            if current_state.street == 'auction':
                # Much more conservative bidding
                bid = int(0.35 * current_state.my_chips)
                return ActionBid(bid)

            # ---------------- WHEN OPPONENT CARD IS REVEALED ----------------
            if current_state.opp_revealed_cards:

                # Pre-flop → keep simple
                if current_state.street == 'pre-flop':
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionCall):
                        return ActionCall()

                # Baseline average strength
                board_cards = [eval7.Card(c) for c in current_state.board[:3]]
                revealed_card = eval7.Card(current_state.opp_revealed_cards[0])

                five_card_hand = board_cards + [revealed_card]
                avg_strength = self.evaluate_expected_from_cards(five_card_hand)

                advantage = strength - avg_strength

                # Clear weakness → fold only if significantly behind
                if advantage < -400:
                    if current_state.can_act(ActionFold):
                        return ActionFold()
                    return ActionCall()

                # Only raise if clearly ahead
                if advantage > 600 and current_state.can_act(ActionRaise):
                    min_raise, max_raise = current_state.raise_bounds

                    # Much smaller scaling
                    scale = min((advantage - 600) / 2500, 1)
                    raise_amount = int(min_raise + scale * (max_raise - min_raise) * 0.5)

                    return ActionRaise(raise_amount)

                # Otherwise just call
                if current_state.can_act(ActionCall):
                    return ActionCall()

                return ActionCheck()

            # ---------------- NORMAL PLAY (NO REVEAL) ----------------

            # Pre-flop
            if current_state.street == 'pre-flop':

                advantage = strength - self.play_threshold

                # Raise only with real edge
                if advantage > 800 and current_state.can_act(ActionRaise):
                    min_raise, max_raise = current_state.raise_bounds
                    scale = min((advantage - 800) / 3000, 1)
                    raise_amount = int(min_raise + scale * (max_raise - min_raise) * 0.4)
                    return ActionRaise(raise_amount)

                if current_state.can_act(ActionCall):
                    return ActionCall()

                return ActionCheck()

            # Post-flop
            advantage = strength - self.play_threshold

            # Only fold if clearly weak
            if advantage < -800:
                if current_state.can_act(ActionFold):
                    return ActionFold()
                return ActionCall()

            # Raise only when convincingly ahead
            if advantage > 1000 and current_state.can_act(ActionRaise):
                min_raise, max_raise = current_state.raise_bounds
                scale = min((advantage - 1000) / 3000, 1)
                raise_amount = int(min_raise + scale * (max_raise - min_raise) * 0.4)
                return ActionRaise(raise_amount)

            # Otherwise call
            if current_state.can_act(ActionCall):
                return ActionCall()

            return ActionCheck()



if __name__ == '__main__':
    run_bot(Player(), parse_args())