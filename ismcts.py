# Copyright 2019 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""An implementation of Information Set Monte Carlo Tree Search (IS-MCTS).

See Cowling, Powley, and Whitehouse 2011.
https://ieeexplore.ieee.org/document/6203567

Исправлено v2: get_state_key передает player_id, добавлен импорт traceback
"""

import copy
import enum
import numpy as np
import pyspiel
import traceback # <--- ДОБАВЛЕН ИМПОРТ

UNLIMITED_NUM_WORLD_SAMPLES = -1
UNEXPANDED_VISIT_COUNT = -1
TIE_TOLERANCE = 1e-5


class ISMCTSFinalPolicyType(enum.Enum):
  """A enumeration class for final ISMCTS policy type."""
  NORMALIZED_VISITED_COUNT = 1
  MAX_VISIT_COUNT = 2
  MAX_VALUE = 3


class ChildSelectionPolicy(enum.Enum):
  """A enumeration class for children selection in ISMCTS."""
  UCT = 1
  PUCT = 2


class ChildInfo(object):
  """Child node information for the search tree."""

  def __init__(self, visits, return_sum, prior):
    self.visits = visits
    self.return_sum = return_sum
    self.prior = prior

  def value(self):
    # Avoid division by zero if visits is 0 (should not happen in normal operation after expansion)
    if self.visits == 0:
        return 0.0
    return self.return_sum / self.visits


class ISMCTSNode(object):
  """Node data structure for the search tree."""

  def __init__(self):
    self.child_info = {}
    self.total_visits = 0
    self.prior_map = {}


class ISMCTSBot(pyspiel.Bot):
  """Adapted from the C++ implementation."""

  def __init__(self,
               game,
               evaluator,
               uct_c,
               max_simulations,
               max_world_samples=UNLIMITED_NUM_WORLD_SAMPLES,
               random_state=None,
               final_policy_type=ISMCTSFinalPolicyType.MAX_VISIT_COUNT,
               use_observation_string=False,
               allow_inconsistent_action_sets=False,
               child_selection_policy=ChildSelectionPolicy.PUCT):

    pyspiel.Bot.__init__(self)
    self._game = game
    self._evaluator = evaluator
    self._uct_c = uct_c
    self._max_simulations = max_simulations
    self._max_world_samples = max_world_samples
    self._final_policy_type = final_policy_type
    self._use_observation_string = use_observation_string
    self._allow_inconsistent_action_sets = allow_inconsistent_action_sets
    self._nodes = {}
    self._node_pool = []
    self._root_samples = []
    self._random_state = random_state or np.random.RandomState()
    self._child_selection_policy = child_selection_policy
    self._resampler_cb = None

  def random_number(self):
    return self._random_state.uniform()

  def reset(self):
    self._nodes = {}
    self._node_pool = []
    self._root_samples = []

  def get_state_key(self, state):
    """Returns a key for the information state."""
    player = state.current_player()
    # ИСПРАВЛЕНО v1: Передаем player в information_state_string/observation_string
    if self._use_observation_string:
      return player, state.observation_string(player)
    else:
      return player, state.information_state_string(player)

  def run_search(self, state):
    """Runs an IS-MCTS search from the current state and returns the policy."""
    self.reset()
    # Проверка на тип игры
    if state.get_game().get_type().dynamics != pyspiel.GameType.Dynamics.SEQUENTIAL:
        raise ValueError("ISMCTS requires sequential games.")
    if state.get_game().get_type().information == pyspiel.GameType.Information.PERFECT_INFORMATION:
        print("Warning: Using ISMCTS for a perfect information game.")

    # Если терминальное состояние или нет действий, возвращаем пустую политику
    if state.is_terminal():
        return []
    # ИСПРАВЛЕНО v2: Вызываем legal_actions с player_id
    current_player_id = state.current_player()
    if current_player_id < 0: # Если это шанс или терминальный узел
        return []
    legal_actions = state.legal_actions(current_player_id)
    if not legal_actions:
        return []
    # Если только одно действие, возвращаем его со 100% вероятностью
    if len(legal_actions) == 1:
      return [(legal_actions[0], 1.0)]

    # Создаем корневой узел для текущего инфостейта
    self._root_node = self.lookup_or_create_node(state)
    if not self._root_node:
        raise RuntimeError("Failed to create root node.")

    root_infostate_key = self.get_state_key(state)

    # Основной цикл симуляций
    for sim_count in range(self._max_simulations):
      sampled_root_state = self.sample_root_state(state)
      if not sampled_root_state:
          raise RuntimeError(f"Simulation {sim_count+1}: Failed to sample root state.")

      # Запускаем одну симуляцию из сэмплированного состояния
      try:
          self.run_simulation(sampled_root_state)
      except Exception as e:
          print(f"!!! Ошибка в симуляции {sim_count+1} !!!")
          print(f"Исходное состояние:\n{state}")
          print(f"Сэмплированное состояние перед симуляцией:\n{sampled_root_state}")
          print(f"Ошибка: {e}")
          traceback.print_exc() # Теперь traceback импортирован
          print("Продолжение поиска после ошибки в симуляции...")
          continue

    # Формируем финальную политику
    if self._allow_inconsistent_action_sets:
      current_legal_actions = state.legal_actions(current_player_id) # Передаем ID
      temp_node = self.filter_illegals(self._root_node, current_legal_actions)
      if temp_node.total_visits <= 0:
          print("Warning: All visited actions became illegal. Returning uniform policy.")
          num_legal = len(current_legal_actions)
          return [(a, 1.0 / num_legal) for a in current_legal_actions] if num_legal > 0 else []
      return self.get_final_policy(state, temp_node)
    else:
      if self._root_node.total_visits <= 0:
           print(f"Warning: Root node has {self._root_node.total_visits} visits after {self._max_simulations} simulations. Returning uniform policy.")
           current_legal_actions = state.legal_actions(current_player_id) # Передаем ID
           num_legal = len(current_legal_actions)
           return [(a, 1.0 / num_legal) for a in current_legal_actions] if num_legal > 0 else []
      return self.get_final_policy(state, self._root_node)


  def step(self, state):
    """Returns the action selected by the bot."""
    policy = self.run_search(state)
    if not policy:
        print("Warning: ISMCTSBot.step received empty policy. Returning random action if available.")
        # ИСПРАВЛЕНО v2: Передаем player_id в legal_actions
        current_player_id = state.current_player()
        legal_actions = state.legal_actions(current_player_id) if current_player_id >= 0 else []
        return self._random_state.choice(legal_actions) if legal_actions else pyspiel.INVALID_ACTION

    action_list, prob_list = zip(*policy)
    prob_sum = sum(prob_list)
    if not np.isclose(prob_sum, 1.0):
        print(f"Warning: Probabilities sum to {prob_sum}, renormalizing.")
        prob_list = np.array(prob_list) / prob_sum
    return self._random_state.choice(action_list, p=prob_list)

  def get_policy(self, state):
    """Returns the policy computed by the bot."""
    return self.run_search(state)

  def step_with_policy(self, state):
    """Returns the policy and the action sampled from it."""
    policy = self.get_policy(state)
    if not policy:
        print("Warning: ISMCTSBot.step_with_policy received empty policy. Returning empty policy and random action.")
        # ИСПРАВЛЕНО v2: Передаем player_id в legal_actions
        current_player_id = state.current_player()
        legal_actions = state.legal_actions(current_player_id) if current_player_id >= 0 else []
        sampled_action = self._random_state.choice(legal_actions) if legal_actions else pyspiel.INVALID_ACTION
        return [], sampled_action

    action_list, prob_list = zip(*policy)
    prob_sum = sum(prob_list)
    if not np.isclose(prob_sum, 1.0):
        print(f"Warning: Probabilities sum to {prob_sum}, renormalizing.")
        prob_list = np.array(prob_list) / prob_sum
    sampled_action = self._random_state.choice(action_list, p=prob_list)
    return policy, sampled_action

  def get_final_policy(self, state, node):
    """Computes the final policy from the visits/values in the node."""
    assert node
    # ИСПРАВЛЕНО v2: Передаем player_id в legal_actions
    current_player_id = state.current_player()
    legal_actions = state.legal_actions(current_player_id) if current_player_id >= 0 else []
    num_legal = len(legal_actions)

    if node.total_visits <= 0:
        print("Warning: get_final_policy called on node with zero visits. Returning uniform policy.")
        return [(a, 1.0 / num_legal) for a in legal_actions] if num_legal > 0 else []

    policy = []
    if (self._final_policy_type == ISMCTSFinalPolicyType.NORMALIZED_VISITED_COUNT):
      total_visits = node.total_visits
      policy = [(action, child.visits / total_visits) for action, child in node.child_info.items() if child.visits > 0]
    elif self._final_policy_type == ISMCTSFinalPolicyType.MAX_VISIT_COUNT:
      max_visits = -1; best_actions = []
      for action, child in node.child_info.items():
          if child.visits > max_visits: max_visits = child.visits; best_actions = [action]
          elif child.visits == max_visits: best_actions.append(action)
      count = len(best_actions)
      policy = [(action, 1. / count if action in best_actions else 0.0) for action, child in node.child_info.items()]
    elif self._final_policy_type == ISMCTSFinalPolicyType.MAX_VALUE:
      max_value = -float('inf'); best_actions = []
      for action, child in node.child_info.items():
          if child.visits > 0:
              val = child.value()
              if val > max_value: max_value = val
      for action, child in node.child_info.items():
           if child.visits > 0 and child.value() >= max_value - TIE_TOLERANCE: best_actions.append(action)
      count = len(best_actions)
      policy = [(action, 1. / count if action in best_actions else 0.0) for action, child in node.child_info.items()]

    policy_actions = {a for a, p in policy}
    for action in legal_actions:
        if action not in policy_actions: policy.append((action, 0.0))

    prob_sum = sum(p for a, p in policy)
    if prob_sum > 0 and not np.isclose(prob_sum, 1.0): policy = [(a, p / prob_sum) for a, p in policy]
    elif prob_sum == 0 and num_legal > 0: policy = [(a, 1.0 / num_legal) for a in legal_actions]

    return policy

  def sample_root_state(self, state):
    """Samples a world state consistent with the information state."""
    if self._max_world_samples == UNLIMITED_NUM_WORLD_SAMPLES: return self.resample_from_infostate(state)
    elif len(self._root_samples) < self._max_world_samples:
      new_sample = self.resample_from_infostate(state); self._root_samples.append(new_sample); return new_sample.clone()
    elif len(self._root_samples) == self._max_world_samples:
      idx = self._random_state.randint(len(self._root_samples)); return self._root_samples[idx].clone()
    else: raise pyspiel.SpielError('Case not handled (badly set max_world_samples..?)')

  def resample_from_infostate(self, state):
    """Calls the state's resample method or a custom callback."""
    if self._resampler_cb: return self._resampler_cb(state, state.current_player())
    else:
      try: return state.resample_from_infostate(state.current_player(), None)
      except AttributeError: print(f"Ошибка: Объект состояния {type(state)} не имеет метода resample_from_infostate."); raise
      except Exception as e: print(f"Ошибка при вызове state.resample_from_infostate: {e}"); raise

  def create_new_node(self, state):
    """Creates a new node in the tree."""
    infostate_key = self.get_state_key(state)
    if infostate_key in self._nodes: print(f"Warning: Node for key {infostate_key} already exists in create_new_node."); return self._nodes[infostate_key]
    new_node = ISMCTSNode(); self._node_pool.append(new_node); self._nodes[infostate_key] = new_node; new_node.total_visits = UNEXPANDED_VISIT_COUNT
    if not state.is_terminal():
        try:
            priors = self._evaluator.prior(state)
            if not isinstance(priors, list) or not all(isinstance(p, tuple) and len(p) == 2 for p in priors):
                 print(f"Warning: Evaluator prior() returned unexpected format: {priors}. Expected list of (action, prob) tuples.")
                 if isinstance(priors, list) and all(isinstance(a, int) for a in priors):
                     num_actions = len(priors); priors = [(a, 1.0/num_actions) for a in priors] if num_actions > 0 else []
                 else: priors = []
            new_node.prior_map = {action: prob for action, prob in priors}
            prob_sum = sum(new_node.prior_map.values())
            if prob_sum > 0 and not np.isclose(prob_sum, 1.0):
                print(f"Warning: Priors sum to {prob_sum}, renormalizing.")
                for action in new_node.prior_map: new_node.prior_map[action] /= prob_sum
        except Exception as e:
            print(f"Ошибка при вызове evaluator.prior(): {e}")
            # ИСПРАВЛЕНО v2: Передаем player_id в legal_actions
            current_player_id = state.current_player()
            legal_actions = state.legal_actions(current_player_id) if current_player_id >= 0 else []
            num_legal = len(legal_actions)
            new_node.prior_map = {action: 1.0 / num_legal for action in legal_actions} if num_legal > 0 else {}
    return new_node

  def set_resampler(self, cb): self._resampler_cb = cb
  def lookup_node(self, state): key = self.get_state_key(state); return self._nodes.get(key, None)
  def lookup_or_create_node(self, state): node = self.lookup_node(state); return node if node else self.create_new_node(state)

  def filter_illegals(self, node, legal_actions):
    new_node = copy.deepcopy(node); legal_action_set = set(legal_actions); actions_to_remove = []
    for action, child in node.child_info.items():
      if action not in legal_action_set: new_node.total_visits -= child.visits; actions_to_remove.append(action)
    for action in actions_to_remove:
         del new_node.child_info[action]
         if action in new_node.prior_map: del new_node.prior_map[action]
    new_node.total_visits = max(0, new_node.total_visits); return new_node

  def expand_if_necessary(self, node, action):
    if action not in node.child_info:
      prior = node.prior_map.get(action, 0.0)
      if prior == 0.0 and node.prior_map: print(f"Warning: Action {action} not found in prior_map during expansion. Using prior=0.")
      elif not node.prior_map and not node.child_info: num_children = len(node.child_info) if node.child_info else 1; prior = 1.0 / num_children if num_children > 0 else 1.0
      node.child_info[action] = ChildInfo(0.0, 0.0, prior)

  def select_action_tree_policy(self, node, legal_actions):
    if self._allow_inconsistent_action_sets:
      temp_node = self.filter_illegals(node, legal_actions)
      if temp_node.total_visits == 0:
        action = legal_actions[self._random_state.randint(len(legal_actions))]; self.expand_if_necessary(node, action); return action
      else: return self.select_action(temp_node)
    else: return self.select_action(node)

  def _action_value(self, node, child):
    if child.visits == 0:
        if self._child_selection_policy == ChildSelectionPolicy.PUCT: sqrt_total_visits = np.sqrt(max(1, node.total_visits)); return self._uct_c * child.prior * sqrt_total_visits
        else: return 0.0
    action_value = child.value(); exploration_term = 0.0
    if self._child_selection_policy == ChildSelectionPolicy.UCT: exploration_term = self._uct_c * np.sqrt(np.log(node.total_visits) / child.visits)
    elif self._child_selection_policy == ChildSelectionPolicy.PUCT: exploration_term = (self._uct_c * child.prior * np.sqrt(node.total_visits) / (1 + child.visits))
    else: raise pyspiel.SpielError('Child selection policy unrecognized.')
    return action_value + exploration_term

  def _select_candidate_actions(self, node):
    candidates = []; max_action_value = -float('inf')
    for child in node.child_info.values(): value = self._action_value(node, child);
        if value > max_action_value: max_action_value = value
    for action, child in node.child_info.items():
      if self._action_value(node, child) >= max_action_value - TIE_TOLERANCE: candidates.append(action)
    return candidates

  def select_action(self, node):
    if not node.child_info: print("Warning: select_action called on node with no children."); return pyspiel.INVALID_ACTION
    candidates = self._select_candidate_actions(node)
    if not candidates: print("Warning: No candidate actions found in select_action. Selecting random child."); candidates = list(node.child_info.keys());
        if not candidates: return pyspiel.INVALID_ACTION
    return candidates[self._random_state.randint(len(candidates))]

  def check_expand(self, node, legal_actions):
    if not self._allow_inconsistent_action_sets:
        if len(node.child_info) == len(legal_actions): return pyspiel.INVALID_ACTION
    legal_actions_set = set(legal_actions); current_actions_set = set(node.child_info.keys()); missing_actions = list(legal_actions_set - current_actions_set)
    if not missing_actions: return pyspiel.INVALID_ACTION
    else: return missing_actions[self._random_state.randint(len(missing_actions))]

  def run_simulation(self, state):
    if state.is_terminal(): return state.returns()
    if state.is_chance_node():
      outcomes_with_probs = state.chance_outcomes()
      if not outcomes_with_probs: print(f"Warning: Chance node with no outcomes at state:\n{state}"); return np.zeros(self._game.num_players())
      action_list, prob_list = zip(*outcomes_with_probs); prob_sum = sum(prob_list)
      if not np.isclose(prob_sum, 1.0): print(f"Warning: Chance outcome probabilities sum to {prob_sum}, renormalizing."); prob_list = np.array(prob_list) / prob_sum
      chance_action = self._random_state.choice(action_list, p=prob_list)
      next_state = state.clone(); next_state.apply_action(chance_action); return self.run_simulation(next_state)

    cur_player = state.current_player()
    # ИСПРАВЛЕНО v2: Передаем player_id в legal_actions
    legal_actions = state.legal_actions(cur_player)
    if not legal_actions: print(f"Warning: No legal actions for player {cur_player} in non-terminal state:\n{state}"); return np.zeros(self._game.num_players())

    node = self.lookup_or_create_node(state)
    if not node: raise RuntimeError(f"Failed to lookup or create node for state:\n{state}")

    returns = np.zeros(self._game.num_players())
    chosen_action = pyspiel.INVALID_ACTION # Инициализация

    if node.total_visits == UNEXPANDED_VISIT_COUNT:
      node.total_visits = 0
      returns = self._evaluator.evaluate(state)
      # Для первого посещения, действие не выбирается, но нам нужно обновить узел
      # Мы не можем обновить child_info, так как действия не было.
      # Обновление total_visits произойдет ниже.
      # Важно: результат evaluate будет возвращен и использован выше по стеку.
    else:
      chosen_action = self.check_expand(node, legal_actions)
      if chosen_action != pyspiel.INVALID_ACTION:
        self.expand_if_necessary(node, chosen_action)
        next_state = state.clone(); next_state.apply_action(chosen_action)
        returns = self._evaluator.evaluate(next_state)
      else:
        chosen_action = self.select_action_tree_policy(node, legal_actions)
        if chosen_action == pyspiel.INVALID_ACTION:
             print(f"Warning: select_action_tree_policy returned INVALID_ACTION for node:\n{state}")
             chosen_action = self._random_state.choice(legal_actions)
             self.expand_if_necessary(node, chosen_action)
        next_state = state.clone(); next_state.apply_action(chosen_action)
        returns = self.run_simulation(next_state)

    # Обратное распространение
    node.total_visits += 1
    # Обновляем статистику только если было выбрано/расширено действие
    if chosen_action != pyspiel.INVALID_ACTION:
        if chosen_action not in node.child_info:
             print(f"Warning: Child info for action {chosen_action} not found during backpropagation. Creating with prior=0.")
             self.expand_if_necessary(node, chosen_action)
        node.child_info[chosen_action].visits += 1
        if len(returns) > cur_player: node.child_info[chosen_action].return_sum += returns[cur_player]
        else: print(f"Warning: 'returns' array too short ({len(returns)}) for player {cur_player}. Using 0.")

    return returns
