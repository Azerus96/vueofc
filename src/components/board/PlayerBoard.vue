<script setup lang="ts">
import type { PlayerState, Card } from '@/types'; // Добавлен импорт Card
import CardRow from './CardRow.vue';
import { useGameStore } from '@/stores/game';

interface Props {
  player: PlayerState;
}
defineProps<Props>();
// Пробрасываем события D&D от рядов выше
const emit = defineEmits(['slot-dragover', 'slot-dragleave', 'slot-drop', 'card-dragstart', 'card-dragend']);

const gameStore = useGameStore();

// --- Обработчики для проброса событий D&D ---
const handleDragOver = (event: DragEvent) => emit('slot-dragover', event);
const handleDragLeave = (event: DragEvent) => emit('slot-dragleave', event);
const handleDrop = (event: DragEvent, rowIndex: number, slotIndex: number) => emit('slot-drop', event, rowIndex, slotIndex);
const handleCardDragStart = (event: DragEvent, card: Card, source: 'board') => emit('card-dragstart', event, card, source);
const handleCardDragEnd = (event: DragEvent) => emit('card-dragend', event);

</script>

<template>
  <!-- Доска игрока теперь тоже может быть drop зоной (для возврата карт) -->
  <div
    class="player-board"
    :class="{ active: player.isActive && gameStore.isMyTurn, foul: player.isFoul }"
    @dragover.prevent="handleDragOver" /* Обрабатываем dragover для доски */
    @dragleave="handleDragLeave" /* Обрабатываем dragleave для доски */
    @drop="handleDrop($event, -1, -1)" /* Обрабатываем drop для доски (индексы не важны) */
  >
    <div class="player-info">
      <span class="player-name">{{ player.name }}</span>
      <span class="player-score">{{ player.score }}</span>
      <span v-if="player.lastRoundScoreChange !== 0 && gameStore.gamePhase === 'round_over'"
            :class="['score-change', player.lastRoundScoreChange > 0 ? 'positive' : 'negative']">
        {{ player.lastRoundScoreChange > 0 ? '+' : '' }}{{ player.lastRoundScoreChange }}
      </span>
      <span v-if="player.isDealer" class="dealer-chip">D</span>
    </div>
    <div class="board-rows">
      <CardRow
        :row-cards="player.board.top" :row-index="0" :player-id="player.id"
        :combination="player.combinations.top" :royalty="player.royalties.top"
        @slot-dragover="handleDragOver" @slot-dragleave="handleDragLeave" @slot-drop="handleDrop"
        @card-dragstart="handleCardDragStart" @card-dragend="handleCardDragEnd"
      />
      <CardRow
        :row-cards="player.board.middle" :row-index="1" :player-id="player.id"
        :combination="player.combinations.middle" :royalty="player.royalties.middle"
        @slot-dragover="handleDragOver" @slot-dragleave="handleDragLeave" @slot-drop="handleDrop"
        @card-dragstart="handleCardDragStart" @card-dragend="handleCardDragEnd"
       />
      <CardRow
        :row-cards="player.board.bottom" :row-index="2" :player-id="player.id"
        :combination="player.combinations.bottom" :royalty="player.royalties.bottom"
        @slot-dragover="handleDragOver" @slot-dragleave="handleDragLeave" @slot-drop="handleDrop"
        @card-dragstart="handleCardDragStart" @card-dragend="handleCardDragEnd"
      />
    </div>
  </div>
</template>

<style scoped>
/* Стили из предыдущего ответа */
.player-board {
  border: 2px solid transparent; border-radius: 8px; padding: 8px 5px;
  background-color: var(--poker-green-darker); transition: border-color 0.3s;
  width: 100%; max-width: 450px; display: flex; flex-direction: column; gap: 8px;
}
.player-board.active { border-color: var(--active-player-border); }
.player-board.foul { border-color: var(--foul-border); }
.player-info { display: flex; align-items: center; gap: 8px; font-size: clamp(12px, 3vw, 14px); padding: 0 5px; min-height: 1.5em; }
.player-name { font-weight: bold; margin-right: auto; }
.player-score { font-weight: normal; }
.dealer-chip {
    background-color: var(--dealer-chip-bg); color: var(--dealer-chip-text); border-radius: 50%;
    width: 1.5em; height: 1.5em; display: inline-flex; justify-content: center; align-items: center;
    font-weight: bold; flex-shrink: 0;
}
.score-change { font-weight: bold; padding: 1px 4px; border-radius: 3px; white-space: nowrap; }
.score-change.positive { color: lightgreen; }
.score-change.negative { color: var(--card-red); }
.board-rows { display: flex; flex-direction: column; gap: 10px; }
</style>
