<script setup lang="ts">
import type { Card } from '@/types';
import CardComponent from '@/components/card/Card.vue';

interface Props {
    cards: Card[];
    selectedDiscardIndex: number | null;
    isDraggingActive: boolean; // Флаг активного перетаскивания из App.vue
    draggedCardId: string | null; // ID карты, которая перетаскивается
}
defineProps<Props>();
// Эмитим события D&D и тап наверх
const emit = defineEmits(['card-dragstart', 'card-dragend', 'card-touchstart', 'card-touchmove', 'card-touchend', 'card-tap']);

// --- Обработчики для проброса событий ---
const onDragStart = (event: DragEvent, card: Card) => emit('card-dragstart', event, card);
const onDragEnd = (event: DragEvent) => emit('card-dragend', event);
const onTouchStart = (event: TouchEvent, card: Card) => emit('card-touchstart', event, card);
const onTouchMove = (event: TouchEvent) => emit('card-touchmove', event);
const onTouchEnd = (event: TouchEvent) => emit('card-touchend', event);
// Тап по карте в руке теперь используется ТОЛЬКО для выбора карты на сброс
const onTap = (cardIndex: number) => emit('card-tap', cardIndex);

</script>

<template>
  <div class="player-hand">
    <CardComponent
      v-for="(card, index) in cards"
      :key="card.id"
      :card="card"
      :is-discard-marked="index === selectedDiscardIndex"
      :is-dragging="isDraggingActive && card.id === draggedCardId"
      @dragstart="(e) => onDragStart(e, card)"
      @dragend="onDragEnd"
      @touchstart="(e) => onTouchStart(e, card)"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
      @tap="() => onTap(index)"
    />
  </div>
</template>

<style scoped>
.player-hand {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 5px;
  padding: 10px 5px;
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 5px;
  min-height: 80px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.player-hand :deep(.card) {
    width: clamp(50px, 15vw, 70px);
    height: auto;
    flex-shrink: 0;
}
</style>
