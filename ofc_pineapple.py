# OFC Pineapple Poker Game Implementation for OpenSpiel
# Версия с реализацией _legal_actions и _apply_action (без Fantasy)

import pyspiel
import numpy as np
from typing import List, Tuple, Any, Dict, Optional
import itertools
from collections import Counter

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

# Фазы игры
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

# Специальное значение для слота сброса
DISCARD_SLOT = -1

RANKS = "23456789TJQKA"
SUITS = "shdc"

# --- Функции для карт ---
def card_rank(card_int: int) -> int:
    if card_int == -1: return -1
    return card_int // NUM_SUITS
def card_suit(card_int: int) -> int:
    if card_int == -1: return -1
    return card_int % NUM_SUITS
def card_to_string(card_int: int) -> str:
    if card_int == -1: return "__"
    if not 0 <= card_int < NUM_CARDS: raise ValueError(f"Неверный код карты: {card_int}")
    return RANKS[card_rank(card_int)] + SUITS[card_suit(card_int)]
def string_to_card(card_str: str) -> int:
    if card_str == "__": return -1
    if len(card_str) != 2: raise ValueError(f"Неверный формат строки карты: {card_str}")
    rank_char = card_str[0].upper(); suit_char = card_str[1].lower()
    if rank_char not in RANKS or suit_char not in SUITS: raise ValueError(f"Неверный ранг или масть: {card_str}")
    rank = RANKS.index(rank_char); suit = SUITS.index(suit_char)
    return rank * NUM_SUITS + suit
def cards_to_strings(card_ints: List[int]) -> List[str]: return [card_to_string(c) for c in card_ints]
def strings_to_cards(card_strs: List[str]) -> List[int]: return [string_to_card(s) for s in card_strs]

# --- Оценка Комбинаций ---
HIGH_CARD = 0; PAIR = 1; TWO_PAIR = 2; THREE_OF_A_KIND = 3; STRAIGHT = 4; FLUSH = 5; FULL_HOUSE = 6; FOUR_OF_A_KIND = 7; STRAIGHT_FLUSH = 8
def evaluate_hand(card_ints: List[int]) -> Tuple[int, List[int]]:
    cards = [c for c in card_ints if c != -1]; n = len(cards)
    if n == 0: return (HIGH_CARD, [])
    if n < 3: return (HIGH_CARD, sorted([card_rank(c) for c in cards], reverse=True))
    if n == 4: return (HIGH_CARD, sorted([card_rank(c) for c in cards], reverse=True))
    if n not in [3, 5]: return (HIGH_CARD, sorted([card_rank(c) for c in cards], reverse=True))
    ranks = sorted([card_rank(c) for c in cards], reverse=True); suits = [card_suit(c) for c in cards]
    rank_counts = Counter(ranks); most_common_ranks = rank_counts.most_common()
    is_flush = False; is_straight = False; straight_high_card_rank = -1
    if n == 5:
        is_flush = len(set(suits)) == 1; unique_ranks = sorted(list(set(ranks)), reverse=True)
        if len(unique_ranks) >= 5:
            for i in range(len(unique_ranks) - 4):
                if all(unique_ranks[i+j] == unique_ranks[i] - j for j in range(5)): is_straight = True; straight_high_card_rank = unique_ranks[i]; break
            if not is_straight and set(unique_ranks).issuperset({12, 3, 2, 1, 0}): is_straight = True; straight_high_card_rank = 3
        if is_straight and is_flush: return (STRAIGHT_FLUSH, [straight_high_card_rank])
        if most_common_ranks[0][1] == 4: return (FOUR_OF_A_KIND, [most_common_ranks[0][0], most_common_ranks[1][0]])
        if len(most_common_ranks) > 1 and most_common_ranks[0][1] == 3 and most_common_ranks[1][1] >= 2: return (FULL_HOUSE, [most_common_ranks[0][0], most_common_ranks[1][0]])
        if is_flush: return (FLUSH, ranks)
        if is_straight: return (STRAIGHT, [straight_high_card_rank])
    if most_common_ranks[0][1] == 3: set_rank = most_common_ranks[0][0]; other_ranks = sorted([r for r in ranks if r != set_rank], reverse=True); return (THREE_OF_A_KIND, [set_rank] + other_ranks)
    if n == 5 and len(most_common_ranks) > 1 and most_common_ranks[0][1] == 2 and most_common_ranks[1][1] == 2: high_pair_rank = most_common_ranks[0][0]; low_pair_rank = most_common_ranks[1][0]; kicker_rank = most_common_ranks[2][0]; return (TWO_PAIR, [high_pair_rank, low_pair_rank, kicker_rank])
    if most_common_ranks[0][1] == 2: pair_rank = most_common_ranks[0][0]; other_ranks = sorted([r for r in ranks if r != pair_rank], reverse=True); return (PAIR, [pair_rank] + other_ranks)
    return (HIGH_CARD, ranks)

