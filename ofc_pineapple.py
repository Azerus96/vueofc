# OFC Pineapple Poker Game Implementation for OpenSpiel
# Версия с ИСПРАВЛЕННЫМ action_to_string и ОТЛАДКОЙ расчета очков

import pyspiel
import numpy as np
from typing import List, Tuple, Any, Dict, Optional
import itertools
from collections import Counter
import copy

# --- Константы ---
NUM_PLAYERS = 2
NUM_RANKS = 13
NUM_SUITS = 4
NUM_CARDS = 52
TOP_ROW_SIZE = 3
MIDDLE_ROW_SIZE = 5
BOTTOM_ROW_SIZE = 5
TOTAL_CARDS_PLACED = TOP_ROW_SIZE + MIDDLE_ROW_SIZE + BOTTOM_ROW_SIZE
TOP_SLOTS = list(range(TOP_ROW_SIZE))
MIDDLE_SLOTS = list(range(TOP_ROW_SIZE, TOP_ROW_SIZE + MIDDLE_ROW_SIZE))
BOTTOM_SLOTS = list(range(TOP_ROW_SIZE + MIDDLE_ROW_SIZE, TOTAL_CARDS_PLACED))
ALL_SLOTS = list(range(TOTAL_CARDS_PLACED))
STREET_PREDEAL = 0
STREET_FIRST_DEAL_P1 = 1
STREET_FIRST_PLACE_P1 = 2
STREET_FIRST_DEAL_P2 = 3
STREET_FIRST_PLACE_P2 = 4
STREET_SECOND_DEAL_P1 = 5
STREET_SECOND_PLACE_P1 = 6
STREET_SECOND_DEAL_P2 = 7
STREET_SECOND_PLACE_P2 = 8
STREET_THIRD_DEAL_P1 = 9
STREET_THIRD_PLACE_P1 = 10
STREET_THIRD_DEAL_P2 = 11
STREET_THIRD_PLACE_P2 = 12
STREET_FOURTH_DEAL_P1 = 13
STREET_FOURTH_PLACE_P1 = 14
STREET_FOURTH_DEAL_P2 = 15
STREET_FOURTH_PLACE_P2 = 16
STREET_FIFTH_DEAL_P1 = 17
STREET_FIFTH_PLACE_P1 = 18
STREET_FIFTH_DEAL_P2 = 19
STREET_FIFTH_PLACE_P2 = 20
STREET_REGULAR_SHOWDOWN = 21
PHASE_FANTASY_DEAL = 30
PHASE_FANTASY_N_STREET_1 = 31
PHASE_FANTASY_F_PLACEMENT = 32
PHASE_FANTASY_N_STREET_2 = 33
PHASE_FANTASY_N_STREET_3 = 34
PHASE_FANTASY_N_STREET_4 = 35
PHASE_FANTASY_N_STREET_5 = 36
PHASE_FANTASY_SHOWDOWN = 37
DISCARD_SLOT = -1
RANKS = "23456789TJQKA"
SUITS = "shdc"

# --- Функции для карт ---
def card_rank(card_int: int) -> int:
    if card_int == -1: return -1
    if card_int is None: raise TypeError("card_rank получила None вместо int")
    return card_int // NUM_SUITS

def card_suit(card_int: int) -> int:
    if card_int == -1: return -1
    if card_int is None: raise TypeError("card_suit получила None вместо int")
    return card_int % NUM_SUITS

def card_to_string(card_int: int) -> str:
    if card_int == -1: return "__"
    if card_int is None: return "NN" # Обработка None для отладки
    if not 0 <= card_int < NUM_CARDS: raise ValueError(f"Неверный код карты: {card_int}")
    rank_idx = card_rank(card_int)
    suit_idx = card_suit(card_int)
    if rank_idx < 0 or rank_idx >= len(RANKS): raise ValueError(f"Неверный ранг {rank_idx} для карты {card_int}")
    if suit_idx < 0 or suit_idx >= len(SUITS): raise ValueError(f"Неверная масть {suit_idx} для карты {card_int}")
    return RANKS[rank_idx] + SUITS[suit_idx]

def string_to_card(card_str: str) -> int:
    if card_str == "__": return -1
    if card_str is None: raise TypeError("string_to_card получила None")
    if len(card_str) != 2: raise ValueError(f"Неверный формат строки карты: {card_str}")
    rank_char = card_str[0].upper()
    suit_char = card_str[1].lower()
    if rank_char not in RANKS or suit_char not in SUITS: raise ValueError(f"Неверный ранг или масть: {card_str}")
    rank = RANKS.index(rank_char)
    suit = SUITS.index(suit_char)
    return rank * NUM_SUITS + suit

def cards_to_strings(card_ints: List[Optional[int]]) -> List[str]:
    return [card_to_string(c) if c is not None else "NN" for c in card_ints]

def strings_to_cards(card_strs: List[str]) -> List[int]:
    return [string_to_card(s) for s in card_strs]

# --- Оценка Комбинаций ---
HIGH_CARD = 0
PAIR = 1
TWO_PAIR = 2
THREE_OF_A_KIND = 3
STRAIGHT = 4
FLUSH = 5
FULL_HOUSE = 6
FOUR_OF_A_KIND = 7
STRAIGHT_FLUSH = 8

