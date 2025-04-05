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
STREET_FIFTH_PLACE_P2 = 20 # Изменено
STREET_REGULAR_SHOWDOWN = 21 # Изменено

PHASE_FANTASY_DEAL = 30 # Изменено
PHASE_FANTASY_N_STREET_1 = 31
PHASE_FANTASY_F_PLACEMENT = 32
PHASE_FANTASY_N_STREET_2 = 33
PHASE_FANTASY_N_STREET_3 = 34
PHASE_FANTASY_N_STREET_4 = 35
PHASE_FANTASY_N_STREET_5 = 36
PHASE_FANTASY_SHOWDOWN = 37

RANKS = "23456789TJQKA"
SUITS = "shdc"

def card_rank(card_int: int) -> int:
    if card_int == -1: return -1
    return card_int // NUM_SUITS

def card_suit(card_int: int) -> int:
    if card_int == -1: return -1
    return card_int % NUM_SUITS

def card_to_string(card_int: int) -> str:
    if card_int == -1: return "__"
    if not 0 <= card_int < NUM_CARDS:
        raise ValueError(f"Неверный код карты: {card_int}")
    return RANKS[card_rank(card_int)] + SUITS[card_suit(card_int)]

def string_to_card(card_str: str) -> int:
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
    return [card_to_string(c) for c in card_ints]

def strings_to_cards(card_strs: List[str]) -> List[int]:
    return [string_to_card(s) for s in card_strs]

HIGH_CARD = 0
PAIR = 1
TWO_PAIR = 2
THREE_OF_A_KIND = 3
STRAIGHT = 4
FLUSH = 5
FULL_HOUSE = 6
FOUR_OF_A_KIND = 7
STRAIGHT_FLUSH = 8

def evaluate_hand(card_ints: List[int]) -> Tuple[int, List[int]]:
    cards = [c for c in card_ints if c != -1]
    n = len(cards)
    if n == 0: return (HIGH_CARD, [])
    if n < 3:
        ranks = sorted([card_rank(c) for c in cards], reverse=True)
        return (HIGH_CARD, ranks)
    if n == 4:
        ranks = sorted([card_rank(c) for c in cards], reverse=True)
        return (HIGH_CARD, ranks)
    if n not in [3, 5]:
         ranks = sorted([card_rank(c) for c in cards], reverse=True)
         print(f"Предупреждение: evaluate_hand вызвана с {n} картами.")
         return (HIGH_CARD, ranks)

    ranks = sorted([card_rank(c) for c in cards], reverse=True)
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
                if all(unique_ranks[i+j] == unique_ranks[i] - j for j in range(5)):
                    is_straight = True
                    straight_high_card_rank = unique_ranks[i]
                    break
            if not is_straight and set(unique_ranks).issuperset({12, 3, 2, 1, 0}): # A-5
                 is_straight = True
                 straight_high_card_rank = 3 # 5ка

        if is_straight and is_flush: return (STRAIGHT_FLUSH, [straight_high_card_rank])
        if most_common_ranks[0][1] == 4:
            quad_rank = most_common_ranks[0][0]
            kicker_rank = most_common_ranks[1][0]
            return (FOUR_OF_A_KIND, [quad_rank, kicker_rank])
        if len(most_common_ranks) > 1 and most_common_ranks[0][1] == 3 and most_common_ranks[1][1] >= 2:
            three_rank = most_common_ranks[0][0]
            pair_rank = most_common_ranks[1][0]
            return (FULL_HOUSE, [three_rank, pair_rank])
        if is_flush: return (FLUSH, ranks)
        if is_straight: return (STRAIGHT, [straight_high_card_rank])

    if most_common_ranks[0][1] == 3:
        set_rank = most_common_ranks[0][0]
        other_ranks = sorted([r for r in ranks if r != set_rank], reverse=True)
        kickers = [set_rank] + other_ranks
        return (THREE_OF_A_KIND, kickers)

    if n == 5 and len(most_common_ranks) > 1 and most_common_ranks[0][1] == 2 and most_common_ranks[1][1] == 2:
        high_pair_rank = most_common_ranks[0][0]
        low_pair_rank = most_common_ranks[1][0]
        kicker_rank = most_common_ranks[2][0]
        kickers = [high_pair_rank, low_pair_rank, kicker_rank]
        return (TWO_PAIR, kickers)

    if most_common_ranks[0][1] == 2:
        pair_rank = most_common_ranks[0][0]
        other_ranks = sorted([r for r in ranks if r != pair_rank], reverse=True)
        kickers = [pair_rank] + other_ranks
        return (PAIR, kickers)

    return (HIGH_CARD, ranks)

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
    type1, kickers1 = eval1
    type2, kickers2 = eval2
    if type1 > type2: return 1
    if type1 < type2: return -1
    len_kickers = min(len(kickers1), len(kickers2))
    for i in range(len_kickers):
        if kickers1[i] > kickers2[i]: return 1
        if kickers1[i] < kickers2[i]: return -1
    return 0