# --- Роялти и Мертвая Рука ---
TOP_ROYALTIES_PAIR = { 4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7, 11: 8, 12: 9 }
TOP_ROYALTIES_SET = { r: 10 + r for r in range(NUM_RANKS) }
MIDDLE_ROYALTIES = { THREE_OF_A_KIND: 2, STRAIGHT: 4, FLUSH: 8, FULL_HOUSE: 12, FOUR_OF_A_KIND: 20, STRAIGHT_FLUSH: 30 }
BOTTOM_ROYALTIES = { STRAIGHT: 2, FLUSH: 4, FULL_HOUSE: 6, FOUR_OF_A_KIND: 10, STRAIGHT_FLUSH: 15 }
ROYAL_FLUSH_RANK = 12
def calculate_royalties(hand_type: int, ranks: List[int], row_type: str) -> int:
    if not ranks: return 0
    if row_type == 'top':
        if hand_type == THREE_OF_A_KIND: return TOP_ROYALTIES_SET.get(ranks[0], 0)
        elif hand_type == PAIR: return TOP_ROYALTIES_PAIR.get(ranks[0], 0)
        else: return 0
    elif row_type == 'middle':
        if hand_type == STRAIGHT_FLUSH and ranks[0] == ROYAL_FLUSH_RANK: return 50
        return MIDDLE_ROYALTIES.get(hand_type, 0)
    elif row_type == 'bottom':
        if hand_type == STRAIGHT_FLUSH and ranks[0] == ROYAL_FLUSH_RANK: return 25
        return BOTTOM_ROYALTIES.get(hand_type, 0)
    else: raise ValueError(f"Неизвестный тип ряда: {row_type}")
def compare_evals(eval1: Tuple[int, List[int]], eval2: Tuple[int, List[int]]) -> int:
    type1, kickers1 = eval1; type2, kickers2 = eval2
    if type1 > type2: return 1;
    if type1 < type2: return -1
    len_kickers = min(len(kickers1), len(kickers2))
    for i in range(len_kickers):
        if kickers1[i] > kickers2[i]: return 1
        if kickers1[i] < kickers2[i]: return -1
    return 0
def is_dead_hand(top_eval: Tuple[int, List[int]], middle_eval: Tuple[int, List[int]], bottom_eval: Tuple[int, List[int]]) -> bool:
    if compare_evals(top_eval, middle_eval) > 0: return True
    if compare_evals(middle_eval, bottom_eval) > 0: return True
    return False

# --- Классы Игры и Состояния ---
_GAME_TYPE = pyspiel.GameType(short_name="ofc_pineapple", long_name="Open Face Chinese Poker Pineapple", dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL, chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC, information=pyspiel.GameType.Information.IMPERFECT_INFORMATION, utility=pyspiel.GameType.Utility.ZERO_SUM, reward_model=pyspiel.GameType.RewardModel.TERMINAL, max_num_players=NUM_PLAYERS, min_num_players=NUM_PLAYERS, provides_information_state_string=True, provides_information_state_tensor=False, provides_observation_string=True, provides_observation_tensor=False, parameter_specification={"num_players": NUM_PLAYERS})
class OFCPineappleGame(pyspiel.Game):
    def __init__(self, params: Dict[str, Any] = None):
        game_info = pyspiel.GameInfo(num_distinct_actions=-1, max_chance_outcomes=NUM_CARDS, num_players=NUM_PLAYERS, min_utility=-250.0, max_utility=250.0, max_game_length=100)
        super().__init__(_GAME_TYPE, game_info, params or {})
    def new_initial_state(self): return OFCPineappleState(self)
    def make_py_observer(self, iig_obs_type=None, params=None): return None

