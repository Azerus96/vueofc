<script setup lang="ts">
import type { Card } from '@/types';
import CardComponent from '@/components/card/Card.vue';
import { computed } from 'vue';

interface Props {
  card: Card | null;
  rowIndex: number;
  slotIndex: number;
  isFoul?: boolean;
}
const props = defineProps<Props>();
// Добавляем события для D&D карты *с доски*
const emit = defineEmits(['dragover', 'dragleave', 'drop', 'card-dragstart', 'card-dragend']);

const slotClasses = computed(() => ({
    'card-slot': true,
    foul: props.isFoul
}));

const slotDataAttrs = computed(() => ({
    'data-row-index': props.rowIndex,
    'data-slot-index': props.slotIndex,
}));

// --- Обработчики D&D для слота ---
const onDragOver = (event: DragEvent) => {
    if (!props.card) { emit('dragover', event); }
    else { event.preventDefault(); event.dataTransfer!.dropEffect = 'none'; }
};
const onDragLeave = (event: DragEvent) => emit('dragleave', event);
const onDrop = (event: DragEvent) => {
    if (!props.card) { emit('drop', event, props.rowIndex, props.slotIndex); }
};

// --- Обработчики D&D для карты ВНУТРИ слота ---
const onCardDragStart = (event: DragEvent, card: Card) => {
    emit('card-dragstart', event, card, 'board'); // Передаем источник 'board'
};
const onCardDragEnd = (event: DragEvent) => {
    emit('card-dragend', event);
};

</script>

<template>
  <div
    :class="slotClasses"
    v-bind="slotDataAttrs"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- Передаем обработчики D&D в CardComponent -->
    <CardComponent
        :card="card"
        :is-draggable="!!card"
        @dragstart="(e: DragEvent) => onCardDragStart(e, card!)"
        @dragend="onCardDragEnd"
    />
  </div>
</template>

<style scoped>
.card-slot {
  /* Стили из main.css */
  padding: 0; /* Убедимся, что нет паддинга */
}
/* Класс drag-over применяется извне */
.card-slot.drag-over {
    background-color: var(--slot-bg-drag-over);
    border-color: var(--slot-border-active);
    border-style: solid;
}
.card-slot.foul {
   border-color: var(--foul-border);
}
/* Стили для карты внутри слота (чтобы она занимала весь слот) */
.card-slot :deep(.card) {
    position: absolute; /* Позиционируем карту абсолютно внутри слота */
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}
.card-slot :deep(.card-placeholder) {
     display: none; /* Скрываем плейсхолдер, если слот пуст */
}
</style>
