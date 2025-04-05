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

# Размеры рядов
TOP_ROW_SIZE = 3
MIDDLE_ROW_SIZE = 5
BOTTOM_ROW_SIZE = 5
TOTAL_CARDS_PLACED = TOP_ROW_SIZE + MIDDLE_ROW_SIZE + BOTTOM_ROW_SIZE # 13

# Индексы слотов (для удобства)
TOP_SLOTS = list(range(TOP_ROW_SIZE)) # 0, 1, 2
MIDDLE_SLOTS = list(range(TOP_ROW_SIZE, TOP_ROW_SIZE + MIDDLE_ROW_SIZE)) # 3, 4, 5, 6, 7
BOTTOM_SLOTS = list(range(TOP_ROW_SIZE + MIDDLE_ROW_SIZE, TOTAL_CARDS_PLACED)) # 8, 9, 10, 11, 12
ALL_SLOTS = list(range(TOTAL_CARDS_PLACED))

# Улицы и Фазы (уточненные)
STREET_PREDEAL = 0 # Техническая фаза до сдачи
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
    # Исправлено: Если карт меньше 3 (для топ) или 5 (для мид/бот), это не комбинация
    if (n < 3 and n > 0) or (n < 5 and n >= 3) : # Неполная рука, пока считаем старшей картой
         ranks = sorted([card_rank(c) for c in cards], reverse=True)
         return (HIGH_CARD, ranks)
    elif n == 0: # Пустая рука
         return (HIGH_CARD, [])
    # Убрано исключение, чтобы обрабатывать неполные руки во время игры

    ranks = sorted([card_rank(c) for c in cards], reverse=True)
    suits = [card_suit(c) for c in cards]
    rank_counts = Counter(ranks)
    most_common_ranks = rank_counts.most_common() # Список кортежей (ранг, количество)

    is_flush = n == 5 and len(set(suits)) == 1
    # Проверка стрита (включая A-5)
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = False
    straight_high_card_rank = -1
    # Для стрита нужно 5 разных рангов (или 3 для топ, но стрит на топ невозможен)
    if n == 5 and len(unique_ranks) >= 5:
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
        kickers = [straight_high_card_rank]
        return (STRAIGHT_FLUSH, kickers)

    # Каре (только для 5 карт)
    if n == 5 and most_common_ranks[0][1] == 4:
        quad_rank = most_common_ranks[0][0]
        kicker_rank = most_common_ranks[1][0]
        kickers = [quad_rank, kicker_rank]
        return (FOUR_OF_A_KIND, kickers)

    # Фулл-хаус (только для 5 карт)
    if n == 5 and most_common_ranks[0][1] == 3 and len(most_common_ranks) > 1 and most_common_ranks[1][1] >= 2: # >=2 на случай если 2я пара не видна из-за каре
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

    # Сет (Тройка) - может быть и в 3, и в 5 картах
    if most_common_ranks[0][1] == 3:
        set_rank = most_common_ranks[0][0]
        other_ranks = sorted([r for r in ranks if r != set_rank], reverse=True)
        kickers = [set_rank] + other_ranks
        return (THREE_OF_A_KIND, kickers)

    # Две пары (только для 5 карт)
    if n == 5 and len(most_common_ranks) > 1 and most_common_ranks[0][1] == 2 and most_common_ranks[1][1] == 2:
        high_pair_rank = most_common_ranks[0][0]
        low_pair_rank = most_common_ranks[1][0]
        kicker_rank = most_common_ranks[2][0]
        kickers = [high_pair_rank, low_pair_rank, kicker_rank]
        return (TWO_PAIR, kickers)

    # Пара - может быть и в 3, и в 5 картах
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

# Добавим глобальную переменную для типа игры, чтобы избежать повторения
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

class OFCPineappleGame(pyspiel.Game):
    """Класс игры OFC Pineapple для pyspiel."""
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
        # Используем глобальную _GAME_TYPE при инициализации
        super().__init__(_GAME_TYPE, game_info, params or {})

    def new_initial_state(self):
        """Создает начальное состояние игры."""
        return OFCPineappleState(self)

    def make_py_observer(self, iig_obs_type=None, params=None):
         """Возвращает объект наблюдателя (пока не реализован)."""
         return None


