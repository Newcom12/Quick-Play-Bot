"""Менеджер игры Шпион."""

import asyncio
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class Player:
    """Игрок в игре."""
    user_id: int
    username: str
    is_spy: bool
    card_name: Optional[str] = None
    file_id: Optional[str] = None
    has_seen_card: bool = False


@dataclass
class Game:
    """Игра Шпион."""
    game_id: str
    creator_id: int
    players: List[Player] = field(default_factory=list)
    players_count: int = 0
    spies_count: int = 0
    current_player_index: int = 0
    timer_task: Optional[asyncio.Task] = None
    timer_message_id: Optional[int] = None
    timer_chat_id: Optional[int] = None
    is_active: bool = False
    votes: Dict[int, int] = field(default_factory=dict)  # user_id -> voted_for_user_id
    
    def get_current_player(self) -> Optional[Player]:
        """Возвращает текущего игрока."""
        if self.current_player_index < len(self.players):
            return self.players[self.current_player_index]
        return None
    
    def next_player(self) -> Optional[Player]:
        """Переходит к следующему игроку."""
        self.current_player_index += 1
        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
            return None  # Все игроки увидели карты
        return self.get_current_player()
    
    def get_spies(self) -> List[Player]:
        """Возвращает список шпионов."""
        return [p for p in self.players if p.is_spy]
    
    def get_regular_players(self) -> List[Player]:
        """Возвращает список обычных игроков."""
        return [p for p in self.players if not p.is_spy]
    
    def check_game_end(self) -> Optional[str]:
        """
        Проверяет условия окончания игры.
        Returns: 'spies_win', 'players_win', 'continue' или None
        
        Игра заканчивается в двух случаях:
        1. Когда все шпионы найдены (удалены) -> игроки выигрывают
        2. Когда осталось 2 человека:
           - Если среди 2 человек есть хотя бы 1 шпион -> шпионы выигрывают
           - Если среди 2 человек нет шпионов -> обычные игроки выигрывают
        """
        spies = self.get_spies()
        regular = self.get_regular_players()
        
        spies_count = len(spies)
        regular_count = len(regular)
        total_remaining = spies_count + regular_count
        
        # Случай 1: Все шпионы найдены - игроки выигрывают
        if spies_count == 0:
            return 'players_win'
        
        # Случай 2: Осталось 2 человека - игра заканчивается
        if total_remaining == 2:
            # Если среди 2 человек есть хотя бы 1 шпион -> шпионы выигрывают
            if spies_count >= 1:
                return 'spies_win'
            # Если среди 2 человек нет шпионов -> обычные игроки выигрывают
            else:
                return 'players_win'
        
        # Если осталось меньше 2 человек - ошибка состояния
        if total_remaining < 2:
            return 'players_win'  # По умолчанию игроки выигрывают
        
        return 'continue'


class GameManager:
    """Менеджер игр."""
    
    def __init__(self):
        self.games: Dict[int, Game] = {}  # creator_id -> Game
    
    def create_game(self, creator_id: int, game_id: str) -> Game:
        """Создает новую игру."""
        # Останавливаем старую игру пользователя, если есть
        if creator_id in self.games:
            self.stop_game(creator_id)
        
        game = Game(game_id=game_id, creator_id=creator_id)
        self.games[creator_id] = game
        logger.info(f"Создана игра {game_id} для пользователя {creator_id}")
        return game
    
    def get_game(self, user_id: int) -> Optional[Game]:
        """Получает игру пользователя."""
        return self.games.get(user_id)
    
    def stop_game(self, user_id: int):
        """Останавливает игру пользователя."""
        if user_id in self.games:
            game = self.games[user_id]
            if game.timer_task:
                game.timer_task.cancel()
            game.is_active = False
            del self.games[user_id]
            logger.info(f"Игра остановлена для пользователя {user_id}")
    
    def setup_game(self, user_id: int, players_count: int, spies_count: int, cards: List[Dict]) -> Game:
        """
        Настраивает игру с игроками и картами.
        
        Args:
            user_id: ID создателя игры
            players_count: Количество игроков
            spies_count: Количество шпионов
            cards: Список карт из базы данных
        """
        game = self.get_game(user_id)
        if not game:
            return None
        
        game.players_count = players_count
        game.spies_count = spies_count
        
        # Выбираем случайные карты для обычных игроков
        regular_cards = random.sample(cards, min(len(cards), players_count - spies_count))
        
        # Создаем игроков
        players = []
        card_index = 0
        
        # Определяем, кто будет шпионом
        spy_indices = set(random.sample(range(players_count), spies_count))
        
        for i in range(players_count):
            is_spy = i in spy_indices
            
            if is_spy:
                player = Player(
                    user_id=user_id,  # Все играют на одном телефоне
                    username=f"Игрок {i + 1}",
                    is_spy=True
                )
            else:
                card = regular_cards[card_index % len(regular_cards)]
                player = Player(
                    user_id=user_id,
                    username=f"Игрок {i + 1}",
                    is_spy=False,
                    card_name=card['name'],
                    file_id=card['file_id']
                )
                card_index += 1
            
            players.append(player)
        
        game.players = players
        logger.info(f"Игра настроена: {players_count} игроков, {spies_count} шпионов")
        return game


# Глобальный менеджер игр
game_manager = GameManager()
