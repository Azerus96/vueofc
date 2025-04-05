 <script setup lang="ts">
import type { PlayerState } from '@/types';
import CardRow from './CardRow.vue';
import { useGameStore } from '@/stores/game'; // Импортируем стор

interface Props {
  player: PlayerState;
}
defineProps<Props>();
const gameStore = useGameStore(); // Получаем доступ к стору

</script>

<template>
  <div class="opponent-board" :class="{ active: player.isActive, foul: player.isFoul }">
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
      />
      <CardRow
        :row-cards="player.board.middle"
        :row-index="1"
        :player-id="player.id"
        :combination="player.combinations.middle"
        :royalty="player.royalties.middle"
       />
      <CardRow
        :row-cards="player.board.bottom"
        :row-index="2"
        :player-id="player.id"
        :combination="player.combinations.bottom"
        :royalty="player.royalties.bottom"
      />
    </div>
  </div>
</template>

<style scoped>
.opponent-board {
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 5px;
  padding: 4px;
  background-color: rgba(0, 0, 0, 0.1);
  transition: border-color 0.3s, opacity 0.3s;
  width: 48%; /* Примерно половина ширины */
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 0.8em; /* Меньше шрифт */
}
 .opponent-board.active {
  border-color: lightblue; /* Подсветка хода оппонента */
}
 .opponent-board.foul {
  border-color: var(--foul-border);
  opacity: 0.7;
}
.player-info {
  display: flex;
  /* justify-content: space-between; */
  align-items: center;
  gap: 5px; /* Отступ между элементами инфо */
  padding: 0 3px;
   min-height: 1.5em;
}
 .player-name {
    font-weight: bold;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    max-width: 40%; /* Ограничить ширину имени */
    margin-right: auto; /* Имя слева */
}
.player-score {
    font-weight: normal;
    white-space: nowrap;
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
    /* margin-left: 3px; */
    font-size: 0.9em;
    flex-shrink: 0;
}
 .score-change {
    font-weight: bold;
    /* margin: 0 3px; */
    padding: 0px 3px;
    border-radius: 2px;
    font-size: 0.9em;
    white-space: nowrap;
}
.score-change.positive { color: lightgreen; }
.score-change.negative { color: var(--card-red); }
.board-rows {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
/* Уменьшим карты внутри оппонента */
.opponent-board :deep(.card) {
    font-size: clamp(10px, 3vw, 14px);
}
 .opponent-board :deep(.card-slot) {
    border-width: 1px;
    min-width: 30px;
}
 .opponent-board :deep(.row-info) {
    font-size: 0.8em;
    min-height: 1.2em;
}
 .opponent-board :deep(.royalty-badge) {
    padding: 0px 3px;
    font-size: 0.9em;
}
</style>
