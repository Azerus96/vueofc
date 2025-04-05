<script setup lang="ts">
import type { Card } from '@/types';
import CardComponent from '@/components/card/Card.vue';

interface Props {
    cards: Card[];
    isDraggingActive: boolean;
    draggedCardId: string | null;
}
defineProps<Props>();
// Убрали touch события и tap
const emit = defineEmits(['card-dragstart', 'card-dragend', 'zone-dragover', 'zone-dragleave', 'zone-drop']);

// --- Обработчики для проброса событий ---
const onDragStart = (event: DragEvent, card: Card) => emit('card-dragstart', event, card, 'hand'); // Явно указываем 'hand'
const onDragEnd = (event: DragEvent) => emit('card-dragend', event);
// Убрали touch обработчики
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
      <!-- Убрали touch слушатели и tap -->
      />
  </div>
</template>

<style scoped>
/* Стили из предыдущего ответа */
.player-hand { display: flex; justify-content: center; align-items: flex-end; gap: 5px; padding: 5px; background-color: rgba(0, 0, 0, 0.2); border-radius: 5px; min-height: auto; flex-wrap: wrap; flex-shrink: 0; transition: background-color 0.2s; }
.player-hand.drag-over { background-color: var(--slot-bg-drag-over); }
.player-hand :deep(.card) { width: clamp(45px, 14vw, 65px); height: auto; flex-shrink: 0; }
</style>
