# OFC Pineapple Poker Game Implementation for OpenSpiel
# Версия с НАЧАЛОМ реализации Fantasyland (v15 - триггер и переход в setup)

import pyspiel
import numpy as np
from typing import List, Tuple, Any, Dict, Optional, Set
import itertools
from collections import Counter
import copy
import random # Используется в resample_from_infostate

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

# Фазы обычной игры
STREET_PREDEAL = 0
STREET_FIRST_DEAL_P1 = 1; STREET_FIRST_PLACE_P1 = 2
STREET_FIRST_DEAL_P2 = 3; STREET_FIRST_PLACE_P2 = 4
STREET_SECOND_DEAL_P1 = 5; STREET_SECOND_PLACE_P1 = 6
STREET_SECOND_DEAL_P2 = 7; STREET_SECOND_PLACE_P2 = 8
STREET_THIRD_DEAL_P1 = 9; STREET_THIRD_PLACE_P1 = 10
STREET_THIRD_DEAL_P2 = 11; STREET_THIRD_PLACE_P2 = 12
STREET_FOURTH_DEAL_P1 = 13; STREET_FOURTH_PLACE_P1 = 14
STREET_FOURTH_DEAL_P2 = 15; STREET_FOURTH_PLACE_P2 = 16
STREET_FIFTH_DEAL_P1 = 17; STREET_FIFTH_PLACE_P1 = 18
STREET_FIFTH_DEAL_P2 = 19; STREET_FIFTH_PLACE_P2 = 20
STREET_REGULAR_SHOWDOWN = 21 # Фаза после подсчета очков (терминальная или переход к Fantasy)

# Фазы Fantasyland (N - Normal player, F - Fantasy player)
PHASE_FANTASY_SETUP = 30 # Определяем кто F, кто N
PHASE_FANTASY_N_DEAL_1 = 31; PHASE_FANTASY_N_PLACE_1 = 32
PHASE_FANTASY_N_DEAL_2 = 33; PHASE_FANTASY_N_PLACE_2 = 34
PHASE_FANTASY_N_DEAL_3 = 35; PHASE_FANTASY_N_PLACE_3 = 36
PHASE_FANTASY_N_DEAL_4 = 37; PHASE_FANTASY_N_PLACE_4 = 38
PHASE_FANTASY_N_DEAL_5 = 39; PHASE_FANTASY_N_PLACE_5 = 40
PHASE_FANTASY_F_DEAL = 41 # Сдача карт игроку F
PHASE_FANTASY_F_PLACE = 42 # Размещение карт игроком F
PHASE_FANTASY_SHOWDOWN = 43 # Подсчет очков Fantasy, проверка Re-Fantasy

DISCARD_SLOT = -1
RANKS = "23456789TJQKA"
SUITS = "shdc"
FANTASY_TRIGGER_RANK = 10 # Дама (индекс 10 в RANKS)

# --- Функции для карт ---
# ... (Без изменений) ...
def card_rank(card_int: int) -> int:
    if card_int == -1: return -1;
    if card_int is None: raise TypeError("card_rank получила None вместо int")
    return card_int // NUM_SUITS
def card_suit(card_int: int) -> int:
    if card_int == -1: return -1;
    if card_int is None: raise TypeError("card_suit получила None вместо int")
    return card_int % NUM_SUITS
def card_to_string(card_int: int) -> str:
    if card_int == -1: return "__";
    if card_int is None: return "NN"
    if not 0 <= card_int < NUM_CARDS: raise ValueError(f"Неверный код карты: {card_int}")
    rank_idx = card_rank(card_int); suit_idx = card_suit(card_int)
    if rank_idx < 0 or rank_idx >= len(RANKS): raise ValueError(f"Неверный ранг {rank_idx} для карты {card_int}")
    if suit_idx < 0 or suit_idx >= len(SUITS): raise ValueError(f"Неверная масть {suit_idx} для карты {card_int}")
    return RANKS[rank_idx] + SUITS[suit_idx]
def string_to_card(card_str: str) -> int:
    if card_str == "__": return -1;
    if card_str is None: raise TypeError("string_to_card получила None")
    if len(card_str) != 2: raise ValueError(f"Неверный формат строки карты: {card_str}")
    rank_char = card_str[0].upper(); suit_char = card_str[1].lower()
    if rank_char not in RANKS or suit_char not in SUITS: raise ValueError(f"Неверный ранг или масть: {card_str}")
    rank = RANKS.index(rank_char); suit = SUITS.index(suit_char); return rank * NUM_SUITS + suit
def cards_to_strings(card_ints: List[Optional[int]]) -> List[str]: return [card_to_string(c) if c is not None else "NN" for c in card_ints]
def strings_to_cards(card_strs: List[str]) -> List[int]: return [string_to_card(s) for s in card_strs]

