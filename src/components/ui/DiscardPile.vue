<script setup lang="ts">
import type { Card } from '@/types';
import CardComponent from '@/components/card/Card.vue';

interface Props {
    cards: Card[];
}
defineProps<Props>();

</script>

<template>
    <div class="discard-pile">
        <!-- Отображаем карты стопкой, последняя сверху -->
        <!-- Ограничим количество видимых карт, например, последними 5 -->
        <div
            v-for="(card, index) in cards.slice(-5)"
            :key="card.id"
            class="discarded-card-wrapper"
            :style="{ top: `${index * 12}px`, zIndex: index + 1 }"
        >
             <!-- Передаем isDraggable=false, чтобы нельзя было утащить из сброса -->
            <CardComponent :card="card" :is-draggable="false" />
        </div>
    </div>
</template>

<style scoped>
.discard-pile {
    position: relative; /* Для позиционирования карт внутри */
    width: 100%;
    height: 100%; /* Занимает высоту родителя (.player-section) */
    min-height: 100px; /* Минимальная высота для отображения стопки */
}
.discarded-card-wrapper {
    position: absolute;
    left: 0;
    width: 100%; /* Ширина обертки равна ширине колонки */
    /* top и z-index задаются инлайн стилем */
}
/* Уменьшаем размер карт в сбросе */
.discarded-card-wrapper :deep(.card) {
    font-size: clamp(8px, 2vw, 10px); /* Очень маленький шрифт */
    border-radius: 3px;
    box-shadow: 0 1px 1px rgba(0,0,0,0.2);
    opacity: 0.8; /* Полупрозрачные */
}
</style>
