"""FSM состояния для игры Шпион."""

from aiogram.fsm.state import State, StatesGroup


class SpyGameStates(StatesGroup):
    """Состояния игры Шпион."""
    
    waiting_for_players_count = State()  # Ожидание количества игроков
    waiting_for_spies_count = State()    # Ожидание количества шпионов
    showing_cards = State()              # Показ карт игрокам
    game_in_progress = State()           # Игра идет
    voting = State()                     # Голосование
