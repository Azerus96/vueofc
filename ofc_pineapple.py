%%writefile ofc_pineapple.py
# OFC Pineapple Poker Game Implementation for OpenSpiel

import pyspiel
import numpy as np
from typing import List, Tuple, Any, Dict, Optional
import itertools
from collections import Counter # Понадобится для подсчета рангов/мастей

# --- Константы ---
NUM_PLAYERS = 2
NUM_RANKS = 13
NUM_SUITS = 4
NUM_CARDS = 52

TOP_ROW_SIZE = 3
MIDDLE_ROW_SIZE = 5
BOTTOM_ROW_SIZE = 5
TOTAL_CARDS_PLACED = TOP_ROW_SIZE + MIDDLE_ROW_SIZE + BOTTOM_ROW_SIZE # 13

TOP_SLOTS = list(range(TOP_ROW_SIZE))
MIDDLE_SLOTS = list(range(TOP_ROW_SIZE, TOP_ROW_SIZE + MIDDLE_ROW_SIZE))
BOTTOM_SLOTS = list(range(TOP_ROW_SIZE + MIDDLE_ROW_SIZE, TOTAL_CARDS_PLACED))
ALL_SLOTS = list(range(TOTAL_CARDS_PLACED))

# Улицы и Фазы (уточненные)
STREET_PREDEAL = 0
STREET_FIRST_DEAL_P1 = 1 # Сдача 5 карт P1
STREET_FIRST_PLACE_P1 = 2 # Размещение P1
STREET_FIRST_DEAL_P2 = 3 # Сдача 5 карт P2
STREET_FIRST_PLACE_P2 = 4 # Размещение P2
STREET_SECOND_DEAL_P1 = 5 # Сдача 3 карт P1
STREET_SECOND_PLACE_P1 = 6 # Размещение P1 (2/1)
STREET_SECOND_DEAL_P2 = 7 # Сдача 3 карт P2
STREET_SECOND_PLACE_P2 = 8 # Размещение P2 (2/1)
# ... Аналогично для STREET_THIRD, STREET_FOURTH, STREET_FIFTH (9-16)
STREET_FIFTH_PLACE_P2 = 16
STREET_REGULAR_SHOWDOWN = 17 # Подсчет основной руки, проверка Fantasy

# Фазы Fantasy (для 1 на 1)
PHASE_FANTASY_DEAL = 20 # Сдача 14 F / 5 N
PHASE_FANTASY_N_STREET_1 = 21 # N размещает 5
PHASE_FANTASY_F_PLACEMENT = 22 # F размещает 13/1
PHASE_FANTASY_N_STREET_2 = 23 # N получает 3, размещает 2/1
PHASE_FANTASY_N_STREET_3 = 24 # N получает 3, размещает 2/1
PHASE_FANTASY_N_STREET_4 = 25 # N получает 3, размещает 2/1
PHASE_FANTASY_N_STREET_5 = 26 # N получает 3, размещает 2/1
PHASE_FANTASY_SHOWDOWN = 27 # Подсчет Fantasy руки, проверка Re-Fantasy

# Карты (0-51): Карта = rank * NUM_SUITS + suit
RANKS = "23456789TJQKA"
SUITS = "shdc" # spades, hearts, diamonds, clubs

def card_rank(card_int: int) -> int:
    """Возвращает ранг карты (0-12)."""
    if card_int == -1: return -1
    return card_int // NUM_SUITS

def card_suit(card_int: int) -> int:
    """Возвращает масть карты (0-3)."""
    if card_int == -1: return -1
    return card_int % NUM_SUITS

def card_to_string(card_int: int) -> str:
    """Преобразует числовое представление карты в строку (e.g., 51 -> 'Ac')."""
    if card_int == -1: return "__" # Пустой слот
    if not 0 <= card_int < NUM_CARDS:
        raise ValueError(f"Неверный код карты: {card_int}")
    return RANKS[card_rank(card_int)] + SUITS[card_suit(card_int)]

