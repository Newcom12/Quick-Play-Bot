"""FSM состояния для игры Шпион."""

from aiogram.fsm.state import State, StatesGroup


class SpyGameStates(StatesGroup):
    """Состояния игры Шпион."""
    
    waiting_for_game_selection = State()  # Ожидание выбора игры
    waiting_for_evolution_setting = State()  # Ожидание настройки использования эволюций
    waiting_for_players_count = State()  # Ожидание количества игроков
    waiting_for_spies_count = State()    # Ожидание количества шпионов
    managing_players = State()           # Управление списком игроков (добавление имен)
    waiting_for_player_name = State()    # Ожидание ввода имени игрока
    showing_cards = State()              # Показ карт игрокам
    game_in_progress = State()           # Игра идет
    waiting_for_guess = State()          # Ожидание угадывания темы игры (шпионом)
    voting = State()                     # Голосование