def evaluate_hand(card_ints: List[Optional[int]]) -> Tuple[int, List[int]]:
    cards = [c for c in card_ints if c is not None and c != -1]
    n = len(cards)
    if n == 0: return (HIGH_CARD, [])

    ranks = sorted([card_rank(c) for c in cards], reverse=True)
    if n < 3: return (HIGH_CARD, ranks) # Для топ-ряда из <3 карт
    if n == 4: return (HIGH_CARD, ranks) # Нестандартный случай, но вернем старшие карты

    if n not in [3, 5]: # Должно быть 3 (топ) или 5 (мид/бот)
        # print(f"Предупреждение: evaluate_hand вызвана с {n} картами: {cards_to_strings(cards)}")
        return (HIGH_CARD, ranks) # Возвращаем старшие карты для неполных рядов

    suits = [card_suit(c) for c in cards]
    rank_counts = Counter(ranks)
    most_common_ranks = rank_counts.most_common()

    is_flush = False
    is_straight = False
    straight_high_card_rank = -1

    if n == 5:
        is_flush = len(set(suits)) == 1
        unique_ranks = sorted(list(set(ranks)), reverse=True)
        if len(unique_ranks) >= 5:
            for i in range(len(unique_ranks) - 4):
                # Проверка на обычный стрит (e.g., 9,8,7,6,5)
                if all(unique_ranks[i+j] == unique_ranks[i] - j for j in range(5)):
                    is_straight = True
                    straight_high_card_rank = unique_ranks[i]
                    break
            # Проверка на "колесо" (A,2,3,4,5) -> ранг 5(индекс 3) старший
            if not is_straight and set(unique_ranks).issuperset({12, 3, 2, 1, 0}): # A, 5, 4, 3, 2
                is_straight = True
                straight_high_card_rank = 3 # Ранг 5ки

        if is_straight and is_flush:
            return (STRAIGHT_FLUSH, [straight_high_card_rank])
        if most_common_ranks[0][1] == 4:
            # Каре: ранг каре, ранг кикера
            kicker = most_common_ranks[1][0] if len(most_common_ranks) > 1 else -1 # На случай если каре из 4х карт (не должно быть)
            return (FOUR_OF_A_KIND, [most_common_ranks[0][0], kicker])
        if len(most_common_ranks) > 1 and most_common_ranks[0][1] == 3 and most_common_ranks[1][1] >= 2:
            # Фулл-хаус: ранг тройки, ранг пары
            return (FULL_HOUSE, [most_common_ranks[0][0], most_common_ranks[1][0]])
        if is_flush:
            # Флеш: все 5 рангов по убыванию
            return (FLUSH, ranks)
        if is_straight:
            # Стрит: ранг старшей карты стрита
            return (STRAIGHT, [straight_high_card_rank])

    # Для 3 или 5 карт:
    if most_common_ranks[0][1] == 3:
        # Тройка: ранг тройки, затем кикеры по убыванию
        set_rank = most_common_ranks[0][0]
        other_ranks = sorted([r for r in ranks if r != set_rank], reverse=True)
        return (THREE_OF_A_KIND, [set_rank] + other_ranks)

    if n == 5 and len(most_common_ranks) > 1 and most_common_ranks[0][1] == 2 and most_common_ranks[1][1] == 2:
        # Две пары: ранг старшей пары, ранг младшей пары, ранг кикера
        high_pair_rank = most_common_ranks[0][0]
        low_pair_rank = most_common_ranks[1][0]
        kicker_rank = most_common_ranks[2][0] if len(most_common_ranks) > 2 else -1 # На случай если 4 карты (не должно быть)
        return (TWO_PAIR, [high_pair_rank, low_pair_rank, kicker_rank])

    if most_common_ranks[0][1] == 2:
        # Пара: ранг пары, затем кикеры по убыванию
        pair_rank = most_common_ranks[0][0]
        other_ranks = sorted([r for r in ranks if r != pair_rank], reverse=True)
        return (PAIR, [pair_rank] + other_ranks)

    # Старшая карта: все ранги по убыванию
    return (HIGH_CARD, ranks)

# --- Роялти и Мертвая Рука ---
TOP_ROYALTIES_PAIR = {
    4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7, 11: 8, 12: 9 # 66=1 ... AA=9
}
TOP_ROYALTIES_SET = { r: 10 + r for r in range(NUM_RANKS) } # 222=10 ... AAA=22
MIDDLE_ROYALTIES = {
    THREE_OF_A_KIND: 2, STRAIGHT: 4, FLUSH: 8, FULL_HOUSE: 12, FOUR_OF_A_KIND: 20, STRAIGHT_FLUSH: 30
}
BOTTOM_ROYALTIES = {
    STRAIGHT: 2, FLUSH: 4, FULL_HOUSE: 6, FOUR_OF_A_KIND: 10, STRAIGHT_FLUSH: 15
}
ROYAL_FLUSH_RANK = 12 # Ранг Туза