def string_to_card(card_str: str) -> int:
    """Преобразует строку карты в числовое представление (e.g., 'Ac' -> 51)."""
    if card_str == "__": return -1
    if len(card_str) != 2:
        raise ValueError(f"Неверный формат строки карты: {card_str}")
    rank_char = card_str[0].upper()
    suit_char = card_str[1].lower()
    if rank_char not in RANKS or suit_char not in SUITS:
        raise ValueError(f"Неверный ранг или масть: {card_str}")
    rank = RANKS.index(rank_char)
    suit = SUITS.index(suit_char)
    return rank * NUM_SUITS + suit

def cards_to_strings(card_ints: List[int]) -> List[str]:
    """Конвертирует список числовых карт в список строк."""
    return [card_to_string(c) for c in card_ints]

def strings_to_cards(card_strs: List[str]) -> List[int]:
    """Конвертирует список строк карт в список чисел."""
    return [string_to_card(s) for s in card_strs]

# --- Оценка Комбинаций ---
# Константы для типов комбинаций (чем больше, тем лучше)
HIGH_CARD = 0
PAIR = 1
TWO_PAIR = 2
THREE_OF_A_KIND = 3
STRAIGHT = 4
FLUSH = 5
FULL_HOUSE = 6
FOUR_OF_A_KIND = 7
STRAIGHT_FLUSH = 8 # Включая Royal Flush

def evaluate_hand(card_ints: List[int]) -> Tuple[int, List[int]]:
    """
    Оценивает комбинацию из 3 или 5 карт.
    Возвращает кортеж: (тип_комбинации, список_рангов_кикеров).
    Кикеры упорядочены по важности (например, для пары QQJ82 кикеры [10, 9, 6, 0]).
    Для стрита A2345 ранг туза считается низким (кикеры [3, 2, 1, 0, -1]).
    """
    cards = [c for c in card_ints if c != -1] # Игнорируем пустые слоты
    n = len(cards)
    if n not in [3, 5]:
        raise ValueError(f"Оценка возможна только для 3 или 5 карт, получено: {n}")

    ranks = sorted([card_rank(c) for c in cards], reverse=True)
    suits = [card_suit(c) for c in cards]
    rank_counts = Counter(ranks)
    most_common_ranks = rank_counts.most_common() # Список кортежей (ранг, количество)

    is_flush = n == 5 and len(set(suits)) == 1
    # Проверка стрита (включая A-5)
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = False
    straight_high_card_rank = -1
    if len(unique_ranks) >= 5: # Нужно 5 разных рангов для стрита из 5 карт
        # Обычный стрит
        for i in range(len(unique_ranks) - 4):
            if all(unique_ranks[i+j] == unique_ranks[i] - j for j in range(5)):
                is_straight = True
                straight_high_card_rank = unique_ranks[i]
                break
        # Проверка A-5 ("колесо")
        if not is_straight and set(unique_ranks).issuperset({12, 3, 2, 1, 0}): # A, 5, 4, 3, 2
             is_straight = True
             straight_high_card_rank = 3 # Старшая карта в A-5 - это 5 (ранг 3)

    # --- Определение комбинации ---
    # (Проверяем от старшей к младшей)

    # Стрит-флеш (только для 5 карт)
    if n == 5 and is_straight and is_flush:
        # Для A-5 флеша кикер - ранг 5 (3)
        # Для Royal Flush (AKQJT) кикер - ранг A (12)
        # Для остальных - старшая карта стрита
        kickers = [straight_high_card_rank]
        return (STRAIGHT_FLUSH, kickers)

    # Каре (только для 5 карт)
    if n == 5 and most_common_ranks[0][1] == 4:
        quad_rank = most_common_ranks[0][0]
        kicker_rank = most_common_ranks[1][0]
        kickers = [quad_rank, kicker_rank]
        return (FOUR_OF_A_KIND, kickers)

    # Фулл-хаус (только для 5 карт)
    if n == 5 and most_common_ranks[0][1] == 3 and most_common_ranks[1][1] == 2:
        three_rank = most_common_ranks[0][0]
        pair_rank = most_common_ranks[1][0]
        kickers = [three_rank, pair_rank]
        return (FULL_HOUSE, kickers)

    # Флеш (только для 5 карт)
    if n == 5 and is_flush:
        kickers = ranks # Все 5 рангов флеша как кикеры
        return (FLUSH, kickers)

    # Стрит (только для 5 карт)
    if n == 5 and is_straight:
        kickers = [straight_high_card_rank]
        return (STRAIGHT, kickers)

    # Сет (Тройка)
    if most_common_ranks[0][1] == 3:
        set_rank = most_common_ranks[0][0]
        other_ranks = sorted([r for r in ranks if r != set_rank], reverse=True)
        kickers = [set_rank] + other_ranks
        return (THREE_OF_A_KIND, kickers)

    # Две пары (только для 5 карт)
    if n == 5 and most_common_ranks[0][1] == 2 and most_common_ranks[1][1] == 2:
        high_pair_rank = most_common_ranks[0][0]
        low_pair_rank = most_common_ranks[1][0]
        kicker_rank = most_common_ranks[2][0]
        kickers = [high_pair_rank, low_pair_rank, kicker_rank]
        return (TWO_PAIR, kickers)

    # Пара
    if most_common_ranks[0][1] == 2:
        pair_rank = most_common_ranks[0][0]
        other_ranks = sorted([r for r in ranks if r != pair_rank], reverse=True)
        kickers = [pair_rank] + other_ranks
        return (PAIR, kickers)

    # Старшая карта
    kickers = ranks
    return (HIGH_CARD, kickers)