def is_dead_hand(top_eval: Tuple[int, List[int]],
                   middle_eval: Tuple[int, List[int]],
                   bottom_eval: Tuple[int, List[int]]) -> bool:
    """
    Проверяет, является ли рука 'мертвой'.
    ВАЖНО: Эта функция предполагает, что все ряды ПОЛНОСТЬЮ ЗАПОЛНЕНЫ.
    Проверку на полноту нужно делать перед вызовом этой функции.
    """
    if compare_evals(top_eval, middle_eval) > 0: return True
    if compare_evals(middle_eval, bottom_eval) > 0: return True
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
        self._dealer_button = 0
        self._next_player_to_act = (self._dealer_button + 1) % self._num_players
        self._current_player = pyspiel.PlayerId.CHANCE
        self._player_to_deal_to = self._next_player_to_act

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

        self._go_to_next_phase()

    def _go_to_next_phase(self):
        """Переход к следующей фазе/улице/игроку."""
        # TODO: Переписать с учетом всех фаз и условий
        if self._phase == STREET_PREDEAL:
             self._phase = STREET_FIRST_DEAL_P1
             self._current_player = pyspiel.PlayerId.CHANCE
             self._player_to_deal_to = self._next_player_to_act
        elif self._phase == STREET_FIRST_DEAL_P1:
             self._phase = STREET_FIRST_PLACE_P1
             self._current_player = self._player_to_deal_to
             self._player_confirmed_action = False
        elif self._phase == STREET_FIRST_PLACE_P1:
             self._phase = STREET_FIRST_DEAL_P2
             self._current_player = pyspiel.PlayerId.CHANCE
             self._player_to_deal_to = (self._next_player_to_act + 1) % self._num_players
        elif self._phase == STREET_FIRST_DEAL_P2:
             self._phase = STREET_FIRST_PLACE_P2
             self._current_player = self._player_to_deal_to
             self._player_confirmed_action = False
        elif self._phase == STREET_FIRST_PLACE_P2:
             self._phase = STREET_SECOND_DEAL_P1
             self._current_player = pyspiel.PlayerId.CHANCE
             self._player_to_deal_to = self._next_player_to_act
        # --- Заглушка для завершения ---
        else:
             print(f"Предупреждение: Необработанный переход из фазы {self._phase}")
             self._game_over = True
             self._current_player = pyspiel.PlayerId.TERMINAL

    def current_player(self):
        """Возвращает ID текущего игрока или константу."""
        return self._current_player

    def _legal_actions(self, player):
        """Генерирует список легальных действий (кортежей)."""
        actions = []
        if self.is_chance_node() or self.is_terminal() or self._current_player != player:
            return []
        # TODO: Реализовать генерацию действий
        return actions

    def _apply_action(self, action):
        """Применяет действие (размещение карт) или исход шанса."""
        if self.is_chance_node():
            player = self._player_to_deal_to
            num_cards_to_deal = 0
            if self._phase == STREET_FIRST_DEAL_P1 or self._phase == STREET_FIRST_DEAL_P2:
                num_cards_to_deal = 5
            elif self._phase >= STREET_SECOND_DEAL_P1 and self._phase <= STREET_FIFTH_PLACE_P2 and self._phase % 2 != 0:
                num_cards_to_deal = 3
            # TODO: Добавить сдачу для Fantasy

            if num_cards_to_deal > 0:
                 if len(self._deck) < num_cards_to_deal: raise Exception("Недостаточно карт в колоде!")
                 self._current_cards[player] = [self._deck.pop() for _ in range(num_cards_to_deal)]

            self._go_to_next_phase()
            return

        if self.is_terminal(): raise ValueError("Cannot apply action on terminal node")
        if self.is_chance_node(): raise ValueError("Cannot apply player action on chance node")

        player = self._current_player
        # TODO: Распарсить 'action' и обновить доску/сброс/руку/счетчики
        self._player_confirmed_action = True
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
        # TODO: Реализовать подсчет очков
        return self._cumulative_returns

    def information_state_string(self, player):
        """Возвращает строку информации, доступную игроку."""
        # TODO: Тщательно реализовать
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
        cloned._player_to_deal_to = self._player_to_deal_to
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
        player = self.current_player()
        if player < 0: player = 0
        return self.information_state_string(player)

# --- Регистрация игры ---
try:
    pyspiel.load_game(_GAME_TYPE.short_name)
    # print(f"Игра '{_GAME_TYPE.short_name}' уже была зарегистрирована.")
except pyspiel.SpielError:
    pyspiel.register_game(_GAME_TYPE, OFCPineappleGame)
    print(f"Игра '{_GAME_TYPE.short_name}' успешно зарегистрирована.")
except Exception as e:
     print(f"Неожиданная ошибка при проверке/регистрации игры: {e}")

# Убраны print() в конце, чтобы не мешать при импорте