class OFCPineappleState(pyspiel.State):
    def __init__(self, game):
        super().__init__(game)
        self._num_players = game.num_players()
        self._dealer_button = 0
        self._next_player_to_act = (self._dealer_button + 1) % self._num_players
        self._current_player = pyspiel.PlayerId.CHANCE
        self._player_to_deal_to = self._next_player_to_act
        self._phase = STREET_PREDEAL
        self._deck = list(range(NUM_CARDS))
        np.random.shuffle(self._deck)
        self._board = [[-1] * TOTAL_CARDS_PLACED for _ in range(NUM_PLAYERS)]
        self._current_cards = [[] for _ in range(NUM_PLAYERS)] # Карты на руках
        self._discards = [[] for _ in range(NUM_PLAYERS)]
        self._cards_to_place_count = [0] * NUM_PLAYERS # Сколько карт нужно разместить на этой улице
        self._cards_to_discard_count = [0] * NUM_PLAYERS # Сколько карт нужно сбросить
        self._in_fantasy = [False] * NUM_PLAYERS
        self._fantasy_trigger = [None] * NUM_PLAYERS
        self._can_enter_fantasy = [True] * NUM_PLAYERS
        self._fantasy_cards_count = 14
        self._fantasy_player_has_placed = False
        self._total_cards_placed = [0] * NUM_PLAYERS
        self._game_over = False
        self._cumulative_returns = [0.0] * NUM_PLAYERS
        self._current_hand_returns = [0.0] * NUM_PLAYERS
        self._go_to_next_phase()

    def _go_to_next_phase(self):
        """Определяет следующую фазу игры и текущего игрока."""
        current_phase = self._phase

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
            if current_phase % 4 == 1: # DEAL P1 (e.g., 5, 9, 13, 17)
                next_phase = current_phase + 1 # -> PLACE P1
                self._current_player = self._player_to_deal_to
                self._cards_to_place_count[self._current_player] = 2
                self._cards_to_discard_count[self._current_player] = 1
            elif current_phase % 4 == 2: # PLACE P1 (e.g., 6, 10, 14, 18)
                next_phase = current_phase + 1 # -> DEAL P2
                self._current_player = pyspiel.PlayerId.CHANCE
                self._player_to_deal_to = (self._next_player_to_act + 1) % self._num_players
            elif current_phase % 4 == 3: # DEAL P2 (e.g., 7, 11, 15, 19)
                next_phase = current_phase + 1 # -> PLACE P2
                self._current_player = self._player_to_deal_to
                self._cards_to_place_count[self._current_player] = 2
                self._cards_to_discard_count[self._current_player] = 1
            elif current_phase % 4 == 0: # PLACE P2 (e.g., 8, 12, 16, 20)
                if current_phase == STREET_FIFTH_PLACE_P2:
                    next_phase = STREET_REGULAR_SHOWDOWN
                    self._current_player = pyspiel.PlayerId.TERMINAL # Переходим к подсчету
                    self._calculate_final_returns() # Считаем очки
                    # TODO: Проверить Fantasy
                    if not any(self._in_fantasy): # Если никто не в Fantasy
                         self._game_over = True
                else:
                    next_phase = current_phase + 1 # -> DEAL P1 (след. улица)
                    self._current_player = pyspiel.PlayerId.CHANCE
                    self._player_to_deal_to = self._next_player_to_act
        # TODO: Добавить логику переходов для Fantasy
        else:
             print(f"Предупреждение: Необработанный переход из фазы {current_phase}")
             self._game_over = True
             self._current_player = pyspiel.PlayerId.TERMINAL

        self._phase = next_phase

    def current_player(self):
        return self._current_player

    def is_chance_node(self):
        return self._current_player == pyspiel.PlayerId.CHANCE

    def _legal_actions(self, player):
        """Генерирует список легальных действий (кортежей)."""
        actions = []
        if self.is_chance_node() or self.is_terminal() or self._current_player != player:
            return []

        # Действия доступны только в фазах PLACE
        is_place_phase = (self._phase >= STREET_FIRST_PLACE_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 == 0) or \
                         (self._phase == PHASE_FANTASY_F_PLACEMENT) or \
                         (self._phase >= PHASE_FANTASY_N_STREET_1 and self._phase <= PHASE_FANTASY_N_STREET_5)

        if not is_place_phase:
            return [] # Нет действий в фазах DEAL или SHOWDOWN

        my_cards = self._current_cards[player]
        num_cards_in_hand = len(my_cards)
        num_to_place = self._cards_to_place_count[player]
        num_to_discard = self._cards_to_discard_count[player]

        # Если карт на руке не соответствует ожиданиям фазы, действий нет
        if num_cards_in_hand != num_to_place + num_to_discard:
            # Это может случиться, если мы пытаемся получить действия до сдачи карт
            # print(f"Предупреждение: Несоответствие карт на руке ({num_cards_in_hand}) и ожиданий фазы ({num_to_place}+{num_to_discard}) для P{player} в фазе {self._phase}")
            return []

        free_slots_indices = [i for i, card in enumerate(self._board[player]) if card == -1]
        num_free_slots = len(free_slots_indices)

        if num_free_slots < num_to_place:
            return [] # Некуда ставить

        # --- Генерация действий ---
        if num_to_discard == 0: # Улица 1 или Fantasy F/N1
            # Нужно разместить все карты с руки (num_to_place штук)
            if num_cards_in_hand != num_to_place: return [] # Проверка
            # Генерируем все перестановки карт по num_to_place свободным слотам
            for slots in itertools.permutations(free_slots_indices, num_to_place):
                 # Действие = ((карта0, слот0), (карта1, слот1), ...)
                 action = tuple((my_cards[i], slots[i]) for i in range(num_to_place))
                 actions.append(action)
        else: # Улицы 2-5 (num_to_place=2, num_to_discard=1)
            if num_to_place != 2 or num_to_discard != 1: return [] # Проверка
            # Перебираем все комбинации: выбрать 2 карты из 3, выбрать 2 слота из свободных
            for cards_to_place_indices in itertools.combinations(range(num_cards_in_hand), num_to_place):
                cards_to_place = [my_cards[i] for i in cards_to_place_indices]
                # Находим индекс карты для сброса
                discard_index = list(set(range(num_cards_in_hand)) - set(cards_to_place_indices))[0]
                card_discard = my_cards[discard_index]

                for slots in itertools.permutations(free_slots_indices, num_to_place):
                    # Действие = ( ((карта1, слот1), (карта2, слот2)), карта_сброс )
                    placement = tuple((cards_to_place[i], slots[i]) for i in range(num_to_place))
                    action = (placement, card_discard)
                    actions.append(action)

        # TODO: Добавить фильтрацию действий, которые немедленно приводят к мертвой руке?
        # Это может быть вычислительно дорого, возможно, лучше оставить на MCTS/Evaluator

        # Преобразуем действия в уникальные целые числа (если нужно для pyspiel)
        # Пока возвращаем список кортежей
        return actions

    def _apply_action(self, action):
        """Применяет действие (размещение карт) или исход шанса."""
        if self.is_chance_node():
            player = self._player_to_deal_to
            num_cards_to_deal = 0
            if self._phase in [STREET_FIRST_DEAL_P1, STREET_FIRST_DEAL_P2]: num_cards_to_deal = 5
            elif (self._phase >= STREET_SECOND_DEAL_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 != 0): num_cards_to_deal = 3
            # TODO: Добавить сдачу для Fantasy

            if num_cards_to_deal > 0:
                 if len(self._deck) < num_cards_to_deal: raise Exception("Недостаточно карт в колоде!")
                 self._current_cards[player] = [self._deck.pop() for _ in range(num_cards_to_deal)]
            self._go_to_next_phase()
            return

        if self.is_terminal(): raise ValueError("Cannot apply action on terminal node")
        if self.is_chance_node(): raise ValueError("Cannot apply player action on chance node")

        player = self._current_player
        placement = []
        card_discard = -1
        num_placed = 0

        # Распарсиваем действие
        if self._phase in [STREET_FIRST_PLACE_P1, STREET_FIRST_PLACE_P2]:
            if not isinstance(action, tuple) or len(action) != 5: raise ValueError(f"Неверный формат действия для 1й улицы: {action}")
            placement = list(action)
            num_placed = 5
        elif (self._phase >= STREET_SECOND_PLACE_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 == 0):
            if not isinstance(action, tuple) or len(action) != 2 or not isinstance(action[0], tuple) or len(action[0]) != 2: raise ValueError(f"Неверный формат действия для улиц 2-5: {action}")
            placement = list(action[0])
            card_discard = action[1]
            num_placed = 2
        # TODO: Добавить распарсер для Fantasy

        else: raise ValueError(f"Применение действия в неизвестной фазе: {self._phase}")

        # Проверяем карты (опционально, т.к. _legal_actions должна генерировать только валидные)
        action_cards = set(c for c, s in placement)
        original_hand = set(self._current_cards[player])
        if card_discard != -1: action_cards.add(card_discard)
        # Проверяем, что все карты действия были на руке
        if not action_cards.issubset(original_hand):
             raise ValueError(f"Действие использует карты не из руки! Рука:{original_hand}, Действие:{action_cards}")
        # Проверяем, что количество карт совпадает
        if len(action_cards) != len(original_hand):
             raise ValueError(f"Неверное количество карт в действии! Рука:{len(original_hand)}, Действие:{len(action_cards)}")


        # Обновляем доску
        for card, slot_idx in placement:
            if not (0 <= slot_idx < TOTAL_CARDS_PLACED): raise ValueError(f"Неверный индекс слота: {slot_idx}")
            if self._board[player][slot_idx] != -1: raise ValueError(f"Слот {slot_idx} уже занят!")
            self._board[player][slot_idx] = card

        # Обновляем сброс
        if card_discard != -1:
            self._discards[player].append(card_discard)

        # Очищаем руку и обновляем счетчики
        self._current_cards[player] = []
        self._total_cards_placed[player] += num_placed
        self._cards_to_place_count[player] = 0 # Обнуляем счетчики для текущего игрока
        self._cards_to_discard_count[player] = 0

        # Переходим к следующей фазе
        self._go_to_next_phase()

    def _action_to_string(self, player, action):
        """Преобразует действие (кортеж) в строку."""
        # TODO: Сделать более читаемым
        if isinstance(action, tuple):
             if len(action) == 5: # Улица 1
                 return "Place1 " + " ".join([f"{card_to_string(c)}({s})" for c,s in action])
             elif len(action) == 2 and isinstance(action[0], tuple): # Улицы 2-5
                 placement_str = " ".join([f"{card_to_string(c)}({s})" for c,s in action[0]])
                 discard_str = card_to_string(action[1])
                 return f"Place2 {placement_str} Discard {discard_str}"
             # TODO: Добавить формат для Fantasy
        return str(action) # По умолчанию

    def is_terminal(self):
        return self._game_over

    def _calculate_final_returns(self):
        """Рассчитывает очки за текущую руку и обновляет кумулятивные очки."""
        if not all(count == TOTAL_CARDS_PLACED for count in self._total_cards_placed):
            print("Предупреждение: Попытка рассчитать очки до завершения руки.")
            self._current_hand_returns = [0.0] * NUM_PLAYERS # Не начисляем очки
            return

        scores = [0] * NUM_PLAYERS; royalties = [0] * NUM_PLAYERS
        is_dead = [False] * NUM_PLAYERS; evals = [{}, {}, {}]

        for p in range(NUM_PLAYERS):
            top_hand = self._board[p][TOP_SLOTS[0]:TOP_SLOTS[-1]+1]
            middle_hand = self._board[p][MIDDLE_SLOTS[0]:MIDDLE_SLOTS[-1]+1]
            bottom_hand = self._board[p][BOTTOM_SLOTS[0]:BOTTOM_SLOTS[-1]+1]
            evals[p]['top'] = evaluate_hand(top_hand)
            evals[p]['middle'] = evaluate_hand(middle_hand)
            evals[p]['bottom'] = evaluate_hand(bottom_hand)
            is_dead[p] = is_dead_hand(evals[p]['top'], evals[p]['middle'], evals[p]['bottom'])
            if not is_dead[p]:
                royalties[p] += calculate_royalties(evals[p]['top'][0], evals[p]['top'][1], 'top')
                royalties[p] += calculate_royalties(evals[p]['middle'][0], evals[p]['middle'][1], 'middle')
                royalties[p] += calculate_royalties(evals[p]['bottom'][0], evals[p]['bottom'][1], 'bottom')

        p0 = 0; p1 = 1; line_wins = 0
        if is_dead[p0]:
            if not is_dead[p1]: scores[p0] -= 6; scores[p1] += 6
        elif is_dead[p1]: scores[p0] += 6; scores[p1] -= 6
        else:
            comp_t = compare_evals(evals[p0]['top'], evals[p1]['top'])
            comp_m = compare_evals(evals[p0]['middle'], evals[p1]['middle'])
            comp_b = compare_evals(evals[p0]['bottom'], evals[p1]['bottom'])
            line_wins = comp_t + comp_m + comp_b
            scores[p0] += line_wins; scores[p1] -= line_wins
            if line_wins == 3: scores[p0] += 3; scores[p1] -= 3
            elif line_wins == -3: scores[p0] -= 3; scores[p1] += 3

        if not is_dead[p0]: scores[p0] += royalties[p0]
        if not is_dead[p1]: scores[p1] += royalties[p1]

        diff = scores[0] - scores[1]
        self._current_hand_returns = [diff, -diff]
        self._cumulative_returns[0] += diff
        self._cumulative_returns[1] -= diff

    def returns(self):
        """Возвращает накопленные очки за весь матч."""
        if not self._game_over: return [0.0] * self._num_players
        return self._cumulative_returns

    def information_state_string(self, player):
        """Возвращает строку информации, доступную игроку."""
        parts = []
        parts.append(f"P:{player}")
        parts.append(f"Phase:{self._phase}")
        parts.append(f"Board:[{' '.join(cards_to_strings(self._board[player]))}]")
        parts.append(f"Hand:[{' '.join(cards_to_strings(self._current_cards[player]))}]")
        parts.append(f"Discard:[{' '.join(cards_to_strings(self._discards[player]))}]")
        opponent = 1 - player
        opponent_board_str = f"OppBoard:[{' '.join(cards_to_strings(self._board[opponent]))}]"
        is_fantasy_phase = self._phase >= PHASE_FANTASY_DEAL and self._phase <= PHASE_FANTASY_SHOWDOWN
        i_am_fantasy = self._in_fantasy[player]
        show_opp_board = not is_fantasy_phase
        if show_opp_board: parts.append(opponent_board_str)
        else: parts.append("OppBoard:[HIDDEN]")
        if self._phase >= STREET_FIRST_DEAL_P1 and self._phase <= STREET_FIRST_PLACE_P2:
             opponent_hand_str = f"OppHand:[{' '.join(cards_to_strings(self._current_cards[opponent]))}]"
             parts.append(opponent_hand_str)
        parts.append(f"Fantasy:[{int(self._in_fantasy[0])}{int(self._in_fantasy[1])}]")
        # Добавим информацию о том, сколько карт нужно разместить/сбросить
        parts.append(f"Place:{self._cards_to_place_count[player]}")
        parts.append(f"Discard:{self._cards_to_discard_count[player]}")
        return " ".join(parts)

    def observation_string(self, player):
        return self.information_state_string(player)

    def clone(self):
        cloned = OFCPineappleState(self._game)
        cloned._current_player = self._current_player
        cloned._dealer_button = self._dealer_button
        cloned._next_player_to_act = self._next_player_to_act
        cloned._player_to_deal_to = self._player_to_deal_to
        cloned._phase = self._phase
        cloned._deck = self._deck[:]
        cloned._board = [row[:] for row in self._board]
        cloned._current_cards = [cards[:] for cards in self._current_cards]
        cloned._discards = [cards[:] for cards in self._discards]
        cloned._cards_to_place_count = self._cards_to_place_count[:] # Добавлено
        cloned._cards_to_discard_count = self._cards_to_discard_count[:] # Добавлено
        cloned._in_fantasy = self._in_fantasy[:]
        cloned._fantasy_trigger = self._fantasy_trigger[:]
        cloned._can_enter_fantasy = self._can_enter_fantasy[:]
        cloned._fantasy_cards_count = self._fantasy_cards_count
        cloned._fantasy_player_has_placed = self._fantasy_player_has_placed
        cloned._total_cards_placed = self._total_cards_placed[:]
        # cloned._player_confirmed_action - не нужно копировать? Это флаг текущего хода
        cloned._game_over = self._game_over
        cloned._cumulative_returns = self._cumulative_returns[:]
        cloned._current_hand_returns = self._current_hand_returns[:]
        return cloned

    def resample_from_infostate(self, player_id, probability_sampler):
        # TODO: Реализовать
        return self.clone() # Placeholder

    def __str__(self):
        player = self.current_player()
        if player < 0: player = 0
        return self.information_state_string(player)

# --- Регистрация игры ---
try:
    pyspiel.load_game(_GAME_TYPE.short_name)
except pyspiel.SpielError:
    pyspiel.register_game(_GAME_TYPE, OFCPineappleGame)
    print(f"Игра '{_GAME_TYPE.short_name}' успешно зарегистрирована.")
except Exception as e:
     print(f"Неожиданная ошибка при проверке/регистрации игры: {e}")
