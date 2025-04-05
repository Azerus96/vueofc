<script setup lang="ts">
import type { Card, RoyaltyResult, CombinationResult } from '@/types';
import CardSlot from './CardSlot.vue';
import { useGameStore } from '@/stores/game';
import { computed } from 'vue';

interface Props {
  rowCards: (Card | null)[];
  rowIndex: number;
  playerId: string;
  combination: CombinationResult | null;
  royalty: RoyaltyResult | null;
}
const props = defineProps<Props>();
// Пробрасываем события D&D от слотов и карт в слотах
const emit = defineEmits(['slot-dragover', 'slot-dragleave', 'slot-drop', 'card-dragstart', 'card-dragend']);

const gameStore = useGameStore();
const isBoardFoul = computed(() => gameStore.isBoardFoul(props.playerId));
const slotCount = computed(() => props.rowIndex === 0 ? 3 : 5);

// --- Обработчики для проброса событий D&D ---
const handleDragOver = (event: DragEvent) => emit('slot-dragover', event);
const handleDragLeave = (event: DragEvent) => emit('slot-dragleave', event);
const handleDrop = (event: DragEvent, rowIndex: number, slotIndex: number) => emit('slot-drop', event, rowIndex, slotIndex);
const handleCardDragStart = (event: DragEvent, card: Card, source: 'board') => emit('card-dragstart', event, card, source);
const handleCardDragEnd = (event: DragEvent) => emit('card-dragend', event);

</script>

<template>
  <div class="card-row-container">
      <div class="card-row">
        <!-- Используем пустые div'ы как спейсеры для верхнего ряда -->
        <div v-if="rowIndex === 0" class="spacer"></div>

        <div
          v-for="(card, index) in rowCards"
          :key="`${playerId}-${rowIndex}-${index}`"
          class="slot-wrapper"
        >
            <CardSlot
              :card="card"
              :row-index="rowIndex"
              :slot-index="index"
              :is-foul="isBoardFoul"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="(e) => handleDrop(e, rowIndex, index)"
              @card-dragstart="handleCardDragStart"
              @card-dragend="handleCardDragEnd"
            ></CardSlot>
        </div>

        <div v-if="rowIndex === 0" class="spacer"></div>
      </div>
      <div class="row-info" v-if="combination">
          <span class="combo-name">{{ combination.name }}</span>
          <span v-if="royalty && !isBoardFoul" class="royalty-badge">{{ royalty.name }}</span>
      </div>
      <div class="row-info-placeholder" v-else></div>
  </div>
</template>

<style scoped>
.card-row-container { display: flex; flex-direction: column; align-items: center; gap: 2px; width: 100%; }
.card-row { display: flex; justify-content: space-between; /* Распределяем равномерно */ width: 100%; }

/* Общие стили для обертки слота и спейсера */
.slot-wrapper, .spacer {
    /* Ширина как 1/5 от общей ширины (минус отступы) */
    flex-basis: calc((100% - 2% * 4) / 5);
    max-width: calc((100% - 2% * 4) / 5);
    flex-shrink: 0;
    flex-grow: 0;
}
.spacer {
    /* Делаем спейсер невидимым, но занимающим место */
    visibility: hidden;
}

 .row-info, .row-info-placeholder {
    display: flex; justify-content: center; align-items: center; gap: 5px;
    font-size: clamp(10px, 2.5vw, 12px); min-height: 1.5em; flex-wrap: wrap; padding: 0 2px;
}
.royalty-badge {
    background-color: var(--royalty-bg); color: var(--royalty-text); padding: 1px 4px;
    border-radius: 3px; font-weight: bold; white-space: nowrap;
}
.combo-name { white-space: nowrap; color: var(--text-light); }
</style>
