'''
Simple example pokerbot, written in Python.
'''
from pkbot.actions import ActionFold, ActionCall, ActionCheck, ActionRaise, ActionBid
from pkbot.states import GameInfo, PokerState
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot

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
        # my_bankroll = game_info.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        # # the total number of seconds your bot has left to play this game
        # time_bank = game_info.time_bank
        # round_num = game_info.round_num  # the round number from 1 to NUM_ROUNDS
        
        # # your cards
        # # is an array; eg: ['Ah', 'Kd'] for Ace of hearts and King of diamonds
        # my_cards = current_state.my_hand

        # # opponent's  revealed cards or [] if not revealed
        # opp_revealed_cards = current_state.opp_revealed_cards
        
        # big_blind = current_state.is_bb  # True if you are the big blind
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
        # my_delta = current_state.payoff  # your bankroll change from this round
        
        # street = current_state.street  # 'pre-flop', 'flop', 'auction', 'turn', or 'river'
        # # your cards
        # # is an array; eg: ['Ah', 'Kd'] for Ace of hearts and King of diamonds
        # my_cards = current_state.my_hand

        # # opponent's revealed cards or [] if not revealed
        # opp_revealed_cards = current_state.opp_revealed_cards
        pass

    def get_move(self, game_info: GameInfo, current_state: PokerState):
        """
        Pure all-in bot. Whatever the street or cards, it bets everything.
        """
        # If auction/bidding phase
        if current_state.can_act(ActionBid):
            return ActionBid(current_state.my_chips)
        
        # If normal betting phase
        if current_state.can_act(ActionRaise):
            min_raise, max_raise = current_state.raise_bounds
            return ActionRaise(max_raise)
        
        if current_state.can_act(ActionCall):
            return ActionCall()
        
        if current_state.can_act(ActionCheck):
            return ActionCheck()
        
        # Otherwise, fold (should rarely happen)
        return ActionFold()


if __name__ == '__main__':
    run_bot(Player(), parse_args())