<script setup lang="ts">
import type { Card } from '@/types';
import CardComponent from '@/components/card/Card.vue';

interface Props {
    cards: Card[];
    // selectedDiscardIndex: number | null; // Убрано
    isDraggingActive: boolean;
    draggedCardId: string | null;
}
defineProps<Props>();
// Эмитим события D&D и тап (если понадобится в будущем)
// Убрали card-tap, т.к. сброс автоматический
const emit = defineEmits(['card-dragstart', 'card-dragend', 'card-touchstart', 'card-touchmove', 'card-touchend', 'zone-dragover', 'zone-dragleave', 'zone-drop']);

// --- Обработчики для проброса событий ---
const onDragStart = (event: DragEvent, card: Card) => emit('card-dragstart', event, card, 'hand'); // Указываем источник 'hand'
const onDragEnd = (event: DragEvent) => emit('card-dragend', event);
const onTouchStart = (event: TouchEvent, card: Card) => emit('card-touchstart', event, card);
const onTouchMove = (event: TouchEvent) => emit('card-touchmove', event);
const onTouchEnd = (event: TouchEvent) => emit('card-touchend', event);
// const onTap = (cardIndex: number) => emit('card-tap', cardIndex); // Убрали

// --- Обработчики для зоны руки (возврат карт) ---
const onZoneDragOver = (event: DragEvent) => emit('zone-dragover', event);
const onZoneDragLeave = (event: DragEvent) => emit('zone-dragleave', event);
const onZoneDrop = (event: DragEvent) => emit('zone-drop', event);

</script>

<template>
  <div
    class="player-hand"
    @dragover.prevent="onZoneDragOver"
    @dragleave="onZoneDragLeave"
    @drop="onZoneDrop"
  >
    <CardComponent
      v-for="(card) in cards"
      :key="card.id"
      :card="card"
      :is-dragging="isDraggingActive && card.id === draggedCardId"
      @dragstart="(e: DragEvent) => onDragStart(e, card)"
      @dragend="onDragEnd"
      @touchstart="(e: TouchEvent) => onTouchStart(e, card)"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
      />
      <!-- Убрали @tap -->
  </div>
</template>

<style scoped>
.player-hand {
  display: flex; justify-content: center; align-items: flex-end; gap: 5px;
  padding: 5px; background-color: rgba(0, 0, 0, 0.2); border-radius: 5px;
  min-height: auto; /* Убрали min-height */ flex-wrap: wrap; flex-shrink: 0;
  transition: background-color 0.2s; /* Анимация для подсветки */
}
.player-hand.drag-over { /* Стиль при наведении карты для возврата */
    background-color: var(--slot-bg-drag-over);
}
.player-hand :deep(.card) {
    width: clamp(45px, 14vw, 65px); /* Уменьшены карты в руке */
    height: auto; flex-shrink: 0;
}
</style>