# TODO: Реализовать calculate_royalties(hand_type: int, ranks: List[int], row_type: str) -> int
# TODO: Реализовать is_dead_hand(top_eval, middle_eval, bottom_eval) -> bool

# --- Классы Игры и Состояния ---

class OFCPineappleGame(pyspiel.Game):
    # ... (Код из предыдущего сообщения) ...
    def __init__(self, params: Dict[str, Any] = None):
        min_util = -250.0
        max_util = 250.0
        game_info = pyspiel.GameInfo(
            num_distinct_actions=-1,
            max_chance_outcomes=NUM_CARDS,
            num_players=NUM_PLAYERS,
            min_utility=min_util,
            max_utility=max_util,
            max_game_length=100
        )
        super().__init__(_GAME_TYPE, game_info, params or {}) # Используем _GAME_TYPE

    def new_initial_state(self):
        return OFCPineappleState(self)

    def make_py_observer(self, iig_obs_type=None, params=None):
         return None


class OFCPineappleState(pyspiel.State):
    # ... (Атрибуты состояния из предыдущего сообщения) ...
    def __init__(self, game):
        super().__init__(game)
        self._num_players = game.num_players()
        self._dealer_button = 0
        self._current_player = pyspiel.PlayerId.CHANCE
        self._next_player_to_deal_to = 1 - self._dealer_button
        self._next_player_to_act = self._next_player_to_deal_to
        self._phase = STREET_PREDEAL
        self._deck = list(range(NUM_CARDS))
        np.random.shuffle(self._deck)
        self._board = [[-1] * TOTAL_CARDS_PLACED for _ in range(NUM_PLAYERS)]
        self._current_cards = [[] for _ in range(NUM_PLAYERS)]
        self._discards = [[] for _ in range(NUM_PLAYERS)]
        self._in_fantasy = [False] * NUM_PLAYERS
        self._fantasy_trigger = [None] * NUM_PLAYERS
        self._can_enter_fantasy = [True] * NUM_PLAYERS
        self._fantasy_cards_count = 14
        self._fantasy_player_has_placed = False
        self._total_cards_placed = [0] * NUM_PLAYERS
        self._player_confirmed_action = False
        self._game_over = False
        self._cumulative_returns = [0.0] * NUM_PLAYERS
        self._current_hand_returns = [0.0] * NUM_PLAYERS
        self._go_to_next_phase() # Начинаем игру

    # ... (Методы _go_to_next_phase, current_player, _legal_actions, _apply_action, ...)
    # ... (Методы _action_to_string, is_terminal, returns, ...)
    # ... (Методы information_state_string, observation_string, clone, resample_from_infostate, __str__)
    # --- Добавляем заглушки для нереализованных методов ---
    def _go_to_next_phase(self):
        # Пока просто переходим к первому игроку для теста
        if self._phase == STREET_PREDEAL:
             self._phase = STREET_FIRST_DEAL_P1
             self._current_player = pyspiel.PlayerId.CHANCE
        elif self._phase == STREET_FIRST_DEAL_P1:
             # Сдаем 5 карт игроку _next_player_to_deal_to
             player = self._next_player_to_deal_to
             if len(self._deck) < 5: raise Exception("Недостаточно карт в колоде!")
             self._current_cards[player] = [self._deck.pop() for _ in range(5)]
             self._phase = STREET_FIRST_PLACE_P1 # Фаза размещения первого игрока
             self._current_player = player
             self._player_confirmed_action = False
        # TODO: Добавить остальные переходы
        else:
             print(f"Предупреждение: Необработанный переход из фазы {self._phase}")
             self._game_over = True # Пока завершаем игру, если не знаем, что делать
             self._current_player = pyspiel.PlayerId.TERMINAL


    def current_player(self):
        return self._current_player

    def _legal_actions(self, player):
        # TODO: Реализовать
        return []

    def _apply_action(self, action):
        # TODO: Реализовать
        self._player_confirmed_action = True
        self._go_to_next_phase()

    def _action_to_string(self, player, action):
        return str(action)

    def is_terminal(self):
        return self._game_over

    def returns(self):
        # TODO: Реализовать подсчет очков
        return self._cumulative_returns

    def information_state_string(self, player):
        # TODO: Реализовать
        return f"Player {player} Phase {self._phase}"

    def observation_string(self, player):
        return self.information_state_string(player)

    def clone(self):
        # TODO: Реализовать полное клонирование
        return self # НЕПРАВИЛЬНО! Только для теста

    def resample_from_infostate(self, player_id, probability_sampler):
         # TODO: Реализовать
         return self.clone() # НЕПРАВИЛЬНО! Только для теста

    def __str__(self):
        # TODO: Улучшить
        return self.information_state_string(self.current_player())