class OFCPineappleState(pyspiel.State):
    """Класс состояния игры OFC Pineapple."""
    def __init__(self, game):
        super().__init__(game)
        # --- Атрибуты состояния ---
        self._num_players = game.num_players()
        self._dealer_button = 0 # Игрок 0 - дилер
        # Определяем, кто ходит первым после дилера
        self._next_player_to_act = (self._dealer_button + 1) % self._num_players
        self._current_player = pyspiel.PlayerId.CHANCE # Начинаем со сдачи 1му игроку
        self._player_to_deal_to = self._next_player_to_act # Кому сдавать карты сейчас

        self._phase = STREET_PREDEAL # Текущая фаза/улица
        self._deck = list(range(NUM_CARDS))
        np.random.shuffle(self._deck)

        # Доска: список из 13 слотов (-1 = пусто) для каждого игрока
        self._board = [[-1] * TOTAL_CARDS_PLACED for _ in range(NUM_PLAYERS)]
        # Карты на руках (сданные на текущей улице)
        self._current_cards = [[] for _ in range(NUM_PLAYERS)]
        # Сброшенные карты (каждый видит только свои)
        self._discards = [[] for _ in range(NUM_PLAYERS)]

        # Fantasy
        self._in_fantasy = [False] * NUM_PLAYERS # Кто сейчас в Fantasy-раунде
        self._fantasy_trigger = [None] * NUM_PLAYERS # Комбинация QQ+ для входа
        self._can_enter_fantasy = [True] * NUM_PLAYERS # Может ли игрок войти в Fantasy в этом матче
        self._fantasy_cards_count = 14 # Для обычной Fantasy
        self._fantasy_player_has_placed = False # Разместил ли F-игрок свои 13 карт

        # Отслеживание прогресса руки/матча
        self._total_cards_placed = [0] * NUM_PLAYERS
        self._player_confirmed_action = False # Подтвердил ли текущий игрок свой ход на улице
        self._game_over = False
        self._cumulative_returns = [0.0] * NUM_PLAYERS # Очки за весь матч
        self._current_hand_returns = [0.0] * NUM_PLAYERS # Очки за текущую руку (основную или Fantasy)

        # Начинаем игру с фазы сдачи 5 карт первому игроку
        self._go_to_next_phase()

    def _go_to_next_phase(self):
        """Переход к следующей фазе/улице/игроку."""
        # --- Логика переходов ---
        if self._phase == STREET_PREDEAL:
             self._phase = STREET_FIRST_DEAL_P1
             self._current_player = pyspiel.PlayerId.CHANCE
             self._player_to_deal_to = self._next_player_to_act # Кому сдаем 5 карт
        elif self._phase == STREET_FIRST_DEAL_P1:
             self._phase = STREET_FIRST_PLACE_P1
             self._current_player = self._player_to_deal_to # Тот, кому сдали, ходит
             self._player_confirmed_action = False
        elif self._phase == STREET_FIRST_PLACE_P1:
             # Игрок 1 разместил, теперь сдаем игроку 2
             self._phase = STREET_FIRST_DEAL_P2
             self._current_player = pyspiel.PlayerId.CHANCE
             self._player_to_deal_to = (self._next_player_to_act + 1) % self._num_players
        elif self._phase == STREET_FIRST_DEAL_P2:
             self._phase = STREET_FIRST_PLACE_P2
             self._current_player = self._player_to_deal_to # Игрок 2 ходит
             self._player_confirmed_action = False
        elif self._phase == STREET_FIRST_PLACE_P2:
             # Первая улица закончена, переходим ко второй
             self._phase = STREET_SECOND_DEAL_P1
             self._current_player = pyspiel.PlayerId.CHANCE
             self._player_to_deal_to = self._next_player_to_act # Сдаем 3 карты первому
        # TODO: Добавить остальные переходы для улиц 2-5
        # TODO: Добавить переход к STREET_REGULAR_SHOWDOWN
        # TODO: Добавить логику проверки Fantasy и переходы в фазы Fantasy
        # TODO: Добавить логику переходов внутри Fantasy
        # TODO: Добавить логику проверки Re-Fantasy и возврата или завершения
        else:
             print(f"Предупреждение: Необработанный переход из фазы {self._phase}")
             self._game_over = True # Пока завершаем игру
             self._current_player = pyspiel.PlayerId.TERMINAL

    def current_player(self):
        """Возвращает ID текущего игрока или константу."""
        return self._current_player

    def _legal_actions(self, player):
        """Генерирует список легальных действий (кортежей)."""
        actions = []
        if self._current_player == pyspiel.PlayerId.CHANCE or \
           self._current_player == pyspiel.PlayerId.TERMINAL or \
           self._current_player != player:
            return []

        # TODO: Реализовать генерацию действий в зависимости от self._phase
        # Используя self._current_cards[player] и свободные слоты в self._board[player]
        # Пример для улицы 2-5:
        # if self._phase >= STREET_SECOND_PLACE_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 == 0: # Фазы размещения
        #   my_cards = self._current_cards[player] # Должно быть 3 карты
        #   if len(my_cards) != 3: return [] # Если карт нет, действий нет
        #   free_slots_indices = [i for i, card in enumerate(self._board[player]) if card == -1]
        #   if len(free_slots_indices) < 2: return [] # Некуда ставить
        #
        #   # Перебрать все комбинации: выбрать 2 карты из 3, выбрать 2 слота из свободных
        #   for cards_to_place in itertools.combinations(my_cards, 2):
        #       card_discard = list(set(my_cards) - set(cards_to_place))[0]
        #       for slots in itertools.permutations(free_slots_indices, 2):
        #           # Действие = ((карта1, слот1), (карта2, слот2), карта_сброс)
        #           action = ( (cards_to_place[0], slots[0]), (cards_to_place[1], slots[1]), card_discard )
        #           # TODO: Проверить, не создает ли это действие "мертвую" руку немедленно (опционально)
        #           actions.append(action)

        return actions # Placeholder

    def _apply_action(self, action):
        """Применяет действие (размещение карт) и переходит к след. фазе."""
        if self._current_player == pyspiel.PlayerId.CHANCE:
            # Логика сдачи карт (вызывается из _go_to_next_phase или явно?)
            # В нашей схеме сдача происходит при переходе *в* фазу DEAL
            player = self._player_to_deal_to
            num_cards_to_deal = 0
            if self._phase == STREET_FIRST_DEAL_P1 or self._phase == STREET_FIRST_DEAL_P2:
                num_cards_to_deal = 5
            elif self._phase >= STREET_SECOND_DEAL_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 != 0: # Фазы DEAL улиц 2-5
                num_cards_to_deal = 3
            # TODO: Добавить сдачу для Fantasy

            if num_cards_to_deal > 0:
                 if len(self._deck) < num_cards_to_deal: raise Exception("Недостаточно карт в колоде!")
                 self._current_cards[player] = [self._deck.pop() for _ in range(num_cards_to_deal)]
            self._go_to_next_phase() # Переходим к фазе размещения
            return

        if self._current_player == pyspiel.PlayerId.TERMINAL:
             raise ValueError("Cannot apply action on terminal node")

        player = self._current_player
        # TODO: Распарсить 'action' (кортеж)
        # TODO: Обновить self._board[player]
        # TODO: Обновить self._discards[player] (если применимо)
        # TODO: Очистить self._current_cards[player]
        # TODO: Обновить self._total_cards_placed[player]
        self._player_confirmed_action = True

        # Переходим к следующей фазе (сдача другому игроку или след. улица)
        self._go_to_next_phase()

    def _action_to_string(self, player, action):
        """Преобразует действие (кортеж) в строку."""
        # TODO: Реализовать
        return str(action)

    def is_terminal(self):
        """Завершен ли весь матч."""
        return self._game_over

    def returns(self):
        """Возвращает накопленные очки за весь матч."""
        # TODO: Реализовать подсчет очков в конце (в фазе SHOWDOWN)
        return self._cumulative_returns

    def information_state_string(self, player):
        """Возвращает строку информации, доступную игроку."""
        # TODO: Тщательно реализовать
        parts = []
        parts.append(f"P:{player}")
        parts.append(f"Phase:{self._phase}")
        # Своя доска
        parts.append(f"Board:[{' '.join(cards_to_strings(self._board[player]))}]")
        # Свои карты на руках
        parts.append(f"Hand:[{' '.join(cards_to_strings(self._current_cards[player]))}]")
        # Свой сброс
        parts.append(f"Discard:[{' '.join(cards_to_strings(self._discards[player]))}]")

        # Информация об оппоненте (зависит от фазы)
        opponent = 1 - player
        opponent_board_str = f"OppBoard:[{' '.join(cards_to_strings(self._board[opponent]))}]"
        opponent_hand_str = ""

        # Видимость доски оппонента (скрыта только в Fantasy)
        is_fantasy_phase = self._phase >= PHASE_FANTASY_DEAL and self._phase <= PHASE_FANTASY_SHOWDOWN
        i_am_fantasy = self._in_fantasy[player]
        opp_is_fantasy = self._in_fantasy[opponent]

        show_opp_board = True
        if is_fantasy_phase and i_am_fantasy: # Если я в Fantasy, я не вижу доску N во время размещения
             show_opp_board = False
        if is_fantasy_phase and not i_am_fantasy: # Если я не в Fantasy, я не вижу доску F во время своей игры
             show_opp_board = False

        if show_opp_board:
             parts.append(opponent_board_str)
        else:
             parts.append("OppBoard:[HIDDEN]")

        # Видимость руки оппонента (только на 1й улице)
        if self._phase >= STREET_FIRST_DEAL_P1 and self._phase <= STREET_FIRST_PLACE_P2:
             opponent_hand_str = f"OppHand:[{' '.join(cards_to_strings(self._current_cards[opponent]))}]"
             parts.append(opponent_hand_str)

        # Статус Fantasy
        parts.append(f"Fantasy:[{int(self._in_fantasy[0])}{int(self._in_fantasy[1])}]")

        return " ".join(parts)


    def observation_string(self, player):
        """Возвращает строку наблюдения (можно как info_state)."""
        return self.information_state_string(player)

    def clone(self):
        """Создает глубокую копию состояния."""
        cloned = OFCPineappleState(self._game)
        cloned._current_player = self._current_player
        cloned._dealer_button = self._dealer_button
        cloned._next_player_to_act = self._next_player_to_act
        cloned._player_to_deal_to = self._player_to_deal_to # Добавлено
        cloned._phase = self._phase
        cloned._deck = self._deck[:]
        cloned._board = [row[:] for row in self._board]
        cloned._current_cards = [cards[:] for cards in self._current_cards]
        cloned._discards = [cards[:] for cards in self._discards]
        cloned._in_fantasy = self._in_fantasy[:]
        cloned._fantasy_trigger = self._fantasy_trigger[:]
        cloned._can_enter_fantasy = self._can_enter_fantasy[:]
        cloned._fantasy_cards_count = self._fantasy_cards_count
        cloned._fantasy_player_has_placed = self._fantasy_player_has_placed
        cloned._total_cards_placed = self._total_cards_placed[:]
        cloned._player_confirmed_action = self._player_confirmed_action
        cloned._game_over = self._game_over
        cloned._cumulative_returns = self._cumulative_returns[:]
        cloned._current_hand_returns = self._current_hand_returns[:]
        return cloned

    def resample_from_infostate(self, player_id, probability_sampler):
        """Сэмплирует полное состояние, совместимое с информацией игрока."""
        # TODO: Реализовать
        return self.clone() # Placeholder

    def __str__(self):
        """Строковое представление состояния для отладки."""
        # TODO: Улучшить
        player = self.current_player()
        if player < 0: player = 0 # Для вывода info_state даже если ход шанса/терминал
        return self.information_state_string(player)


# --- Регистрация игры ---
try:
    # Проверяем, зарегистрирована ли игра, чтобы избежать ошибки при перезапуске
    pyspiel.load_game(_GAME_TYPE.short_name)
    print(f"Игра '{_GAME_TYPE.short_name}' уже была зарегистрирована.")
except pyspiel.SpielError:
    # Регистрируем, если не была зарегистрирована
    pyspiel.register_game(_GAME_TYPE, OFCPineappleGame)
    print(f"Игра '{_GAME_TYPE.short_name}' успешно зарегистрирована.")
except Exception as e:
     print(f"Неожиданная ошибка при проверке/регистрации игры: {e}")


print("\nФайл ofc_pineapple.py создан/перезаписан.")
print("Не забудьте обновить его в вашем GitHub репозитории.")
print("В Colab используйте:")
print("!wget -O ofc_pineapple.py <URL_RAW_ВАШЕГО_ФАЙЛА>")
print("import ofc_pineapple")
print("import pyspiel")
print("game = pyspiel.load_game('ofc_pineapple')")
print("state = game.new_initial_state()")
