<script setup lang="ts">
import type { Card, Suit } from '@/types';
import { computed } from 'vue';

interface Props {
  card: Card | null;
  isDragging?: boolean;
  isDraggable?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
    isDraggable: true,
});
const emit = defineEmits(['dragstart', 'dragend', 'touchstart', 'touchmove', 'touchend']);

const suitSymbol = computed(() => {
  if (!props.card) return '';
  const symbols: Record<Suit, string> = { s: '♠', h: '♥', d: '♦', c: '♣' };
  return symbols[props.card.suit];
});

const cardDisplay = computed(() => {
    if (!props.card) return '';
    return `${props.card.rank}${suitSymbol.value}`;
});

const cardClasses = computed(() => ({
    card: true,
    dragging: props.isDragging,
    'suit-red': props.card?.suit === 'h' || props.card?.suit === 'd',
    'suit-black': props.card?.suit === 's' || props.card?.suit === 'c',
}));

const cardDataAttrs = computed(() => ({
    'data-id': props.card?.id,
    'data-suit': props.card?.suit,
    'data-rank': props.card?.rank,
}));

const onDragStart = (event: DragEvent) => {
    if (props.card && props.isDraggable) emit('dragstart', event, props.card);
    else event.preventDefault();
};
const onDragEnd = (event: DragEvent) => emit('dragend', event);
const onTouchStart = (event: TouchEvent) => {
    if (props.card && props.isDraggable) emit('touchstart', event, props.card);
};
// Убрали .passive, чтобы иметь возможность вызвать preventDefault если нужно (хотя пока не используем)
const onTouchMove = (event: TouchEvent) => emit('touchmove', event);
const onTouchEnd = (event: TouchEvent) => emit('touchend', event);

</script>

<template>
  <div
    v-if="card"
    :class="cardClasses"
    v-bind="cardDataAttrs"
    :draggable="isDraggable"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
    @touchstart="onTouchStart"
    @touchmove="onTouchMove"
    @touchend="onTouchEnd"
  >
    <div class="card-content">{{ cardDisplay }}</div>
  </div>
  <div v-else class="card-placeholder"></div>
</template>

<style scoped>
/* Стили из предыдущего ответа */
.card { cursor: grab; touch-action: none; }
.card:not([draggable="true"]) { cursor: default; }
.card.dragging { opacity: 0.4 !important; cursor: grabbing; }
.card-content { text-align: center; line-height: 1; pointer-events: none; color: var(--card-black) !important; }
.card-placeholder { width: 100%; height: 100%; aspect-ratio: 2.5 / 3.5; border-radius: 5px; background-color: rgba(255, 255, 255, 0.05); }
</style>
