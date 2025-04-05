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
// Определяем события D&D, которые слот будет генерировать
const emit = defineEmits(['dragover', 'dragleave', 'drop']);

const slotClasses = computed(() => ({
    'card-slot': true,
    foul: props.isFoul
}));

// Data-атрибуты для передачи информации при drop
const slotDataAttrs = computed(() => ({
    'data-row-index': props.rowIndex,
    'data-slot-index': props.slotIndex,
}));

// --- Обработчики D&D для проброса наверх ---
const onDragOver = (event: DragEvent) => {
    // Разрешаем drop только если слот пуст
    if (!props.card) {
        emit('dragover', event); // Пробрасываем событие
    } else {
        event.preventDefault(); // Нужно вызвать, но эффект не меняем
        event.dataTransfer!.dropEffect = 'none'; // Запрещаем drop в занятый слот
    }
};
const onDragLeave = (event: DragEvent) => emit('dragleave', event);
const onDrop = (event: DragEvent) => {
    // Разрешаем drop только если слот пуст
    if (!props.card) {
        emit('drop', event, props.rowIndex, props.slotIndex); // Пробрасываем с данными
    }
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
    <CardComponent :card="card" />
  </div>
</template>

<style scoped>
/* Стили из main.css */
.card-slot {
  /* ... основные стили ... */
}
/* Класс drag-over будет добавляться/удаляться в App.vue через CSS или JS */
.card-slot.drag-over {
    background-color: var(--slot-bg-drag-over);
    border-color: var(--slot-border-active);
    border-style: solid;
}
.card-slot.foul {
   border-color: var(--foul-border);
}
</style>