def calculate_royalties(hand_type: int, ranks: List[int], row_type: str) -> int:
    if not ranks: return 0
    if any(r is None for r in ranks): raise TypeError(f"calculate_royalties получила None в списке рангов: {ranks}")

    if row_type == 'top':
        if hand_type == THREE_OF_A_KIND:
            return TOP_ROYALTIES_SET.get(ranks[0], 0) # ranks[0] - ранг тройки
        elif hand_type == PAIR:
            return TOP_ROYALTIES_PAIR.get(ranks[0], 0) # ranks[0] - ранг пары
        else:
            return 0
    elif row_type == 'middle':
        # Роял флеш на мидле = 50
        if hand_type == STRAIGHT_FLUSH and ranks[0] == ROYAL_FLUSH_RANK:
            return 50
        return MIDDLE_ROYALTIES.get(hand_type, 0)
    elif row_type == 'bottom':
        # Роял флеш на боттоме = 25
        if hand_type == STRAIGHT_FLUSH and ranks[0] == ROYAL_FLUSH_RANK:
            return 25
        return BOTTOM_ROYALTIES.get(hand_type, 0)
    else:
        raise ValueError(f"Неизвестный тип ряда: {row_type}")

def compare_evals(eval1: Tuple[int, List[int]], eval2: Tuple[int, List[int]]) -> int:
    if eval1 is None or eval2 is None: raise TypeError("compare_evals получила None")
    type1, kickers1 = eval1
    type2, kickers2 = eval2
    if type1 is None or type2 is None: raise TypeError("compare_evals получила None в типе руки")
    if kickers1 is None or kickers2 is None: raise TypeError("compare_evals получила None в кикерах")
    if any(k is None for k in kickers1) or any(k is None for k in kickers2): raise TypeError("compare_evals получила None в списке кикеров")

    if type1 > type2: return 1
    if type1 < type2: return -1
    # Типы равны, сравниваем по кикерам
    len_kickers = min(len(kickers1), len(kickers2))
    for i in range(len_kickers):
        if kickers1[i] > kickers2[i]: return 1
        if kickers1[i] < kickers2[i]: return -1
    # Все кикеры равны
    return 0

def is_dead_hand(top_eval: Tuple[int, List[int]], middle_eval: Tuple[int, List[int]], bottom_eval: Tuple[int, List[int]]) -> bool:
    # Сравниваем топ с мидлом
    if compare_evals(top_eval, middle_eval) > 0:
        return True
    # Сравниваем мидл с боттомом
    if compare_evals(middle_eval, bottom_eval) > 0:
        return True
    return False

# --- Классы Игры и Состояния ---
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
    provides_information_state_tensor=False, # Пока не реализуем тензоры
    provides_observation_string=True,
    provides_observation_tensor=False, # Пока не реализуем тензоры
    parameter_specification={"num_players": NUM_PLAYERS} # Можно добавить параметры, если нужно
)

class OFCPineappleGame(pyspiel.Game):
    def __init__(self, params: Dict[str, Any] = None):
        # Устанавливаем разумные пределы для очков, хотя они могут быть и больше/меньше
        game_info = pyspiel.GameInfo(
            num_distinct_actions=-1, # Динамическое число действий
            max_chance_outcomes=NUM_CARDS,
            num_players=NUM_PLAYERS,
            min_utility=-250.0, # Примерный минимум (сильный проигрыш с роялти оппонента)
            max_utility=250.0, # Примерный максимум (сильный выигрыш с роялти)
            max_game_length=100 # Примерная длина игры (шанс-узлы + ходы игроков)
        )
        super().__init__(_GAME_TYPE, game_info, params or {})

    def new_initial_state(self):
        return OFCPineappleState(self)

    def make_py_observer(self, iig_obs_type=None, params=None):
        # Наблюдатель пока не нужен, ISMCTS использует information_state_string
        return None

