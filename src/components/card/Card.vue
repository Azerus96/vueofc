<script setup lang="ts">
import type { Card, Suit } from '@/types';
import { computed } from 'vue';

interface Props {
  card: Card | null;
  isSelected?: boolean;
  isDiscardMarked?: boolean;
  isGhost?: boolean; // Для анимации или предпросмотра
}
const props = defineProps<Props>();

// Вычисляем символ масти
const suitSymbol = computed(() => {
  if (!props.card) return '';
  const symbols: Record<Suit, string> = { s: '♠', h: '♥', d: '♦', c: '♣' };
  return symbols[props.card.suit];
});

// Вычисляем отображаемый текст карты (Ранг + Символ масти)
const cardDisplay = computed(() => {
    if (!props.card) return '';
    // Используем display из объекта Card, если он есть, иначе формируем
    return props.card.display || `${props.card.rank}${suitSymbol.value}`;
});

// Классы для стилизации карты
const cardClasses = computed(() => ({
    card: true,
    selected: props.isSelected,
    'discard-marked': props.isDiscardMarked,
    ghost: props.isGhost,
    // Добавляем классы для цвета масти прямо на основной элемент
    'suit-red': props.card?.suit === 'h' || props.card?.suit === 'd',
    'suit-black': props.card?.suit === 's' || props.card?.suit === 'c',
}));

// Data-атрибуты остаются полезными для селекторов или тестирования
const cardDataAttrs = computed(() => ({
    'data-suit': props.card?.suit,
    'data-rank': props.card?.rank,
}));

</script>

<template>
  <div v-if="card" :class="cardClasses" v-bind="cardDataAttrs">
    <!-- Отображаем объединенный текст -->
    <div class="card-content">{{ cardDisplay }}</div>
    <!-- Маркер сброса остается отдельным элементом для позиционирования -->
    <div v-if="isDiscardMarked" class="discard-marker">X</div>
  </div>
  <!-- Можно добавить пустой слот или другую заглушку, если card === null -->
  <div v-else class="card-placeholder"></div> <!-- Пример заглушки -->
</template>

<style scoped>
.card {
  /* Базовые стили из main.css */
  transition: transform 0.2s ease-out, box-shadow 0.2s ease-out, opacity 0.2s;
  width: 100%;
  height: 100%;
  display: flex; /* Используем flex для центрирования контента */
  justify-content: center;
  align-items: center;
  font-weight: bold;
  position: relative; /* Для позиционирования маркера */
  overflow: hidden;
  border-radius: 5px; /* Убедимся, что скругление есть */
  background-color: var(--card-bg);
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  user-select: none;
  -webkit-user-select: none;
  cursor: pointer;
  aspect-ratio: 2.5 / 3.5;
  min-width: 40px;
  font-size: clamp(16px, 4vw, 22px); /* Сделаем шрифт чуть крупнее */
}

/* Применяем цвет к основному элементу */
.card.suit-red {
  color: var(--card-red);
}
.card.suit-black {
  color: var(--card-black);
}

.card-content {
    /* Можно добавить стили для текста, если нужно */
    text-align: center;
    line-height: 1; /* Убрать лишнюю высоту строки */
}

.card.selected {
  transform: translateY(-10px) scale(1.05);
  box-shadow: 0 4px 8px rgba(0,0,0,0.3);
}
.card.ghost {
    opacity: 0.5;
}
.discard-marker {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--discard-marker-bg);
    color: var(--card-black); /* Черный X на желтом фоне */
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 2em; /* Крупный X */
    font-weight: bold;
    border-radius: inherit;
    z-index: 1; /* Поверх основного текста */
}
.card-placeholder {
    /* Стили для пустой карты, если нужно */
    width: 100%;
    height: 100%;
    aspect-ratio: 2.5 / 3.5;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.05); /* Полупрозрачный фон */
}
</style>
