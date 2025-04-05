<script setup lang="ts">
import { useGameStore } from '@/stores/game';
import { computed } from 'vue';

const gameStore = useGameStore();

const buttonText = computed(() => {
    // Кнопка отображается только если можно подтвердить действие
    if (gameStore.canConfirmAction) {
        if (gameStore.gamePhase === 'placing_street_1') {
            return 'Готово';
        }
        if (gameStore.gamePhase === 'placing_street_2_5') {
            // Показываем карту, которая будет сброшена
            const cardToDiscard = gameStore.cardsOnHand[0]; // Единственная оставшаяся карта
            return `Готово (Сброс ${cardToDiscard?.rank ?? '?'})`;
        }
    }
    return ''; // Не показывать кнопку, если действие нельзя подтвердить
});

// Кнопка активна, если можно подтвердить действие
const isButtonActive = computed(() => gameStore.canConfirmAction);

const handleConfirm = () => {
    if (isButtonActive.value) {
        gameStore.confirmAction();
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
  </div>
</template>

<style scoped>
/* Стили из предыдущего ответа */
.game-controls { display: flex; justify-content: center; padding: 5px 0; flex-shrink: 0; }
.control-button {
  padding: 10px 20px; /* Уменьшен padding */ font-size: clamp(14px, 3.8vw, 17px); font-weight: bold;
  background-color: var(--button-primary-bg); color: white; border: none; border-radius: 25px;
  cursor: pointer; transition: background-color 0.2s, transform 0.1s, opacity 0.2s;
  min-width: 140px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
.control-button:hover:not(:disabled) { background-color: var(--button-primary-hover); }
.control-button:active:not(:disabled) { transform: scale(0.98); box-shadow: 0 1px 2px rgba(0,0,0,0.2); }
.control-button:disabled { background-color: var(--button-disabled-bg); cursor: not-allowed; opacity: 0.6; box-shadow: none; }
</style>