# --- Оценка Комбинаций ---
# ... (Без изменений) ...
HIGH_CARD = 0; PAIR = 1; TWO_PAIR = 2; THREE_OF_A_KIND = 3; STRAIGHT = 4; FLUSH = 5; FULL_HOUSE = 6; FOUR_OF_A_KIND = 7; STRAIGHT_FLUSH = 8
def evaluate_hand(card_ints: List[Optional[int]]) -> Tuple[int, List[int]]:
    cards = [c for c in card_ints if c is not None and c != -1]; n = len(cards)
    if n == 0: return (HIGH_CARD, [])
    ranks = sorted([card_rank(c) for c in cards], reverse=True)
    if n < 3: return (HIGH_CARD, ranks)
    if n == 4: return (HIGH_CARD, ranks)
    if n not in [3, 5]: return (HIGH_CARD, ranks)
    suits = [card_suit(c) for c in cards]; rank_counts = Counter(ranks); most_common_ranks = rank_counts.most_common()
    is_flush = False; is_straight = False; straight_high_card_rank = -1
    if n == 5:
        is_flush = len(set(suits)) == 1; unique_ranks = sorted(list(set(ranks)), reverse=True)
        if len(unique_ranks) >= 5:
            for i in range(len(unique_ranks) - 4):
                if all(unique_ranks[i+j] == unique_ranks[i] - j for j in range(5)): is_straight = True; straight_high_card_rank = unique_ranks[i]; break
            if not is_straight and set(unique_ranks).issuperset({12, 3, 2, 1, 0}): is_straight = True; straight_high_card_rank = 3
        if is_straight and is_flush: return (STRAIGHT_FLUSH, [straight_high_card_rank])
        if most_common_ranks[0][1] == 4: kicker = most_common_ranks[1][0] if len(most_common_ranks) > 1 else -1; return (FOUR_OF_A_KIND, [most_common_ranks[0][0], kicker])
        if len(most_common_ranks) > 1 and most_common_ranks[0][1] == 3 and most_common_ranks[1][1] >= 2: return (FULL_HOUSE, [most_common_ranks[0][0], most_common_ranks[1][0]])
        if is_flush: return (FLUSH, ranks)
        if is_straight: return (STRAIGHT, [straight_high_card_rank])
    if most_common_ranks[0][1] == 3: set_rank = most_common_ranks[0][0]; other_ranks = sorted([r for r in ranks if r != set_rank], reverse=True); return (THREE_OF_A_KIND, [set_rank] + other_ranks)
    if n == 5 and len(most_common_ranks) > 1 and most_common_ranks[0][1] == 2 and most_common_ranks[1][1] == 2: high_pair_rank = most_common_ranks[0][0]; low_pair_rank = most_common_ranks[1][0]; kicker_rank = most_common_ranks[2][0] if len(most_common_ranks) > 2 else -1; return (TWO_PAIR, [high_pair_rank, low_pair_rank, kicker_rank])
    if most_common_ranks[0][1] == 2: pair_rank = most_common_ranks[0][0]; other_ranks = sorted([r for r in ranks if r != pair_rank], reverse=True); return (PAIR, [pair_rank] + other_ranks)
    return (HIGH_CARD, ranks)

# --- Роялти и Мертвая Рука ---
# ... (Без изменений) ...
TOP_ROYALTIES_PAIR = { 4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7, 11: 8, 12: 9 }
TOP_ROYALTIES_SET = { r: 10 + r for r in range(NUM_RANKS) }
MIDDLE_ROYALTIES = { THREE_OF_A_KIND: 2, STRAIGHT: 4, FLUSH: 8, FULL_HOUSE: 12, FOUR_OF_A_KIND: 20, STRAIGHT_FLUSH: 30 }
BOTTOM_ROYALTIES = { STRAIGHT: 2, FLUSH: 4, FULL_HOUSE: 6, FOUR_OF_A_KIND: 10, STRAIGHT_FLUSH: 15 }
ROYAL_FLUSH_RANK = 12
def calculate_royalties(hand_type: int, ranks: List[int], row_type: str) -> int:
    if not ranks: return 0;
    if any(r is None for r in ranks): raise TypeError(f"calculate_royalties получила None в списке рангов: {ranks}")
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
    if eval1 is None or eval2 is None: raise TypeError("compare_evals получила None")
    type1, kickers1 = eval1; type2, kickers2 = eval2
    if type1 is None or type2 is None: raise TypeError("compare_evals получила None в типе руки")
    if kickers1 is None or kickers2 is None: raise TypeError("compare_evals получила None в кикерах")
    if any(k is None for k in kickers1) or any(k is None for k in kickers2): raise TypeError("compare_evals получила None в списке кикеров")
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
# ... (GameType и OFCPineappleGame без изменений) ...
_GAME_TYPE = pyspiel.GameType(short_name="ofc_pineapple", long_name="Open Face Chinese Poker Pineapple", dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL, chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC, information=pyspiel.GameType.Information.IMPERFECT_INFORMATION, utility=pyspiel.GameType.Utility.ZERO_SUM, reward_model=pyspiel.GameType.RewardModel.TERMINAL, max_num_players=NUM_PLAYERS, min_num_players=NUM_PLAYERS, provides_information_state_string=True, provides_information_state_tensor=False, provides_observation_string=True, provides_observation_tensor=False, parameter_specification={"num_players": NUM_PLAYERS})
class OFCPineappleGame(pyspiel.Game):
    def __init__(self, params: Dict[str, Any] = None):
        game_info = pyspiel.GameInfo(num_distinct_actions=-1, max_chance_outcomes=NUM_CARDS, num_players=NUM_PLAYERS, min_utility=-250.0, max_utility=250.0, max_game_length=150) # Увеличено для Fantasy
        super().__init__(_GAME_TYPE, game_info, params or {})
    def new_initial_state(self): return OFCPineappleState(self)
    def make_py_observer(self, iig_obs_type=None, params=None): return None

