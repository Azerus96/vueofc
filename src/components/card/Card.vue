<script setup lang="ts">
import type { Card, Suit } from '@/types';
import { computed } from 'vue';

interface Props {
  card: Card | null;
  // isSelected?: boolean; // Убрано, т.к. выбор теперь через D&D или тап для сброса
  isDiscardMarked?: boolean;
  isDragging?: boolean; // Флаг, что эта карта сейчас перетаскивается (управляется извне)
}
const props = defineProps<Props>();
// Определяем события, которые компонент может генерировать
const emit = defineEmits(['dragstart', 'dragend', 'touchstart', 'touchmove', 'touchend', 'tap']);

// Вычисляем символ масти (Unicode)
const suitSymbol = computed(() => {
  if (!props.card) return '';
  const symbols: Record<Suit, string> = { s: '♠', h: '♥', d: '♦', c: '♣' };
  return symbols[props.card.suit];
});

// Отображаемый текст карты
const cardDisplay = computed(() => {
    if (!props.card) return '';
    return `${props.card.rank}${suitSymbol.value}`;
});

// Классы для стилизации
const cardClasses = computed(() => ({
    card: true,
    'discard-marked': props.isDiscardMarked,
    dragging: props.isDragging, // Применяем класс, если isDragging true
    'suit-red': props.card?.suit === 'h' || props.card?.suit === 'd',
    'suit-black': props.card?.suit === 's' || props.card?.suit === 'c',
}));

// Data-атрибуты
const cardDataAttrs = computed(() => ({
    'data-id': props.card?.id, // ID важен для D&D
    'data-suit': props.card?.suit,
    'data-rank': props.card?.rank,
}));

// --- Обработчики событий для проброса наверх ---
const onDragStart = (event: DragEvent) => {
    // Запрещаем D&D для помеченной карты
    if (props.isDiscardMarked) {
        event.preventDefault();
        return;
    }
    if (props.card) emit('dragstart', event, props.card);
};
const onDragEnd = (event: DragEvent) => emit('dragend', event);
const onTouchStart = (event: TouchEvent) => {
     // Запрещаем D&D для помеченной карты
    if (props.isDiscardMarked) {
        // Не вызываем preventDefault, чтобы тап сработал для отмены
        return;
    }
    if (props.card) emit('touchstart', event, props.card);
};
const onTouchMove = (event: TouchEvent) => emit('touchmove', event);
const onTouchEnd = (event: TouchEvent) => emit('touchend', event);
// Тап используется для выбора/отмены выбора карты на сброс
const onTap = (event: Event) => emit('tap', event); // Передаем событие наверх

</script>

<template>
  <div
    v-if="card"
    :class="cardClasses"
    v-bind="cardDataAttrs"
    :draggable="!isDiscardMarked"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
    @touchstart.passive="onTouchStart"  
    @touchmove.passive="onTouchMove"    
    @touchend.passive="onTouchEnd"      
    @click="onTap"
  >
    <div class="card-content">{{ cardDisplay }}</div>
    <div v-if="isDiscardMarked" class="discard-marker">X</div>
  </div>
  <div v-else class="card-placeholder"></div>
</template>

<style scoped>
/* Стили из main.css + специфичные */
.card {
  cursor: grab;
  touch-action: none; /* Важно для предотвращения конфликтов скролла при touch D&D */
}
.card.dragging {
    opacity: 0.4 !important;
    cursor: grabbing;
    /* transform: scale(1.05); */
}
.card.discard-marked {
    cursor: pointer; /* Можно тапнуть для отмены */
}
.card-content {
    text-align: center;
    line-height: 1;
    pointer-events: none; /* Чтобы не мешать событиям на самой карте */
}
.discard-marker {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-color: var(--discard-marker-bg);
    color: var(--card-black);
    display: flex; justify-content: center; align-items: center;
    font-size: 2em; font-weight: bold;
    border-radius: inherit; z-index: 1;
    pointer-events: none; /* Не мешать тапу по карте */
}
.card-placeholder {
    width: 100%; height: 100%; aspect-ratio: 2.5 / 3.5;
    border-radius: 5px; background-color: rgba(255, 255, 255, 0.05);
}
</style>
