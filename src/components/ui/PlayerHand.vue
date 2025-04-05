<script setup lang="ts">
import { useGameStore } from '@/stores/game';
import CardComponent from '@/components/card/Card.vue';
import { computed } from 'vue';

const gameStore = useGameStore();

const handleCardClick = (index: number) => {
    // Клик по карте в руке только если это ход игрока
    if (gameStore.isMyTurn) {
        gameStore.selectCard(index);
    }
};

// Определяем, выбрана ли карта для размещения
const isSelectedForPlacement = (index: number) => {
    return index === gameStore.selectedCardToPlaceIndex;
}
// Определяем, помечена ли карта для сброса
const isMarkedForDiscard = (index: number) => {
     return index === gameStore.selectedCardToDiscardIndex;
}

</script>

<template>
  <div class="player-hand">
    <CardComponent
      v-for="(card, index) in gameStore.cardsOnHand"
      :key="card.id"
      :card="card"
      :is-selected="isSelectedForPlacement(index)"
      :is-discard-marked="isMarkedForDiscard(index)"
      @click="handleCardClick(index)"
    />
  </div>
</template>

<style scoped>
.player-hand {
  display: flex;
  justify-content: center;
  align-items: flex-end; /* Карты "стоят" на нижней линии */
  gap: 5px;
  padding: 10px 5px;
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 5px;
  min-height: 80px; /* Минимальная высота */
  flex-wrap: wrap; /* Перенос карт, если не влезают */
  flex-shrink: 0; /* Не сжиматься */
}
/* Ограничиваем размер карт в руке */
.player-hand :deep(.card) {
    width: clamp(50px, 15vw, 70px); /* Адаптивная ширина */
    height: auto; /* Высота по aspect-ratio */
    flex-shrink: 0;
}
</style>
