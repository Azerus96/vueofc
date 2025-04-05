<script setup lang="ts">
import { onMounted, computed } from 'vue';
import { useGameStore } from '@/stores/game';
import PlayerBoard from '@/components/board/PlayerBoard.vue';
import OpponentBoard from '@/components/board/OpponentBoard.vue';
import PlayerHand from '@/components/ui/PlayerHand.vue';
import GameControls from '@/components/ui/GameControls.vue';
// import ScoreDisplay from '@/components/ui/ScoreDisplay.vue'; // Компонент для анимации очков

const gameStore = useGameStore();

onMounted(() => {
  // Инициализируем игру при загрузке (3 игрока)
  gameStore.initializeGame(['You', 'Opponent 1', 'Opponent 2'], 5000);
});

// Определяем, нужно ли показывать руку и контролы
const showHandAndControls = computed(() => {
    return gameStore.isMyTurn &&
           (gameStore.gamePhase === 'placing_street_1' || gameStore.gamePhase === 'placing_street_2_5');
});

</script>

<template>
  <div class="game-container">
    <!-- Зона оппонентов -->
    <div class="opponents-area">
      <OpponentBoard
        v-for="opponent in gameStore.getOpponents"
        :key="opponent.id"
        :player="opponent"
      />
    </div>

    <!-- Сообщение для игрока -->
    <div class="game-message" v-if="gameStore.message">
        {{ gameStore.message }}
    </div>

    <!-- Зона игрока -->
    <div class="player-area">
       <PlayerBoard :player="gameStore.getMyPlayer" v-if="gameStore.getMyPlayer" />
    </div>

    <!-- Рука игрока (появляется только в ход игрока на фазе расстановки) -->
    <PlayerHand v-if="showHandAndControls" />

    <!-- Контролы игрока (появляются только в ход игрока на фазе расстановки) -->
    <GameControls v-if="showHandAndControls" />

    <!-- TODO: Компонент для анимации результатов вскрытия -->
    <!-- <ScoreDisplay :results="gameStore.showdownResults" v-if="gameStore.gamePhase === 'round_over'" /> -->

  </div>
</template>

<style scoped>
.game-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* Занять всю высоту */
  padding: 5px;
  gap: 8px; /* Пространство между зонами */
}

.opponents-area {
  display: flex;
  justify-content: space-around;
  gap: 8px;
  flex-shrink: 0; /* Не сжиматься */
}

.game-message {
    text-align: center;
    padding: 5px;
    font-size: 0.9em;
    min-height: 1.2em;
    flex-shrink: 0;
    color: var(--text-light);
    background-color: rgba(0,0,0,0.2);
    border-radius: 4px;
}

.player-area {
  flex-grow: 1; /* Занять основное пространство */
  display: flex;
  justify-content: center;
  align-items: center; /* Центрировать поле игрока */
  min-height: 250px; /* Дать достаточно места полю */
}

/* Стили для PlayerHand и GameControls будут в их компонентах */
</style>
