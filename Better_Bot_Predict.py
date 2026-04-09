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


    def evaluate_hand(self, current_state: PokerState) -> int:
        """
        Returns integer strength of current hand using eval7.
        Higher value = stronger hand.
        """

        hole = [eval7.Card(card) for card in current_state.my_hand]
        board = [eval7.Card(card) for card in current_state.board]

        # Need at least 5 total cards to evaluate
        if len(hole) + len(board) < 5:
            return 0

        return eval7.evaluate(hole + board)
    

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
            v = random.uniform(0.2,0.4)
            bid = max(1, int(v * game_info.bankroll))
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

            for r in ranks:
                last_card = eval7.Card(r + 's')  # suit doesn't matter
                five_card_hand = board_cards + [revealed_card, last_card]
                sumi = sumi + eval7.evaluate(five_card_hand)

            avg_strength = sumi / 13

            # Compare actual hand strength to this average
            if strength < avg_strength and current_state.street != 'pre-flop':
                if current_state.can_act(ActionFold):
                    return ActionFold()

            elif strength >= avg_strength + 600 or current_state.street == 'pre-flop':
                if current_state.street == 'pre-flop':
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionCall):
                        return ActionCall()

                if current_state.can_act(ActionRaise):
                    min_raise, max_raise = current_state.raise_bounds
                    return ActionRaise(int (max_raise))
                
            else:
                
                ratio = 1 - (((avg_strength + 600) - strength)/600)

                if current_state.street != 'pre-flop':
                    if current_state.can_act(ActionCheck):
                        return ActionCheck()
                    if current_state.can_act(ActionCall):
                        if current_state.cost_to_call < int (0.75 * ratio * current_state.my_chips):
                            return ActionCall()
                        else:
                            return ActionFold()

            return ActionCall()



        else:
        
            if((strength < self.play_threshold) and (current_state.street != 'pre-flop')):
                if current_state.can_act(ActionFold):
                    return ActionFold()

            if(strength >= self.play_threshold or current_state.street == 'pre-flop'):
                
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