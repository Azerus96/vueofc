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
// Пробрасываем события D&D от слотов выше
const emit = defineEmits(['slot-dragover', 'slot-dragleave', 'slot-drop']);

const gameStore = useGameStore();
const isBoardFoul = computed(() => gameStore.isBoardFoul(props.playerId));

// --- Обработчики для проброса событий D&D ---
const handleDragOver = (event: DragEvent) => emit('slot-dragover', event);
const handleDragLeave = (event: DragEvent) => emit('slot-dragleave', event);
const handleDrop = (event: DragEvent, rowIndex: number, slotIndex: number) => {
    emit('slot-drop', event, rowIndex, slotIndex);
};

// Определяем количество слотов в ряду
const slotCount = computed(() => props.rowIndex === 0 ? 3 : 5);

</script>

<template>
  <div class="card-row-container">
      <!-- Используем justify-content: center для всех рядов для простоты -->
      <div class="card-row">
        <!-- Обертка для центрирования -->
        <div class="row-content" :class="`row-${slotCount}`">
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
                ></CardSlot>
            </div>
        </div>
      </div>
      <div class="row-info" v-if="combination">
          <span class="combo-name">{{ combination.name }}</span>
          <span v-if="royalty && !isBoardFoul" class="royalty-badge">{{ royalty.name }}</span>
      </div>
      <div class="row-info-placeholder" v-else></div>
  </div>
</template>

<style scoped>
.card-row-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    width: 100%;
}
.card-row {
  display: flex;
  justify-content: center; /* Центрируем содержимое ряда */
  width: 100%;
}
.row-content {
    display: flex;
    justify-content: center;
    gap: 2%; /* Отступы между обертками слотов */
    width: 100%;
}
/* Ограничиваем ширину ряда с 3 картами, чтобы они были того же размера */
.row-content.row-3 {
    /* (100% / 5 слотов) * 3 слота + 2% * 2 промежутка */
    width: calc(60% + 4%);
    max-width: 100%; /* На случай очень узких экранов */
}
.row-content.row-5 {
    width: 100%; /* Ряд с 5 картами занимает всю ширину */
}

.slot-wrapper {
    /* Ширина слота теперь одинакова для всех рядов */
    flex-basis: calc((100% - 2% * 4) / 5); /* Базис как для 5 карт */
    max-width: calc((100% - 2% * 4) / 5);
    flex-shrink: 0;
    flex-grow: 0;
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