class OFCPineappleState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        self._num_players = game.num_players()
        self._dealer_button = 0 # Игрок 0 - дилер в первой раздаче
        self._next_player_to_act = (self._dealer_button + 1) % self._num_players # Игрок слева от дилера ходит первым
        self._current_player = pyspiel.PlayerId.CHANCE # Начинаем с раздачи
        self._player_to_deal_to = self._next_player_to_act # Кому сдавать
        self._phase = STREET_PREDEAL # Начальная фаза

        self._deck = list(range(NUM_CARDS))
        np.random.shuffle(self._deck)

        # Доски игроков: список списков, где каждый внутренний список - 13 слотов
        self._board = [[-1] * TOTAL_CARDS_PLACED for _ in range(NUM_PLAYERS)]
        # Карты на руках у игроков на текущей улице
        self._current_cards = [[] for _ in range(NUM_PLAYERS)]
        # Сброшенные карты игроков (приватная информация)
        self._discards = [[] for _ in range(NUM_PLAYERS)]
        # Сколько карт нужно разместить/сбросить на текущем ходу
        self._cards_to_place_count = [0] * NUM_PLAYERS
        self._cards_to_discard_count = [0] * NUM_PLAYERS

        # Состояние Fantasyland (пока не используется)
        self._in_fantasy = [False] * NUM_PLAYERS
        self._fantasy_trigger = [None] * NUM_PLAYERS # Комбинация, вызвавшая Fantasy
        self._can_enter_fantasy = [True] * NUM_PLAYERS # Можно ли войти в Fantasy в этой раздаче
        self._fantasy_cards_count = 14 # Базовое кол-во карт Fantasy
        self._fantasy_player_has_placed = False # Флаг для Fantasy хода

        # Общее количество размещенных карт каждым игроком
        self._total_cards_placed = [0] * NUM_PLAYERS
        self._game_over = False
        # Накопленные очки за все раздачи
        self._cumulative_returns = [0.0] * NUM_PLAYERS
        # Очки за текущую раздачу (для отладки)
        self._current_hand_returns = [0.0] * NUM_PLAYERS

        # Кэш легальных действий (кортежей)
        self._cached_legal_actions: Optional[List[Any]] = None

        # Переходим к первой фазе игры
        self._go_to_next_phase()

    def _clear_cache(self):
        self._cached_legal_actions = None

    def _go_to_next_phase(self):
        self._clear_cache() # Очищаем кэш действий при смене фазы
        current_phase = self._phase
        next_phase = -1

        # Логика переходов для обычной игры
        if current_phase == STREET_PREDEAL:
            next_phase = STREET_FIRST_DEAL_P1
            self._current_player = pyspiel.PlayerId.CHANCE
            self._player_to_deal_to = self._next_player_to_act
        elif current_phase == STREET_FIRST_DEAL_P1:
            next_phase = STREET_FIRST_PLACE_P1
            self._current_player = self._player_to_deal_to
            self._cards_to_place_count[self._current_player] = 5
            self._cards_to_discard_count[self._current_player] = 0
        elif current_phase == STREET_FIRST_PLACE_P1:
            next_phase = STREET_FIRST_DEAL_P2
            self._current_player = pyspiel.PlayerId.CHANCE
            self._player_to_deal_to = (self._next_player_to_act + 1) % self._num_players
        elif current_phase == STREET_FIRST_DEAL_P2:
            next_phase = STREET_FIRST_PLACE_P2
            self._current_player = self._player_to_deal_to
            self._cards_to_place_count[self._current_player] = 5
            self._cards_to_discard_count[self._current_player] = 0
        elif current_phase == STREET_FIRST_PLACE_P2:
            next_phase = STREET_SECOND_DEAL_P1
            self._current_player = pyspiel.PlayerId.CHANCE
            self._player_to_deal_to = self._next_player_to_act
        # Улицы 2-5
        elif current_phase >= STREET_SECOND_DEAL_P1 and current_phase < STREET_REGULAR_SHOWDOWN:
            # Фаза сдачи (нечетная) -> Фаза размещения (следующая четная)
            if current_phase % 2 != 0: # DEAL phase
                next_phase = current_phase + 1
                self._current_player = self._player_to_deal_to
                self._cards_to_place_count[self._current_player] = 2
                self._cards_to_discard_count[self._current_player] = 1
            # Фаза размещения (четная) -> Фаза сдачи следующему игроку ИЛИ следующая улица ИЛИ шоудаун
            else: # PLACE phase
                current_player_index = (current_phase - STREET_FIRST_PLACE_P1) // 2 % NUM_PLAYERS
                is_p1_phase = current_player_index == 0 # Это была фаза размещения P1? (индексы 2, 6, 10, 14, 18)
                is_p2_phase = not is_p1_phase # Это была фаза размещения P2? (индексы 4, 8, 12, 16, 20)

                if is_p1_phase: # После хода P1 -> сдача P2
                    next_phase = current_phase + 1
                    self._current_player = pyspiel.PlayerId.CHANCE
                    self._player_to_deal_to = (self._next_player_to_act + 1) % self._num_players
                elif is_p2_phase: # После хода P2
                    if current_phase == STREET_FIFTH_PLACE_P2: # Последний ход в обычной игре
                        next_phase = STREET_REGULAR_SHOWDOWN
                        self._current_player = pyspiel.PlayerId.TERMINAL # Переходим к расчету
                        self._calculate_final_returns()
                        # Проверяем Fantasy (пока заглушка)
                        if not self._check_and_setup_fantasy():
                            self._game_over = True # Если нет Fantasy, игра окончена
                    else: # Не последняя улица -> сдача P1 на следующей улице
                        next_phase = current_phase + 1
                        self._current_player = pyspiel.PlayerId.CHANCE
                        self._player_to_deal_to = self._next_player_to_act
        elif current_phase == STREET_REGULAR_SHOWDOWN:
             # После расчета очков, если не было Fantasy, игра уже окончена (_game_over=True)
             # Если была настроена Fantasy, здесь должна быть логика перехода в фазы Fantasy
             if not self._game_over:
                 print("Переход в Fantasy (пока не реализован)")
                 # Здесь должна быть установка фазы Fantasy, например PHASE_FANTASY_DEAL
                 self._game_over = True # Пока ставим заглушку
                 self._current_player = pyspiel.PlayerId.TERMINAL
             next_phase = current_phase # Остаемся в этой фазе, если игра окончена
        # TODO: Добавить логику переходов для фаз Fantasyland
        else:
             # Неизвестная или терминальная фаза
             if not self._game_over:
                 self._game_over = True
                 self._current_player = pyspiel.PlayerId.TERMINAL
             next_phase = current_phase

        self._phase = next_phase

    def current_player(self):
        return self._current_player

    def is_chance_node(self):
        return self._current_player == pyspiel.PlayerId.CHANCE

    def is_terminal(self):
        return self._game_over

    def legal_actions(self, player: int) -> List[int]:
        """Возвращает список индексов легальных действий."""
        if self.is_chance_node() or self.is_terminal() or self._current_player != player:
            return []

        # Используем кэш, если он есть
        if self._cached_legal_actions is not None:
            return list(range(len(self._cached_legal_actions)))

        # Генерируем кортежи действий
        actions_tuples = self._generate_legal_actions_tuples(player)
        self._cached_legal_actions = actions_tuples # Сохраняем в кэш

        # Возвращаем индексы от 0 до N-1
        return list(range(len(actions_tuples)))

    def _generate_legal_actions_tuples(self, player):
        """Генерирует список кортежей, представляющих легальные действия."""
        actions = []
        is_place_phase = (self._phase >= STREET_FIRST_PLACE_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 == 0)
        # TODO: Добавить фазы размещения Fantasyland
        if not is_place_phase:
            return [] # Нет действий в фазах сдачи или шоудауна

        my_cards = self._current_cards[player]
        num_cards_in_hand = len(my_cards)
        num_to_place = self._cards_to_place_count[player]
        num_to_discard = self._cards_to_discard_count[player]

        if num_cards_in_hand != num_to_place + num_to_discard:
            # print(f"Предупреждение: Несоответствие карт в руке ({num_cards_in_hand}) и требуемых ({num_to_place}+{num_to_discard}) для P{player} в фазе {self._phase}")
            return [] # Не должно происходить при правильной логике фаз

        free_slots_indices = [i for i, card in enumerate(self._board[player]) if card == -1]
        num_free_slots = len(free_slots_indices)

        if num_free_slots < num_to_place:
            # print(f"Предупреждение: Недостаточно свободных слотов ({num_free_slots}) для размещения {num_to_place} карт для P{player} в фазе {self._phase}")
            return [] # Не должно происходить

        if num_to_discard == 0: # Улица 1
            if num_cards_in_hand != 5 or num_to_place != 5: return [] # Доп. проверка
            # Генерируем все перестановки слотов для данных 5 карт
            # Действие: кортеж из 5 пар (карта, слот)
            for slots in itertools.permutations(free_slots_indices, num_to_place):
                 action = tuple((my_cards[i], slots[i]) for i in range(num_to_place))
                 actions.append(action)
        else: # Улицы 2-5
            if num_cards_in_hand != 3 or num_to_place != 2 or num_to_discard != 1: return [] # Доп. проверка
            # Перебираем, какую карту сбросить
            for discard_idx in range(num_cards_in_hand):
                card_discard = my_cards[discard_idx]
                cards_to_place = my_cards[:discard_idx] + my_cards[discard_idx+1:]
                # Генерируем все перестановки слотов для 2х размещаемых карт
                for slots in itertools.permutations(free_slots_indices, num_to_place):
                    # Действие: кортеж ( ( (карта1,слот1), (карта2,слот2) ), карта_сброса )
                    placement = tuple((cards_to_place[i], slots[i]) for i in range(num_to_place))
                    action = (placement, card_discard)
                    actions.append(action)
        # TODO: Добавить генерацию действий для Fantasyland (размещение 13 из 14)

        return actions

    def apply_action(self, action_index_or_outcome):
        """Применяет действие или исход шанса."""
        if self.is_chance_node():
            # Применяем исход шанса (раздачу карт)
            player = self._player_to_deal_to
            num_cards_to_deal = 0
            if self._phase in [STREET_FIRST_DEAL_P1, STREET_FIRST_DEAL_P2]:
                num_cards_to_deal = 5
            elif (self._phase >= STREET_SECOND_DEAL_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 != 0): # Фазы сдачи 2-5 улиц
                num_cards_to_deal = 3
            # TODO: Добавить раздачу для Fantasyland

            if num_cards_to_deal > 0:
                 if len(self._deck) < num_cards_to_deal:
                     raise Exception(f"Недостаточно карт в колоде ({len(self._deck)}) для сдачи {num_cards_to_deal} карт!")
                 # Сдаем карты из колоды
                 self._current_cards[player] = [self._deck.pop() for _ in range(num_cards_to_deal)]

            self._go_to_next_phase() # Переходим к фазе размещения
            return

        # Применяем действие игрока
        if self.is_terminal(): raise ValueError("Cannot apply action on terminal node")
        if self.is_chance_node(): raise ValueError("Cannot apply player action on chance node")

        player = self._current_player
        action_index = action_index_or_outcome

        # Получаем кортеж действия из кэша (он должен быть заполнен вызовом legal_actions)
        if self._cached_legal_actions is None:
            self.legal_actions(player) # Заполняем кэш, если его нет (не должно происходить при правильном использовании)
        if self._cached_legal_actions is None or action_index < 0 or action_index >= len(self._cached_legal_actions):
            raise ValueError(f"Неверный индекс действия: {action_index} (доступно: {len(self._cached_legal_actions) if self._cached_legal_actions is not None else 'кэш пуст'}) для P{player} в фазе {self._phase}")

        action_tuple = self._cached_legal_actions[action_index]

        placement = []
        card_discard = -1
        num_placed = 0

        # Разбираем кортеж действия в зависимости от фазы
        if self._phase in [STREET_FIRST_PLACE_P1, STREET_FIRST_PLACE_P2]: # Улица 1
            if not (isinstance(action_tuple, tuple) and len(action_tuple) == 5): raise ValueError(f"Неверный формат действия для улицы 1: {action_tuple}")
            placement = list(action_tuple)
            num_placed = 5
        elif (self._phase >= STREET_SECOND_PLACE_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 == 0): # Улицы 2-5
            if not (isinstance(action_tuple, tuple) and len(action_tuple) == 2 and isinstance(action_tuple[0], tuple) and len(action_tuple[0]) == 2): raise ValueError(f"Неверный формат действия для улиц 2-5: {action_tuple}")
            placement = list(action_tuple[0])
            card_discard = action_tuple[1]
            num_placed = 2
        # TODO: Добавить обработку действия Fantasyland
        else:
            raise ValueError(f"Применение действия в неизвестной или неверной фазе: {self._phase}")

        # Размещаем карты на доске
        for card, slot_idx in placement:
            if not (0 <= slot_idx < TOTAL_CARDS_PLACED):
                raise ValueError(f"Неверный индекс слота: {slot_idx} в действии {action_tuple}")
            if self._board[player][slot_idx] != -1:
                raise ValueError(f"Слот {slot_idx} уже занят! Доска: {cards_to_strings(self._board[player])}, Действие: {action_tuple}")
            self._board[player][slot_idx] = card

        # Добавляем карту в сброс, если нужно
        if card_discard != -1:
            self._discards[player].append(card_discard)

        # Очищаем руку игрока
        self._current_cards[player] = []
        # Обновляем счетчик размещенных карт
        self._total_cards_placed[player] += num_placed
        # Сбрасываем счетчики для текущего хода
        self._cards_to_place_count[player] = 0
        self._cards_to_discard_count[player] = 0

        # Переходим к следующей фазе
        self._go_to_next_phase()

    def action_to_string(self, player: int, action_index: int) -> str:
        """Возвращает строковое представление действия по индексу."""
        action_tuple = None
        # Пытаемся получить действие из кэша
        if self._cached_legal_actions is not None and 0 <= action_index < len(self._cached_legal_actions):
            action_tuple = self._cached_legal_actions[action_index]
        # Если кэша нет или индекс вне диапазона, но это ход текущего игрока, генерируем действия
        elif self._current_player == player:
             self.legal_actions(player) # Заполняем кэш
             if self._cached_legal_actions is not None and 0 <= action_index < len(self._cached_legal_actions):
                 action_tuple = self._cached_legal_actions[action_index]

        if action_tuple is None:
            return f"InvalidActionIndex({action_index})"

        try:
            # Проверяем формат для Улиц 2-5 или Fantasy F (кортеж из 2х элементов: placement и discard)
            if isinstance(action_tuple, tuple) and len(action_tuple) == 2 and isinstance(action_tuple[0], tuple):
                 placement_tuple = action_tuple[0]
                 discard_card = action_tuple[1]
                 # Проверяем, что placement_tuple содержит пары (карта, слот)
                 if all(isinstance(item, tuple) and len(item) == 2 for item in placement_tuple):
                     placement_str = " ".join([f"{card_to_string(c)}({s})" for c,s in placement_tuple])
                     discard_str = card_to_string(discard_card)
                     if len(placement_tuple) == 2: # Улицы 2-5
                         return f"Place2 {placement_str} Discard {discard_str}"
                     # TODO: Добавить сюда логику для Fantasy F, если формат действия будет таким же
                     # elif len(placement_tuple) == 13: return f"FantasyF {placement_str} Discard {discard_str}"

            # Проверяем формат для Улицы 1 (кортеж из 5 пар (карта, слот))
            elif isinstance(action_tuple, tuple) and len(action_tuple) == 5 and all(isinstance(item, tuple) and len(item) == 2 for item in action_tuple):
                 return "Place1 " + " ".join([f"{card_to_string(c)}({s})" for c,s in action_tuple])

        except Exception as e:
            # print(f"Ошибка форматирования действия {action_tuple}: {e}") # Можно раскомментировать для отладки
            return f"ErrorFormattingAction({action_tuple})" # Возвращаем информацию об ошибке

        # Если формат не подошел ни под один известный
        return f"UnknownActionFormat({action_tuple})"

    def _calculate_final_returns(self):
        """Рассчитывает очки в конце раздачи (без Fantasy)."""
        # Проверяем, что все игроки разместили все карты
        if not all(count == TOTAL_CARDS_PLACED for count in self._total_cards_placed):
             # Это может случиться, если вызвать до конца игры, возвращаем 0
             # print("Предупреждение: Попытка рассчитать очки до завершения руки.")
             self._current_hand_returns = [0.0] * NUM_PLAYERS
             return

        scores = [0] * NUM_PLAYERS # Общий счет (линии + скуп + роялти)
        royalties = [0] * NUM_PLAYERS
        is_dead = [False] * NUM_PLAYERS
        evals = [{}, {}, {}] # evals[player_id][row_name] = (type, kickers)

        # 1. Оцениваем руки и проверяем на "мертвую"
        for p in range(NUM_PLAYERS):
            top_hand = self._board[p][TOP_SLOTS[0]:TOP_SLOTS[-1]+1]
            middle_hand = self._board[p][MIDDLE_SLOTS[0]:MIDDLE_SLOTS[-1]+1]
            bottom_hand = self._board[p][BOTTOM_SLOTS[0]:BOTTOM_SLOTS[-1]+1]
            evals[p]['top'] = evaluate_hand(top_hand)
            evals[p]['middle'] = evaluate_hand(middle_hand)
            evals[p]['bottom'] = evaluate_hand(bottom_hand)
            is_dead[p] = is_dead_hand(evals[p]['top'], evals[p]['middle'], evals[p]['bottom'])
            # Считаем роялти только для живых рук
            if not is_dead[p]:
                royalties[p] += calculate_royalties(evals[p]['top'][0], evals[p]['top'][1], 'top')
                royalties[p] += calculate_royalties(evals[p]['middle'][0], evals[p]['middle'][1], 'middle')
                royalties[p] += calculate_royalties(evals[p]['bottom'][0], evals[p]['bottom'][1], 'bottom')

        # 2. Попарное сравнение (для 2х игроков)
        p0 = 0
        p1 = 1
        line_scores = [0, 0] # Очки только за сравнение линий (+1/-1 за каждую)
        scoop_bonus = [0, 0] # Дополнительные +3 за скуп

        if is_dead[p0] and is_dead[p1]:
            # Обе руки мертвы - счет 0 для обоих по сравнению друг с другом
            pass # scores остаются 0
        elif is_dead[p0]:
            # P0 мертв, P1 жив -> P1 получает +6 очков (3 линии + 3 скуп) + свои роялти
            scores[p0] = -6 # P0 проигрывает 6 очков, роялти 0
            scores[p1] = 6 + royalties[p1]
        elif is_dead[p1]:
            # P1 мертв, P0 жив -> P0 получает +6 очков + свои роялти
            scores[p0] = 6 + royalties[p0]
            scores[p1] = -6 # P1 проигрывает 6 очков, роялти 0
        else:
            # Обе руки живы, сравниваем линии
            comp_t = compare_evals(evals[p0]['top'], evals[p1]['top'])
            comp_m = compare_evals(evals[p0]['middle'], evals[p1]['middle'])
            comp_b = compare_evals(evals[p0]['bottom'], evals[p1]['bottom'])
            # Начисляем очки за линии +1/-1
            line_scores[p0] = comp_t + comp_m + comp_b
            line_scores[p1] = -line_scores[p0]
            # Проверяем скуп по результатам сравнения
            if comp_t == 1 and comp_m == 1 and comp_b == 1: scoop_bonus[p0] = 3
            elif comp_t == -1 and comp_m == -1 and comp_b == -1: scoop_bonus[p1] = 3
            # Итоговый счет = очки за линии + очки за скуп + роялти
            scores[p0] = line_scores[p0] + scoop_bonus[p0] + royalties[p0]
            scores[p1] = line_scores[p1] + scoop_bonus[p1] + royalties[p1]

        # 3. Рассчитываем финальную разницу для returns()
        # Для 2х игроков разница P0 = score[0] - score[1]
        diff = scores[p0] - scores[p1]
        self._current_hand_returns = [diff, -diff]
        # Обновляем кумулятивные очки
        self._cumulative_returns[0] += diff
        self._cumulative_returns[1] -= diff
        # print(f"Рассчитаны очки: P0={scores[p0]}, P1={scores[p1]}, Royalty=[{royalties[0]},{royalties[1]}], Diff={diff}")

    def _check_and_setup_fantasy(self) -> bool:
        """Проверяет условия для Fantasyland и настраивает состояние (пока заглушка)."""
        # TODO: Реализовать проверку QQ+ на топе для живых рук
        # TODO: Настроить состояние для Fantasyland (фаза, раздача карт и т.д.)
        return False # Пока всегда возвращаем False

    def returns(self):
        """Возвращает кумулятивные очки для каждого игрока."""
        # Возвращаем очки только в терминальном состоянии
        if not self._game_over:
            return [0.0] * self._num_players
        return self._cumulative_returns

    def information_state_string(self, player: int) -> str:
        """Возвращает строку информационного состояния для указанного игрока."""
        if player < 0 or player >= self._num_players:
            # Для наблюдателя или невалидного игрока возвращаем общую информацию
            return f"Phase:{self._phase};GameOver:{self._game_over}"

        parts = []
        parts.append(f"P:{player}") # ID игрока
        parts.append(f"Ph:{self._phase}") # Текущая фаза

        # Доска текущего игрока
        my_board_cards = self._board[player]
        my_board_str = f"B:[{' '.join(cards_to_strings(my_board_cards[:3]))}|{' '.join(cards_to_strings(my_board_cards[3:8]))}|{' '.join(cards_to_strings(my_board_cards[8:]))}]"
        parts.append(my_board_str)

        # Карты на руке текущего игрока (если есть)
        parts.append(f"H:[{' '.join(cards_to_strings(self._current_cards[player]))}]")

        # Сброшенные карты текущего игрока (приватная информация)
        parts.append(f"D:[{' '.join(cards_to_strings(self._discards[player]))}]")

        # Доска оппонента (видимая часть)
        opponent = 1 - player
        opp_board_cards = self._board[opponent]
        opp_board_str = f"OB:[{' '.join(cards_to_strings(opp_board_cards[:3]))}|{' '.join(cards_to_strings(opp_board_cards[3:8]))}|{' '.join(cards_to_strings(opp_board_cards[8:]))}]"

        # Скрываем доску оппонента во время Fantasyland (если будет реализовано)
        is_fantasy_phase = self._phase >= PHASE_FANTASY_DEAL and self._phase <= PHASE_FANTASY_SHOWDOWN
        show_opp_board = not is_fantasy_phase # Пока всегда показываем
        if show_opp_board:
            parts.append(opp_board_str)
        else:
            parts.append("OB:[HIDDEN]") # Задел на будущее

        # Карты на руке оппонента (только на улице 1, когда они открыты)
        # На улицах 2-5 рука оппонента не видна
        if self._phase == STREET_FIRST_DEAL_P2 and player == 0: # Игрок 0 видит руку P1 перед его ходом
             opponent_hand_str = f"OH:[{' '.join(cards_to_strings(self._current_cards[opponent]))}]"
             parts.append(opponent_hand_str)
        elif self._phase == STREET_FIRST_PLACE_P1 and player == 1: # Игрок 1 видит руку P0 перед его ходом
             opponent_hand_str = f"OH:[{' '.join(cards_to_strings(self._current_cards[opponent]))}]"
             parts.append(opponent_hand_str)
        else:
             parts.append("OH:[?]") # Рука оппонента неизвестна

        # Статус Fantasyland (пока всегда False)
        parts.append(f"F:[{int(self._in_fantasy[0])}{int(self._in_fantasy[1])}]")

        # Сколько карт нужно разместить/сбросить (для текущего игрока)
        try:
            parts.append(f"Place:{self._cards_to_place_count[player]}|Discard:{self._cards_to_discard_count[player]}")
        except IndexError:
            parts.append("Place:?|Discard:?") # На всякий случай

        return ";".join(parts)

    def observation_string(self, player):
        """Возвращает строку наблюдения (используем ту же, что и information_state)."""
        return self.information_state_string(player)

    def clone(self):
        """Создает глубокую копию состояния."""
        cloned = type(self)(self._game) # Создаем новый экземпляр того же класса

        # Копируем неизменяемые или простые типы
        cloned._num_players = self._num_players
        cloned._current_player = self._current_player
        cloned._dealer_button = self._dealer_button
        cloned._next_player_to_act = self._next_player_to_act
        cloned._player_to_deal_to = self._player_to_deal_to
        cloned._phase = self._phase
        cloned._fantasy_cards_count = self._fantasy_cards_count
        cloned._fantasy_player_has_placed = self._fantasy_player_has_placed
        cloned._game_over = self._game_over

        # Копируем списки и словари
        cloned._deck = self._deck[:] # Поверхностная копия списка чисел
        cloned._cards_to_place_count = self._cards_to_place_count[:]
        cloned._cards_to_discard_count = self._cards_to_discard_count[:]
        cloned._in_fantasy = self._in_fantasy[:]
        cloned._can_enter_fantasy = self._can_enter_fantasy[:]
        cloned._total_cards_placed = self._total_cards_placed[:]
        cloned._cumulative_returns = self._cumulative_returns[:]
        cloned._current_hand_returns = self._current_hand_returns[:]

        # Глубокие копии для вложенных структур
        cloned._board = copy.deepcopy(self._board)
        cloned._current_cards = copy.deepcopy(self._current_cards)
        cloned._discards = copy.deepcopy(self._discards)
        cloned._fantasy_trigger = copy.deepcopy(self._fantasy_trigger) # Хотя пока None

        # Кэш не копируем, он будет пересоздан при необходимости
        cloned._cached_legal_actions = None

        return cloned

    def resample_from_infostate(self, player_id: int, probability_sampler) -> 'OFCPineappleState':
        """
        Создает новое состояние, сэмплируя неизвестную информацию.
        ЗАГЛУШКА! Требует полной реализации для ISMCTS.
        """
        # TODO: Реализовать настоящую детерминизацию:
        # 1. Определить все известные карты (доска player_id, рука player_id, сброс player_id, видимая доска оппонента).
        # 2. Собрать пул всех неизвестных карт (остаток колоды + невидимые карты оппонента: рука, сброс).
        # 3. Перемешать пул неизвестных карт с помощью probability_sampler или np.random.
        # 4. Создать клон текущего состояния (self.clone()).
        # 5. В клоне:
        #    а. Заполнить руку оппонента (если у него сейчас есть карты) из перемешанного пула.
        #    б. Заполнить сброс оппонента (если нужно для консистентности) из пула.
        #    в. Оставшиеся карты из пула поместить в колоду клона (_deck).
        # 6. Вернуть модифицированный клон.

        # Пока просто возвращаем клон без изменений (НЕПРАВИЛЬНО для ISMCTS)
        print("ПРЕДУПРЕЖДЕНИЕ: Вызвана заглушка resample_from_infostate!")
        return self.clone()

    def __str__(self):
        """Строковое представление состояния (для отладки)."""
        player = self.current_player()
        # Показываем инфостейт для текущего игрока или P0, если это шанс/терминал
        player_to_show = player if player >= 0 else 0
        return self.information_state_string(player_to_show)

# --- Регистрация игры ---
try:
    # Проверяем, не зарегистрирована ли игра уже
    pyspiel.load_game(_GAME_TYPE.short_name)
    print(f"Игра '{_GAME_TYPE.short_name}' уже была зарегистрирована.")
except pyspiel.SpielError:
    # Регистрируем игру, если она не найдена
    pyspiel.register_game(_GAME_TYPE, OFCPineappleGame)
    print(f"Игра '{_GAME_TYPE.short_name}' успешно зарегистрирована.")
except Exception as e:
    # Обработка других возможных ошибок при проверке/регистрации
    print(f"Неожиданная ошибка при проверке/регистрации игры '{_GAME_TYPE.short_name}': {e}")
