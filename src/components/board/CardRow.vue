<script setup lang="ts">
import type { Card, RoyaltyResult, CombinationResult } from '@/types';
import CardSlot from './CardSlot.vue';
import { useGameStore } from '@/stores/game';
import { computed } from 'vue';

interface Props {
  rowCards: (Card | null)[];
  rowIndex: number; // 0=top, 1=middle, 2=bottom
  playerId: string;
  combination: CombinationResult | null; // Передаем результат оценки
  royalty: RoyaltyResult | null; // Передаем роялти
}
const props = defineProps<Props>();
const emit = defineEmits(['slot-click']);

const gameStore = useGameStore();

const handleSlotClick = (slotIndex: number) => {
    // Клик по слоту возможен только на своей доске в свой ход
    if (gameStore.isMyTurn && props.playerId === gameStore.getMyPlayer?.id) {
         emit('slot-click', { rowIndex: props.rowIndex, slotIndex });
    }
};

// Подсвечивать ли слоты для размещения (только для текущего игрока)
const isHighlighted = computed(() =>
    gameStore.isMyTurn &&
    props.playerId === gameStore.getMyPlayer?.id &&
    gameStore.canPlaceCard
);

// Является ли вся доска фолом
const isBoardFoul = computed(() => gameStore.isBoardFoul(props.playerId));

</script>

<template>
  <div class="card-row-container">
      <div class="card-row">
        <CardSlot
          v-for="(card, index) in rowCards"
          :key="`${playerId}-${rowIndex}-${index}`"
          :card="card"
          :row-index="rowIndex"
          :slot-index="index"
          :is-highlighted="isHighlighted && !card"  // Подсвечиваем только пустые слоты
          :is-foul="isBoardFoul" // Передаем статус фола в слот
          @click="handleSlotClick(index)"
        />
      </div>
      <!-- Отображаем инфо только если есть комбинация -->
      <div class="row-info" v-if="combination">
          <span class="combo-name">{{ combination.name }}</span>
          <!-- Отображаем роялти только если оно есть и доска не фол -->
          <span v-if="royalty && !isBoardFoul" class="royalty-badge">{{ royalty.name }}</span>
      </div>
       <!-- Заглушка, чтобы высота не прыгала -->
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
  justify-content: center;
  gap: 2%;
  width: 100%;
}
 .row-info, .row-info-placeholder {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 5px;
    font-size: clamp(10px, 2.5vw, 12px); /* Мелкий шрифт для инфо */
    min-height: 1.5em; /* Резервируем место */
    flex-wrap: wrap;
    padding: 0 2px;
}
.royalty-badge {
    background-color: var(--royalty-bg);
    color: var(--royalty-text);
    padding: 1px 4px;
    border-radius: 3px;
    font-weight: bold;
    white-space: nowrap;
}
.combo-name {
    white-space: nowrap;
    color: var(--text-light);
}
</style>
