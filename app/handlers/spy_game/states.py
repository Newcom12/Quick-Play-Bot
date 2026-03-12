"""FSM состояния для игры Шпион."""

from aiogram.fsm.state import State, StatesGroup


class SpyGameStates(StatesGroup):
    """Состояния игры Шпион."""
    
    waiting_for_game_selection = State()  # Ожидание выбора игры
    waiting_for_evolution_setting = State()  # Ожидание настройки использования эволюций
    waiting_for_players_count = State()  # Ожидание количества игроков
    waiting_for_spies_count = State()    # Ожидание количества шпионов
    selecting_players = State()          # Выбор игроков из сохраненных
    waiting_for_player_name_in_game = State()  # Ожидание ввода имени игрока во время игры
    managing_players = State()           # Управление списком игроков (добавление имен) - устарело
    waiting_for_player_name = State()    # Ожидание ввода имени игрока - устарело
    showing_cards = State()              # Показ карт игрокам
    game_in_progress = State()           # Игра идет
    selecting_guessing_player = State()  # Выбор игрока, который угадывает тему
    waiting_for_guess = State()          # Ожидание угадывания темы игры (шпионом)
    voting = State()                     # Голосование
