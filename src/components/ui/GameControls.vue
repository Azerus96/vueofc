<script setup lang="ts">
import { useGameStore } from '@/stores/game';
import { computed } from 'vue';

const gameStore = useGameStore();

const buttonText = computed(() => {
    if (gameStore.gamePhase === 'placing_street_1') {
        // На первой улице кнопка активна только когда все 5 карт размещены
        return gameStore.canConfirmAction ? 'Готово' : 'Place Cards';
    }
    if (gameStore.gamePhase === 'placing_street_2_5') {
        // Если можно подтвердить сброс (1 карта в руке, выбрана на сброс)
        if (gameStore.canConfirmAction) {
             const card = gameStore.cardsOnHand[gameStore.selectedCardToDiscardIndex!];
             return `Сбросить ${card?.rank ?? '?'}`; // Показываем ранг карты на сброс
        }
        // Если карта на сброс еще не выбрана
        else if (gameStore.selectedCardToDiscardIndex === null) {
             return `Discard (${gameStore.cardsOnHand.length})`; // Показывает "Discard (3)"
        }
        // Если карта на сброс выбрана, но не все размещены
        else {
             return 'Place Cards';
        }
    }
    return ''; // Не показывать кнопку в других фазах
});

// Активность кнопки определяется напрямую из геттера
const isButtonActive = computed(() => gameStore.canConfirmAction);

const handleConfirm = () => {
    // Действие только если кнопка активна
    if (isButtonActive.value) {
        gameStore.confirmAction();
    } else {
        // Можно добавить обратную связь, если кнопка неактивна
        console.log("Cannot confirm action now.");
    }
};

</script>

<template>
  <div class="game-controls">
    <button
      v-if="buttonText"
      @click="handleConfirm"
      :disabled="!isButtonActive"
      class="control-button"
    >
      {{ buttonText }}
    </button>
    <!-- Можно добавить другие кнопки: фолд, таймбанк и т.д. -->
  </div>
</template>

<style scoped>
.game-controls {
  display: flex;
  justify-content: center;
  padding: 10px 0;
  flex-shrink: 0; /* Не сжиматься */
}
.control-button {
  padding: 12px 25px;
  font-size: clamp(14px, 4vw, 18px); /* Адаптивный размер шрифта */
  font-weight: bold;
  background-color: var(--button-primary-bg);
  color: white;
  border: none;
  border-radius: 25px;
  cursor: pointer;
  transition: background-color 0.2s, transform 0.1s, opacity 0.2s;
  min-width: 150px;
  text-align: center;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
.control-button:hover:not(:disabled) {
  background-color: var(--button-primary-hover);
}
.control-button:active:not(:disabled) {
    transform: scale(0.98);
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}
.control-button:disabled {
  background-color: var(--button-disabled-bg);
  cursor: not-allowed;
  opacity: 0.6;
   box-shadow: none;
}
</style>