class OFCPineappleState(pyspiel.State):
    # ИЗМЕНЕНО v15: Добавлены переменные Fantasyland
    def __init__(self, game):
        super().__init__(game)
        self._num_players = game.num_players(); self._dealer_button = 0
        self._next_player_to_act = (self._dealer_button + 1) % self._num_players
        self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = self._next_player_to_act
        self._phase = STREET_PREDEAL; self._deck = list(range(NUM_CARDS)); np.random.shuffle(self._deck)
        self._board = [[-1] * TOTAL_CARDS_PLACED for _ in range(NUM_PLAYERS)]
        self._current_cards = [[] for _ in range(NUM_PLAYERS)]; self._discards = [[] for _ in range(NUM_PLAYERS)]
        self._cards_to_place_count = [0] * NUM_PLAYERS; self._cards_to_discard_count = [0] * NUM_PLAYERS
        self._total_cards_placed = [0] * NUM_PLAYERS; self._game_over = False
        self._cumulative_returns = [0.0] * NUM_PLAYERS; self._current_hand_returns = [0.0] * NUM_PLAYERS
        self._cached_legal_actions: Optional[List[Any]] = None
        # --- Переменные Fantasyland ---
        self._is_fantasy_hand = False
        self._next_fantasy_players: List[int] = [] # Кто войдет в Fantasy в *следующей* руке
        self._current_fantasy_player: Optional[int] = None # Кто F *в этой* руке
        self._current_normal_player: Optional[int] = None # Кто N *в этой* руке
        self._fantasy_cards_count = 14
        # --- ---
        self._go_to_next_phase()

    def _clear_cache(self): self._cached_legal_actions = None

    # ИЗМЕНЕНО v15: Добавлена логика перехода в Fantasyland
    def _go_to_next_phase(self):
        self._clear_cache(); current_phase = self._phase; next_phase = -1

        # --- Логика обычной игры ---
        if current_phase >= STREET_PREDEAL and current_phase < STREET_REGULAR_SHOWDOWN:
            if current_phase == STREET_PREDEAL: next_phase = STREET_FIRST_DEAL_P1; self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = self._next_player_to_act
            elif current_phase == STREET_FIRST_DEAL_P1: next_phase = STREET_FIRST_PLACE_P1; self._current_player = self._player_to_deal_to; self._cards_to_place_count[self._current_player] = 5; self._cards_to_discard_count[self._current_player] = 0
            elif current_phase == STREET_FIRST_PLACE_P1: next_phase = STREET_FIRST_DEAL_P2; self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = (self._next_player_to_act + 1) % self._num_players
            elif current_phase == STREET_FIRST_DEAL_P2: next_phase = STREET_FIRST_PLACE_P2; self._current_player = self._player_to_deal_to; self._cards_to_place_count[self._current_player] = 5; self._cards_to_discard_count[self._current_player] = 0
            elif current_phase == STREET_FIRST_PLACE_P2: next_phase = STREET_SECOND_DEAL_P1; self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = self._next_player_to_act
            elif current_phase >= STREET_SECOND_DEAL_P1: # Улицы 2-5
                if current_phase % 2 != 0: # DEAL phase -> PLACE phase
                    next_phase = current_phase + 1; self._current_player = self._player_to_deal_to; self._cards_to_place_count[self._current_player] = 2; self._cards_to_discard_count[self._current_player] = 1
                else: # PLACE phase
                    current_player_index = (current_phase - STREET_FIRST_PLACE_P1) // 2 % NUM_PLAYERS; is_p1_phase = current_player_index == 0; is_p2_phase = not is_p1_phase
                    if is_p1_phase: next_phase = current_phase + 1; self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = (self._next_player_to_act + 1) % self._num_players
                    elif is_p2_phase:
                        if current_phase == STREET_FIFTH_PLACE_P2:
                            next_phase = STREET_REGULAR_SHOWDOWN; self._current_player = pyspiel.PlayerId.TERMINAL # Переход к шоудауну
                        else:
                            next_phase = current_phase + 1; self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = self._next_player_to_act

        # --- Логика Шоудауна и перехода к Fantasy/Концу игры ---
        elif current_phase == STREET_REGULAR_SHOWDOWN:
            self._calculate_final_returns() # Считаем очки за обычную руку
            fantasy_triggered = self._check_and_setup_fantasy() # Проверяем и устанавливаем _next_fantasy_players
            if fantasy_triggered:
                next_phase = PHASE_FANTASY_SETUP # Переходим к настройке Fantasy
                self._current_player = pyspiel.PlayerId.TERMINAL # Переходный узел
                self._reset_for_new_hand(keep_fantasy_status=True) # Сбрасываем доски/руки/колоду, но сохраняем статус Fantasy
            else:
                # Нет Fantasy, эта рука (и симуляция) завершена.
                self._game_over = True
                next_phase = current_phase # Остаемся в терминальной фазе
                self._current_player = pyspiel.PlayerId.TERMINAL

        # --- Логика Fantasyland ---
        elif current_phase == PHASE_FANTASY_SETUP:
            if len(self._next_fantasy_players) == 1:
                self._current_fantasy_player = self._next_fantasy_players[0]
                self._current_normal_player = 1 - self._current_fantasy_player
                self._is_fantasy_hand = True
                print(f"Fantasyland начался! Игрок F: {self._current_fantasy_player}, Игрок N: {self._current_normal_player}")
                # Начинает игрок N
                next_phase = PHASE_FANTASY_N_DEAL_1
                self._current_player = pyspiel.PlayerId.CHANCE
                self._player_to_deal_to = self._current_normal_player
            elif len(self._next_fantasy_players) == 2:
                 print("Warning: Случай с двумя игроками в Fantasy пока не реализован."); self._game_over = True; next_phase = current_phase
            else: # Никто не в Fantasy, ошибка логики
                 print("Warning: Ошибка в PHASE_FANTASY_SETUP, нет игроков для Fantasy."); self._game_over = True; next_phase = current_phase

        elif current_phase >= PHASE_FANTASY_N_DEAL_1 and current_phase <= PHASE_FANTASY_N_PLACE_5:
            street_num = (current_phase - PHASE_FANTASY_N_DEAL_1) // 2 + 1; is_deal_phase = current_phase % 2 != 0
            if is_deal_phase: # DEAL -> PLACE
                next_phase = current_phase + 1; self._current_player = self._current_normal_player
                if street_num == 1: self._cards_to_place_count[self._current_player] = 5; self._cards_to_discard_count[self._current_player] = 0
                else: self._cards_to_place_count[self._current_player] = 2; self._cards_to_discard_count[self._current_player] = 1
            else: # PLACE -> DEAL (next street or F_DEAL)
                if current_phase == PHASE_FANTASY_N_PLACE_5: next_phase = PHASE_FANTASY_F_DEAL; self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = self._current_fantasy_player
                else: next_phase = current_phase + 1; self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = self._current_normal_player

        elif current_phase == PHASE_FANTASY_F_DEAL:
            # TODO: Реализовать логику для PHASE_FANTASY_F_DEAL
            print(f"Warning: Фаза {current_phase} не реализована, завершаем игру.")
            self._game_over = True; next_phase = current_phase; self._current_player = pyspiel.PlayerId.TERMINAL
            # next_phase = PHASE_FANTASY_F_PLACE; self._current_player = self._current_fantasy_player
            # self._cards_to_place_count[self._current_player] = 13; self._cards_to_discard_count[self._current_player] = 1

        elif current_phase == PHASE_FANTASY_F_PLACE:
            # TODO: Реализовать логику для PHASE_FANTASY_F_PLACE
            print(f"Warning: Фаза {current_phase} не реализована, завершаем игру.")
            self._game_over = True; next_phase = current_phase; self._current_player = pyspiel.PlayerId.TERMINAL
            # next_phase = PHASE_FANTASY_SHOWDOWN; self._current_player = pyspiel.PlayerId.TERMINAL

        elif current_phase == PHASE_FANTASY_SHOWDOWN:
            # TODO: Реализовать логику для PHASE_FANTASY_SHOWDOWN
            print(f"Warning: Фаза {current_phase} не реализована, завершаем игру.")
            self._game_over = True; next_phase = current_phase; self._current_player = pyspiel.PlayerId.TERMINAL
            # self._calculate_final_returns() # Считаем очки за Fantasy раунд
            # re_fantasy_triggered = False # Заглушка
            # if re_fantasy_triggered:
            #      next_phase = PHASE_FANTASY_SETUP; self._current_player = pyspiel.PlayerId.TERMINAL
            #      self._reset_for_new_hand(keep_fantasy_status=True)
            # else:
            #      self._dealer_button = (self._dealer_button + 1) % self._num_players
            #      self._next_player_to_act = (self._dealer_button + 1) % self._num_players
            #      self._reset_for_new_hand(); next_phase = STREET_FIRST_DEAL_P1
            #      self._current_player = pyspiel.PlayerId.CHANCE; self._player_to_deal_to = self._next_player_to_act

        # --- Обработка конца игры или неизвестной фазы ---
        else:
             if not self._game_over: self._game_over = True; self._current_player = pyspiel.PlayerId.TERMINAL
             next_phase = current_phase

        self._phase = next_phase

    # ИЗМЕНЕНО v12: Добавлен метод _reset_for_new_hand
    def _reset_for_new_hand(self, keep_fantasy_status=False):
        """Сбрасывает состояние для начала новой руки."""
        self._deck = list(range(NUM_CARDS)); np.random.shuffle(self._deck)
        self._board = [[-1] * TOTAL_CARDS_PLACED for _ in range(NUM_PLAYERS)]
        self._current_cards = [[] for _ in range(NUM_PLAYERS)]; self._discards = [[] for _ in range(NUM_PLAYERS)]
        self._cards_to_place_count = [0] * NUM_PLAYERS; self._cards_to_discard_count = [0] * NUM_PLAYERS
        self._total_cards_placed = [0] * NUM_PLAYERS; self._current_hand_returns = [0.0] * NUM_PLAYERS
        self._cached_legal_actions = None; self._is_fantasy_hand = False
        self._current_fantasy_player = None; self._current_normal_player = None
        if not keep_fantasy_status:
            self._next_fantasy_players = []
            # self._in_fantasy больше не используется для отслеживания следующей руки

    def current_player(self): return self._current_player
    def is_chance_node(self): return self._current_player == pyspiel.PlayerId.CHANCE
    def is_terminal(self): return self._game_over
    def legal_actions(self, player: Optional[int] = None) -> List[int]:
        # ИСПРАВЛЕНО v15: Корректная проверка player_for_actions
        current_player = self.current_player()
        if player is None: player_for_actions = current_player
        else: player_for_actions = player
        is_valid_player_id = isinstance(player_for_actions, int) and 0 <= player_for_actions < self._num_players
        if not is_valid_player_id or \
           player_for_actions != current_player or \
           self.is_chance_node() or \
           self.is_terminal():
            return []
        if self._cached_legal_actions is not None: return list(range(len(self._cached_legal_actions)))
        actions_tuples = self._generate_legal_actions_tuples(player_for_actions)
        self._cached_legal_actions = actions_tuples
        return list(range(len(actions_tuples)))

    # ИЗМЕНЕНО v15: Добавлена обработка фаз Fantasyland N
    def _generate_legal_actions_tuples(self, player):
        actions = []
        is_normal_place_phase = (self._phase >= STREET_FIRST_PLACE_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 == 0)
        is_fantasy_n_place_phase = (self._phase >= PHASE_FANTASY_N_PLACE_1 and self._phase <= PHASE_FANTASY_N_PLACE_5 and self._phase % 2 == 0)
        is_fantasy_f_place_phase = (self._phase == PHASE_FANTASY_F_PLACE)

        if not (is_normal_place_phase or is_fantasy_n_place_phase or is_fantasy_f_place_phase): return []

        my_cards = self._current_cards[player]; num_cards_in_hand = len(my_cards)
        num_to_place = self._cards_to_place_count[player]; num_to_discard = self._cards_to_discard_count[player]
        if num_cards_in_hand != num_to_place + num_to_discard: return []
        free_slots_indices = [i for i, card in enumerate(self._board[player]) if card == -1]; num_free_slots = len(free_slots_indices)
        if num_free_slots < num_to_place: return []

        if is_normal_place_phase or is_fantasy_n_place_phase:
            if num_to_discard == 0: # Улица 1 (обычная или N в Fantasy)
                if num_cards_in_hand != 5 or num_to_place != 5: return []
                for slots in itertools.permutations(free_slots_indices, num_to_place):
                     action = tuple((my_cards[i], slots[i]) for i in range(num_to_place)); actions.append(action)
            else: # Улицы 2-5 (обычная или N в Fantasy)
                if num_cards_in_hand != 3 or num_to_place != 2 or num_to_discard != 1: return []
                for discard_idx in range(num_cards_in_hand):
                    card_discard = my_cards[discard_idx]; cards_to_place = my_cards[:discard_idx] + my_cards[discard_idx+1:]
                    for slots in itertools.permutations(free_slots_indices, num_to_place):
                        placement = tuple((cards_to_place[i], slots[i]) for i in range(num_to_place)); action = (placement, card_discard); actions.append(action)
        elif is_fantasy_f_place_phase:
             if num_cards_in_hand != self._fantasy_cards_count or num_to_place != 13 or num_to_discard != 1: print(f"Warning: Несоответствие карт для Fantasy F: рука={num_cards_in_hand}, надо_мест={num_to_place}, надо_сброс={num_to_discard}"); return []
             print("Warning: Генерация действий Fantasyland F не реализована, возвращено фиктивное действие.")
             if free_slots_indices and len(free_slots_indices) >= 13 and my_cards:
                 placement = tuple((my_cards[i], free_slots_indices[i]) for i in range(13)); discard = my_cards[13]; actions.append((placement, discard))
             else: return []
        return actions

    # ИЗМЕНЕНО v15: Добавлена обработка фаз Fantasyland
    def apply_action(self, action_index_or_outcome):
        if self.is_chance_node():
            player = self._player_to_deal_to; num_cards_to_deal = 0
            # Определяем, сколько карт сдавать в зависимости от фазы
            if self._phase in [STREET_FIRST_DEAL_P1, STREET_FIRST_DEAL_P2, PHASE_FANTASY_N_DEAL_1]: num_cards_to_deal = 5
            elif (self._phase >= STREET_SECOND_DEAL_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 != 0) or \
                 (self._phase >= PHASE_FANTASY_N_DEAL_2 and self._phase <= PHASE_FANTASY_N_PLACE_5 and self._phase % 2 != 0): num_cards_to_deal = 3
            elif self._phase == PHASE_FANTASY_F_DEAL: num_cards_to_deal = self._fantasy_cards_count

            if num_cards_to_deal > 0:
                 if len(self._deck) < num_cards_to_deal: raise Exception(f"Недостаточно карт в колоде ({len(self._deck)}) для сдачи {num_cards_to_deal} карт!")
                 self._current_cards[player] = [self._deck.pop() for _ in range(num_cards_to_deal)]
            self._go_to_next_phase(); return

        if self.is_terminal(): raise ValueError("Cannot apply action on terminal node")
        if self.is_chance_node(): raise ValueError("Cannot apply player action on chance node")
        player = self._current_player; action_index = action_index_or_outcome
        if self._cached_legal_actions is None: self.legal_actions(player)
        if self._cached_legal_actions is None or action_index < 0 or action_index >= len(self._cached_legal_actions): raise ValueError(f"Неверный индекс действия: {action_index} (доступно: {len(self._cached_legal_actions) if self._cached_legal_actions is not None else 'кэш пуст'}) для P{player} в фазе {self._phase}")
        action_tuple = self._cached_legal_actions[action_index]
        placement = []; card_discard = -1; num_placed = 0

        # Разбираем кортеж действия в зависимости от фазы
        is_normal_place_phase = (self._phase >= STREET_FIRST_PLACE_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 == 0)
        is_fantasy_n_place_phase = (self._phase >= PHASE_FANTASY_N_PLACE_1 and self._phase <= PHASE_FANTASY_N_PLACE_5 and self._phase % 2 == 0)
        is_fantasy_f_place_phase = (self._phase == PHASE_FANTASY_F_PLACE)

        if is_normal_place_phase or is_fantasy_n_place_phase:
            if self._phase in [STREET_FIRST_PLACE_P1, STREET_FIRST_PLACE_P2, PHASE_FANTASY_N_PLACE_1]: # Улица 1
                if not (isinstance(action_tuple, tuple) and len(action_tuple) == 5): raise ValueError(f"Неверный формат действия для улицы 1: {action_tuple}")
                placement = list(action_tuple); num_placed = 5
            else: # Улицы 2-5
                if not (isinstance(action_tuple, tuple) and len(action_tuple) == 2 and isinstance(action_tuple[0], tuple) and len(action_tuple[0]) == 2): raise ValueError(f"Неверный формат действия для улиц 2-5: {action_tuple}")
                placement = list(action_tuple[0]); card_discard = action_tuple[1]; num_placed = 2
        elif is_fantasy_f_place_phase:
             if not (isinstance(action_tuple, tuple) and len(action_tuple) == 2 and isinstance(action_tuple[0], tuple) and len(action_tuple[0]) == 13): raise ValueError(f"Неверный формат действия для Fantasy F: {action_tuple}")
             placement = list(action_tuple[0]); card_discard = action_tuple[1]; num_placed = 13
        else: raise ValueError(f"Применение действия в неизвестной или неверной фазе: {self._phase}")

        # Размещаем карты на доске
        for card, slot_idx in placement:
            if not (0 <= slot_idx < TOTAL_CARDS_PLACED): raise ValueError(f"Неверный индекс слота: {slot_idx} в действии {action_tuple}")
            if self._board[player][slot_idx] != -1: raise ValueError(f"Слот {slot_idx} уже занят! Доска: {cards_to_strings(self._board[player])}, Действие: {action_tuple}")
            self._board[player][slot_idx] = card
        if card_discard != -1: self._discards[player].append(card_discard)
        self._current_cards[player] = []; self._total_cards_placed[player] += num_placed; self._cards_to_place_count[player] = 0; self._cards_to_discard_count[player] = 0
        self._go_to_next_phase()

    def action_to_string(self, player: int, action_index: int) -> str:
        # ... (Без изменений) ...
        action_tuple = None
        if self._cached_legal_actions is not None and 0 <= action_index < len(self._cached_legal_actions): action_tuple = self._cached_legal_actions[action_index]
        elif self._current_player == player:
             self.legal_actions(player)
             if self._cached_legal_actions is not None and 0 <= action_index < len(self._cached_legal_actions): action_tuple = self._cached_legal_actions[action_index]
        if action_tuple is None: return f"InvalidActionIndex({action_index})"
        try:
            if isinstance(action_tuple, tuple) and len(action_tuple) == 2 and isinstance(action_tuple[0], tuple):
                 placement_tuple = action_tuple[0]; discard_card = action_tuple[1]
                 if all(isinstance(item, tuple) and len(item) == 2 for item in placement_tuple):
                     placement_str = " ".join([f"{card_to_string(c)}({s})" for c,s in placement_tuple]); discard_str = card_to_string(discard_card)
                     if len(placement_tuple) == 2: return f"Place2 {placement_str} Discard {discard_str}"
                     elif len(placement_tuple) == 13: return f"FantasyF {placement_str} Discard {discard_str}" # Для Fantasyland
            elif isinstance(action_tuple, tuple) and len(action_tuple) == 5 and all(isinstance(item, tuple) and len(item) == 2 for item in action_tuple):
                 return "Place1 " + " ".join([f"{card_to_string(c)}({s})" for c,s in action_tuple])
        except Exception as e: return f"ErrorFormattingAction({action_tuple})"
        return f"UnknownActionFormat({action_tuple})"

    def _calculate_final_returns(self):
        # ... (Без изменений) ...
        if not all(count == TOTAL_CARDS_PLACED for count in self._total_cards_placed): self._current_hand_returns = [0.0] * NUM_PLAYERS; return
        scores = [0] * NUM_PLAYERS; royalties = [0] * NUM_PLAYERS; is_dead = [False] * NUM_PLAYERS; evals = [{}, {}, {}]
        for p in range(NUM_PLAYERS):
            top_hand = self._board[p][TOP_SLOTS[0]:TOP_SLOTS[-1]+1]; middle_hand = self._board[p][MIDDLE_SLOTS[0]:MIDDLE_SLOTS[-1]+1]; bottom_hand = self._board[p][BOTTOM_SLOTS[0]:BOTTOM_SLOTS[-1]+1]
            evals[p]['top'] = evaluate_hand(top_hand); evals[p]['middle'] = evaluate_hand(middle_hand); evals[p]['bottom'] = evaluate_hand(bottom_hand)
            is_dead[p] = is_dead_hand(evals[p]['top'], evals[p]['middle'], evals[p]['bottom'])
            if not is_dead[p]:
                royalties[p] += calculate_royalties(evals[p]['top'][0], evals[p]['top'][1], 'top'); royalties[p] += calculate_royalties(evals[p]['middle'][0], evals[p]['middle'][1], 'middle'); royalties[p] += calculate_royalties(evals[p]['bottom'][0], evals[p]['bottom'][1], 'bottom')
        p0 = 0; p1 = 1; line_scores = [0, 0]; scoop_bonus = [0, 0]
        if is_dead[p0] and is_dead[p1]: pass
        elif is_dead[p0]: scores[p0] = -6; scores[p1] = 6 + royalties[p1]
        elif is_dead[p1]: scores[p0] = 6 + royalties[p0]; scores[p1] = -6
        else:
            comp_t = compare_evals(evals[p0]['top'], evals[p1]['top']); comp_m = compare_evals(evals[p0]['middle'], evals[p1]['middle']); comp_b = compare_evals(evals[p0]['bottom'], evals[p1]['bottom'])
            line_scores[p0] = comp_t + comp_m + comp_b; line_scores[p1] = -line_scores[p0]
            if comp_t == 1 and comp_m == 1 and comp_b == 1: scoop_bonus[p0] = 3
            elif comp_t == -1 and comp_m == -1 and comp_b == -1: scoop_bonus[p1] = 3
            scores[p0] = line_scores[p0] + scoop_bonus[p0] + royalties[p0]; scores[p1] = line_scores[p1] + scoop_bonus[p1] + royalties[p1]
        diff = scores[p0] - scores[p1]; self._current_hand_returns = [diff, -diff]; self._cumulative_returns[0] += diff; self._cumulative_returns[1] -= diff

    # ИЗМЕНЕНО v15: Реализация _check_and_setup_fantasy
    def _check_and_setup_fantasy(self) -> bool:
        """Проверяет условия для Fantasyland и устанавливает флаги для *следующей* руки."""
        self._next_fantasy_players = [] # Очищаем список перед проверкой
        triggered = False
        evals = [{}, {}]; is_dead = [False, False]
        for p in range(self._num_players):
            top_hand = self._board[p][TOP_SLOTS[0]:TOP_SLOTS[-1]+1]; middle_hand = self._board[p][MIDDLE_SLOTS[0]:MIDDLE_SLOTS[-1]+1]; bottom_hand = self._board[p][BOTTOM_SLOTS[0]:BOTTOM_SLOTS[-1]+1]
            evals[p]['top'] = evaluate_hand(top_hand); evals[p]['middle'] = evaluate_hand(middle_hand); evals[p]['bottom'] = evaluate_hand(bottom_hand)
            is_dead[p] = is_dead_hand(evals[p]['top'], evals[p]['middle'], evals[p]['bottom'])
        for p in range(self._num_players):
            if not is_dead[p]: # Проверяем только живые руки
                top_eval = evals[p]['top']
                # Проверяем QQ+ или сет на топе
                if (top_eval[0] == PAIR and top_eval[1][0] >= FANTASY_TRIGGER_RANK) or \
                   (top_eval[0] == THREE_OF_A_KIND):
                    self._next_fantasy_players.append(p)
                    triggered = True
        return triggered

    def returns(self):
        # ... (Без изменений) ...
        if not self._game_over: return [0.0] * self._num_players
        return self._cumulative_returns
    def information_state_string(self, player: int) -> str:
        # ИЗМЕНЕНО v15: Добавлена информация о Fantasyland
        if player < 0 or player >= self._num_players: return f"Phase:{self._phase};GameOver:{self._game_over}"
        parts = []; parts.append(f"P:{player}"); parts.append(f"Ph:{self._phase}")
        my_board_cards = self._board[player]; my_board_str = f"B:[{' '.join(cards_to_strings(my_board_cards[:3]))}|{' '.join(cards_to_strings(my_board_cards[3:8]))}|{' '.join(cards_to_strings(my_board_cards[8:]))}]"; parts.append(my_board_str)
        parts.append(f"H:[{' '.join(cards_to_strings(self._current_cards[player]))}]"); parts.append(f"D:[{' '.join(cards_to_strings(self._discards[player]))}]")
        opponent = 1 - player; opp_board_cards = self._board[opponent]; opp_board_str = f"OB:[{' '.join(cards_to_strings(opp_board_cards[:3]))}|{' '.join(cards_to_strings(opp_board_cards[3:8]))}|{' '.join(cards_to_strings(opp_board_cards[8:]))}]"
        is_fantasy_phase = self._phase >= PHASE_FANTASY_SETUP and self._phase <= PHASE_FANTASY_SHOWDOWN; show_opp_board = not is_fantasy_phase
        if show_opp_board: parts.append(opp_board_str)
        else: parts.append("OB:[HIDDEN]")
        if self._phase == STREET_FIRST_DEAL_P2 and player == 0: opponent_hand_str = f"OH:[{' '.join(cards_to_strings(self._current_cards[opponent]))}]"; parts.append(opponent_hand_str)
        elif self._phase == STREET_FIRST_PLACE_P1 and player == 1: opponent_hand_str = f"OH:[{' '.join(cards_to_strings(self._current_cards[opponent]))}]"; parts.append(opponent_hand_str)
        else: parts.append("OH:[?]")
        # Показываем, кто БУДЕТ в фантазии на след. руку (если мы не в Fantasy)
        # или кто сейчас F/N (если мы в Fantasy)
        if self._is_fantasy_hand: f_status = f"CurF:{self._current_fantasy_player};CurN:{self._current_normal_player}"
        else: fantasy_next = [int(p in self._next_fantasy_players) for p in range(self._num_players)]; f_status = f"NextF:[{fantasy_next[0]}{fantasy_next[1]}]"
        parts.append(f_status)
        try: parts.append(f"Place:{self._cards_to_place_count[player]}|Discard:{self._cards_to_discard_count[player]}")
        except IndexError: parts.append("Place:?|Discard:?")
        return ";".join(parts)
    def observation_string(self, player): return self.information_state_string(player)
    def clone(self):
        # ИЗМЕНЕНО v15: Копируем новые переменные
        cloned = type(self)(self.get_game()); cloned._num_players = self._num_players; cloned._current_player = self._current_player; cloned._dealer_button = self._dealer_button
        cloned._next_player_to_act = self._next_player_to_act; cloned._player_to_deal_to = self._player_to_deal_to; cloned._phase = self._phase
        cloned._fantasy_cards_count = self._fantasy_cards_count; cloned._game_over = self._game_over
        cloned._deck = self._deck[:]; cloned._cards_to_place_count = self._cards_to_place_count[:]; cloned._cards_to_discard_count = self._cards_to_discard_count[:]
        cloned._total_cards_placed = self._total_cards_placed[:]; cloned._cumulative_returns = self._cumulative_returns[:]; cloned._current_hand_returns = self._current_hand_returns[:]
        cloned._board = copy.deepcopy(self._board); cloned._current_cards = copy.deepcopy(self._current_cards); cloned._discards = copy.deepcopy(self._discards)
        cloned._is_fantasy_hand = self._is_fantasy_hand; cloned._next_fantasy_players = self._next_fantasy_players[:]; cloned._current_fantasy_player = self._current_fantasy_player; cloned._current_normal_player = self._current_normal_player
        cloned._cached_legal_actions = None
        return cloned

    # ИСПРАВЛЕНО v10: Правильная реализация chance_outcomes
    def chance_outcomes(self) -> List[Tuple[Any, float]]:
        if not self.is_chance_node(): return []
        num_remaining_cards = len(self._deck)
        if num_remaining_cards == 0: print(f"Warning: Chance node called with empty deck in phase {self._phase}"); return []
        prob = 1.0 / num_remaining_cards
        return [(card, prob) for card in self._deck]

    def resample_from_infostate(self, player_id: int, probability_sampler) -> 'OFCPineappleState':
        # ... (Без изменений) ...
        if not (0 <= player_id < self._num_players): raise ValueError(f"Неверный player_id: {player_id}")
        opponent_id = 1 - player_id
        known_cards: Set[int] = set()
        known_cards.update(c for c in self._board[player_id] if c != -1); known_cards.update(c for c in self._current_cards[player_id] if c != -1); known_cards.update(c for c in self._discards[player_id] if c != -1)
        known_cards.update(c for c in self._board[opponent_id] if c != -1)
        if self._phase == STREET_FIRST_DEAL_P2 and player_id == 0: known_cards.update(c for c in self._current_cards[opponent_id] if c != -1)
        elif self._phase == STREET_FIRST_PLACE_P1 and player_id == 1: known_cards.update(c for c in self._current_cards[opponent_id] if c != -1)
        all_cards = set(range(NUM_CARDS)); unknown_cards_set = all_cards - known_cards; unknown_cards_list = list(unknown_cards_set)
        rng = np.random.RandomState(); rng.shuffle(unknown_cards_list); unknown_cards_iter = iter(unknown_cards_list)
        cloned_state = self.clone()
        opponent_hand_size_needed = 0; opponent_discard_count_needed = 0; current_phase = self._phase
        if opponent_id == 1: # Оппонент - P2
            if current_phase in [STREET_SECOND_DEAL_P2, STREET_THIRD_DEAL_P2, STREET_FOURTH_DEAL_P2, STREET_FIFTH_DEAL_P2]: opponent_hand_size_needed = 3
            if current_phase > STREET_SECOND_PLACE_P2: opponent_discard_count_needed += 1
            if current_phase > STREET_THIRD_PLACE_P2: opponent_discard_count_needed += 1
            if current_phase > STREET_FOURTH_PLACE_P2: opponent_discard_count_needed += 1
            if current_phase > STREET_FIFTH_PLACE_P2: opponent_discard_count_needed += 1
        else: # Оппонент - P1
            if current_phase in [STREET_SECOND_DEAL_P1, STREET_THIRD_DEAL_P1, STREET_FOURTH_DEAL_P1, STREET_FIFTH_DEAL_P1]: opponent_hand_size_needed = 3
            if current_phase > STREET_SECOND_PLACE_P1: opponent_discard_count_needed += 1
            if current_phase > STREET_THIRD_PLACE_P1: opponent_discard_count_needed += 1
            if current_phase > STREET_FOURTH_PLACE_P1: opponent_discard_count_needed += 1
            if current_phase > STREET_FIFTH_PLACE_P1: opponent_discard_count_needed += 1
        try:
            cloned_state._current_cards[opponent_id] = [next(unknown_cards_iter) for _ in range(opponent_hand_size_needed)]
            cloned_state._discards[opponent_id] = [next(unknown_cards_iter) for _ in range(opponent_discard_count_needed)] # Заменяем сброс
            cloned_state._deck = list(unknown_cards_iter)
        except StopIteration: raise Exception(f"Ошибка в resample_from_infostate: Не хватило неизвестных карт. Фаза: {current_phase}, Игрок: {player_id}, Известно: {len(known_cards)}, Неизвестно: {len(unknown_cards_set)}, Нужно опп.рука: {opponent_hand_size_needed}, Нужно опп.сброс: {opponent_discard_count_needed}")
        return cloned_state

    def __str__(self):
        player = self.current_player(); player_to_show = player if player >= 0 else 0
        return self.information_state_string(player_to_show)

# --- Регистрация игры ---
# ... (Без изменений) ...
try:
    pyspiel.load_game(_GAME_TYPE.short_name)
    # print(f"Игра '{_GAME_TYPE.short_name}' уже была зарегистрирована.")
except pyspiel.SpielError:
    pyspiel.register_game(_GAME_TYPE, OFCPineappleGame)
    print(f"Игра '{_GAME_TYPE.short_name}' успешно зарегистрирована.")
except Exception as e:
    print(f"Неожиданная ошибка при проверке/регистрации игры '{_GAME_TYPE.short_name}': {e}")
