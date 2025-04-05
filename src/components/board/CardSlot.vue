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
const emit = defineEmits(['dragover', 'dragleave', 'drop', 'card-dragstart', 'card-dragend']);

const slotClasses = computed(() => ({ 'card-slot': true, foul: props.isFoul }));
const slotDataAttrs = computed(() => ({ 'data-row-index': props.rowIndex, 'data-slot-index': props.slotIndex, }));

const onDragOver = (event: DragEvent) => {
    if (!props.card) { emit('dragover', event); }
    else { event.preventDefault(); event.dataTransfer!.dropEffect = 'none'; }
};
const onDragLeave = (event: DragEvent) => emit('dragleave', event);
const onDrop = (event: DragEvent) => { if (!props.card) { emit('drop', event, props.rowIndex, props.slotIndex); } };
const onCardDragStart = (event: DragEvent, card: Card) => emit('card-dragstart', event, card, 'board');
const onCardDragEnd = (event: DragEvent) => emit('card-dragend', event);

</script>

<template>
  <div :class="slotClasses" v-bind="slotDataAttrs"
    @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
    <CardComponent :card="card" :is-draggable="!!card"
        @dragstart="(e: DragEvent) => onCardDragStart(e, card!)"
        @dragend="onCardDragEnd" />
  </div>
</template>

<style scoped>
.card-slot {
  border: 2px dashed var(--slot-border); border-radius: 5px; aspect-ratio: 2.5 / 3.5;
  min-width: 40px; display: flex; justify-content: center; align-items: center;
  transition: background-color 0.2s, border-color 0.2s; width: 100%; height: auto; position: relative;
  padding: 0; /* Убран паддинг */
}
.card-slot.drag-over { background-color: var(--slot-bg-drag-over); border-color: var(--slot-border-active); border-style: solid; }
.card-slot.foul { border-color: var(--foul-border); }
.card-slot :deep(.card) { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.card-slot :deep(.card-placeholder) { display: none; }
</style>
