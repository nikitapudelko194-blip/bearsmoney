"""Finite State Machine states for user dialogs."""
from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """
    Main user conversation states.
    """
    # Wallet states
    waiting_for_wallet_address = State()
    waiting_for_withdrawal_amount = State()
    waiting_for_withdrawal_confirmation = State()
    
    # Shop states
    choosing_bear_type = State()
    confirming_bear_purchase = State()
    
    # Upgrade states
    choosing_bear_to_upgrade = State()
    confirming_upgrade = State()
    
    # Quest states
    viewing_quest = State()
    claiming_quest_reward = State()
    
    # Case states
    choosing_case_type = State()
    confirming_case_opening = State()
    
    # Subscription states
    choosing_subscription = State()
    confirming_subscription = State()
    
    # Channel task states
    checking_channel_subscription = State()
    claiming_channel_reward = State()
    
    # Admin states
    admin_setting_coin_rate = State()
    admin_setting_bear_cost = State()
    admin_creating_quest = State()
    admin_configuring_case = State()


class AdminStates(StatesGroup):
    """
    Admin panel states.
    """
    in_admin_menu = State()
    configuring_economy = State()
    managing_quests = State()
    managing_cases = State()
    viewing_statistics = State()
