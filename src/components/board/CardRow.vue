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
const emit = defineEmits(['slot-dragover', 'slot-dragleave', 'slot-drop', 'card-dragstart', 'card-dragend']);

const gameStore = useGameStore();
const isBoardFoul = computed(() => gameStore.isBoardFoul(props.playerId));
const slotCount = computed(() => props.rowIndex === 0 ? 3 : 5);

const handleDragOver = (event: DragEvent) => emit('slot-dragover', event);
const handleDragLeave = (event: DragEvent) => emit('slot-dragleave', event);
const handleDrop = (event: DragEvent, rowIndex: number, slotIndex: number) => emit('slot-drop', event, rowIndex, slotIndex);
const handleCardDragStart = (event: DragEvent, card: Card, source: 'board') => emit('card-dragstart', event, card, source);
const handleCardDragEnd = (event: DragEvent) => emit('card-dragend', event);

</script>

<template>
  <div class="card-row-container">
      <div class="card-row">
        <!-- Новый способ выравнивания верхнего ряда -->
        <template v-if="rowIndex === 0">
            <div class="slot-wrapper placeholder"></div> <!-- Пустой спейсер слева -->
            <div class="slot-wrapper" v-for="(card, index) in rowCards" :key="`${playerId}-0-${index}`">
                <CardSlot :card="card" :row-index="0" :slot-index="index" :is-foul="isBoardFoul"
                    @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="(e) => handleDrop(e, 0, index)"
                    @card-dragstart="handleCardDragStart" @card-dragend="handleCardDragEnd"
                ></CardSlot>
            </div>
             <div class="slot-wrapper placeholder"></div> <!-- Пустой спейсер справа -->
        </template>
        <!-- Для среднего и нижнего ряда -->
        <template v-else>
             <div class="slot-wrapper" v-for="(card, index) in rowCards" :key="`${playerId}-${rowIndex}-${index}`">
                <CardSlot :card="card" :row-index="rowIndex" :slot-index="index" :is-foul="isBoardFoul"
                    @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="(e) => handleDrop(e, rowIndex, index)"
                    @card-dragstart="handleCardDragStart" @card-dragend="handleCardDragEnd"
                ></CardSlot>
            </div>
        </template>
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
.card-row { display: flex; justify-content: space-between; width: 100%; }

.slot-wrapper {
    flex-basis: calc((100% - 2% * 4) / 5); /* Базис как для 5 карт */
    max-width: calc((100% - 2% * 4) / 5);
    flex-shrink: 0; flex-grow: 0;
}
.slot-wrapper.placeholder { visibility: hidden; } /* Скрываем спейсеры */

 .row-info, .row-info-placeholder {
    display: flex; justify-content: center; align-items: center; gap: 5px;
    font-size: clamp(10px, 2.5vw, 12px); min-height: 1.5em; flex-wrap: wrap; padding: 0 2px;
}
.royalty-badge { background-color: var(--royalty-bg); color: var(--royalty-text); padding: 1px 4px; border-radius: 3px; font-weight: bold; white-space: nowrap; }
.combo-name { white-space: nowrap; color: var(--text-light); }
</style>
