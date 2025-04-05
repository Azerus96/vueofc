<script setup lang="ts">
import type { Card } from '@/types';
import CardComponent from '@/components/card/Card.vue'; // Используем CardComponent
import { computed } from 'vue';

interface Props {
  card: Card | null;
  rowIndex: number;
  slotIndex: number;
  isHighlighted?: boolean; // Подсвечивать ли как доступный для размещения
  isFoul?: boolean; // Является ли часть фол-руки
}
const props = defineProps<Props>();

const slotClasses = computed(() => ({
    'card-slot': true,
    highlighted: props.isHighlighted,
    // Подсвечиваем красным, если вся доска фол (передается из CardRow)
    foul: props.isFoul
}));
</script>

<template>
  <div :class="slotClasses">
    <!-- Отображаем карту, если она есть -->
    <CardComponent :card="card" />
  </div>
</template>

<style scoped>
.card-slot {
  /* Стили из main.css */
  width: 100%; /* Занять ширину в ряду */
  height: auto; /* Высота определяется aspect-ratio */
  position: relative;
  border: 2px dashed var(--slot-border);
  border-radius: 5px;
  aspect-ratio: 2.5 / 3.5;
  min-width: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: background-color 0.2s, border-color 0.2s;
}
.card-slot.highlighted {
  border-color: var(--slot-border-active);
  background-color: var(--slot-bg-highlight);
}
.card-slot.foul {
   /* Если вся доска фол, подсвечиваем границу слота красным */
   border-color: var(--foul-border);
   /* Можно добавить и фон, если нужно */
   /* background-color: rgba(228, 65, 69, 0.1); */
}
/* Убираем внутреннюю карту, если слот пустой */
.card-slot:empty {
    /* Можно оставить стили по умолчанию или добавить что-то еще */
}
</style>