# --- Регистрация игры ---
_GAME_TYPE = pyspiel.GameType(
    short_name="ofc_pineapple",
    long_name="Open Face Chinese Poker Pineapple",
    dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL,
    chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC,
    information=pyspiel.GameType.Information.IMPERFECT_INFORMATION,
    utility=pyspiel.GameType.Utility.ZERO_SUM,
    reward_model=pyspiel.GameType.RewardModel.TERMINAL,
    max_num_players=NUM_PLAYERS,
    min_num_players=NUM_PLAYERS,
    provides_information_state_string=True,
    provides_information_state_tensor=False,
    provides_observation_string=True,
    provides_observation_tensor=False,
    parameter_specification={"num_players": NUM_PLAYERS}
)
try:
    pyspiel.register_game(_GAME_TYPE, OFCPineappleGame)
    print(f"Игра '{_GAME_TYPE.short_name}' успешно зарегистрирована.")
except Exception as e:
    # Если игра уже зарегистрирована (при повторном запуске ячейки), это нормально
    if "already registered" not in str(e):
        print(f"Ошибка при регистрации игры: {e}")

print("\nФайл ofc_pineapple.py создан/перезаписан.")
print("Не забудьте обновить его в вашем GitHub репозитории.")
print("В Colab используйте:")
print("!wget -O ofc_pineapple.py <URL_RAW_ВАШЕГО_ФАЙЛА>")
print("import ofc_pineapple")
print("import pyspiel")
print("game = pyspiel.load_game('ofc_pineapple')")
print("state = game.new_initial_state()")
