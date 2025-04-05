<script setup lang="ts">
import type { PlayerState } from '@/types';
import CardRow from './CardRow.vue';
import { useGameStore } from '@/stores/game';

interface Props {
  player: PlayerState;
}
const props = defineProps<Props>();
const gameStore = useGameStore();

const handleSlotClick = (payload: { rowIndex: number; slotIndex: number }) => {
    gameStore.placeSelectedCard(payload.rowIndex, payload.slotIndex);
};

</script>

<template>
  <div class="player-board" :class="{ active: player.isActive, foul: player.isFoul }">
    <div class="player-info">
      <span class="player-name">{{ player.name }}</span>
      <span class="player-score">{{ player.score }}</span>
      <!-- Отображение изменения счета -->
      <span v-if="player.lastRoundScoreChange !== 0 && gameStore.gamePhase === 'round_over'"
            :class="['score-change', player.lastRoundScoreChange > 0 ? 'positive' : 'negative']">
        {{ player.lastRoundScoreChange > 0 ? '+' : '' }}{{ player.lastRoundScoreChange }}
      </span>
      <span v-if="player.isDealer" class="dealer-chip">D</span>
       <!-- TODO: Timer -->
    </div>
    <div class="board-rows">
      <CardRow
        :row-cards="player.board.top"
        :row-index="0"
        :player-id="player.id"
        :combination="player.combinations.top"
        :royalty="player.royalties.top"
        @slot-click="handleSlotClick"
      />
      <CardRow
        :row-cards="player.board.middle"
        :row-index="1"
        :player-id="player.id"
        :combination="player.combinations.middle"
        :royalty="player.royalties.middle"
        @slot-click="handleSlotClick"
       />
      <CardRow
        :row-cards="player.board.bottom"
        :row-index="2"
        :player-id="player.id"
        :combination="player.combinations.bottom"
        :royalty="player.royalties.bottom"
        @slot-click="handleSlotClick"
      />
    </div>
  </div>
</template>

<style scoped>
.player-board {
  border: 2px solid transparent;
  border-radius: 8px;
  padding: 8px 5px; /* Немного больше паддинг */
  background-color: var(--poker-green-darker); /* Темнее фон для своей доски */
  transition: border-color 0.3s;
  width: 100%;
  max-width: 450px;
  display: flex;
  flex-direction: column;
  gap: 8px; /* Увеличим отступ */
}
.player-board.active {
  /* Подсветка только если это ход игрока (не ИИ) */
  border-color: var(--active-player-border);
}
 .player-board.foul {
  border-color: var(--foul-border);
}
.player-info {
  display: flex;
  /* justify-content: space-between; */
  align-items: center;
  gap: 8px; /* Отступ между элементами инфо */
  font-size: clamp(12px, 3vw, 14px);
  padding: 0 5px;
  min-height: 1.5em;
}
.player-name {
    font-weight: bold;
    margin-right: auto; /* Имя слева, остальное справа */
}
.player-score {
    font-weight: normal;
}
.dealer-chip {
    background-color: var(--dealer-chip-bg);
    color: var(--dealer-chip-text);
    border-radius: 50%;
    width: 1.5em;
    height: 1.5em;
    display: inline-flex;
    justify-content: center;
    align-items: center;
    font-weight: bold;
    /* margin-left: 5px; */
    flex-shrink: 0;
}
.score-change {
    font-weight: bold;
    /* margin: 0 5px; */
    padding: 1px 4px;
    border-radius: 3px;
    white-space: nowrap;
}
.score-change.positive {
    color: lightgreen;
    /* background-color: rgba(0, 255, 0, 0.1); */
}
 .score-change.negative {
    color: var(--card-red);
     /* background-color: rgba(255, 0, 0, 0.1); */
}
.board-rows {
  display: flex;
  flex-direction: column;
  gap: 10px; /* Отступ между рядами */
}
</style>
