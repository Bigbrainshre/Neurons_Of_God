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
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_info: the GameInfo object.
        current_state: the PokerState object.

        Returns:
        Your action.
        '''

        strength = self.evaluate_hand(current_state)
        
        if current_state.street == 'auction':
            v = random.uniform(0.5,0.8)
            bid = int(v * current_state.my_chips) + 10
            return ActionBid(bid)



        if current_state.opp_revealed_cards:

            if(current_state.street == 'pre-flop'):
                if current_state.can_act(ActionCheck):
                        return ActionCheck()
                if current_state.can_act(ActionCall):
                    return ActionCall()
                

            board_cards = [eval7.Card(c) for c in current_state.board[:3]]
            revealed_card = eval7.Card(current_state.opp_revealed_cards[0])

            ranks = '23456789TJQKA'
            sumi = 0

            
            five_card_hand = board_cards + [revealed_card]
            avg_strength = self.evaluate_expected_from_cards(five_card_hand)

            # Compare actual hand strength to this average
            if strength < avg_strength and current_state.street != 'pre-flop':
                if current_state.can_act(ActionFold):
                    return ActionFold()

            elif strength >= avg_strength + 500 or current_state.street == 'pre-flop':
                if current_state.street == 'pre-flop':
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionCall):
                        return ActionCall()

                if current_state.can_act(ActionRaise):
                    min_raise, max_raise = current_state.raise_bounds
                    return ActionRaise(int (max_raise))
                
            else:
         
                if current_state.street != 'pre-flop':
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionCall):
                        if current_state.cost_to_call < int (0.25 * current_state.my_chips):
                            return ActionCall()
                        else:
                            return ActionFold()

            return ActionCall()



        else:
        
            if((strength < self.play_threshold) and (current_state.street != 'pre-flop')):
                if current_state.can_act(ActionFold):
                    return ActionFold()

            if(strength >= self.play_threshold - 97 or current_state.street == 'pre-flop'):
                
                if current_state.street == 'pre-flop' :
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionCall):
                        return ActionCall()
                            
                if current_state.can_act(ActionRaise):
                    min_raise, max_raise = current_state.raise_bounds
                    return ActionRaise(int (0.75 * max_raise))
            
                
            
            return ActionCall()



if __name__ == '__main__':
    run_bot(Player(), parse_args())