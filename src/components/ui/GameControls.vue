<script setup lang="ts">
import { useGameStore } from '@/stores/game';
import { computed } from 'vue';

const gameStore = useGameStore();

const buttonText = computed(() => {
    if (gameStore.canConfirmAction) {
        if (gameStore.gamePhase === 'placing_street_1') {
            return 'Готово';
        }
        if (gameStore.gamePhase === 'placing_street_2_5') {
            // На улицах 2-5 кнопка "Готово" появляется, когда 2 карты размещены
            return 'Готово'; // Текст всегда "Готово", т.к. сброс автоматический
        }
    }
    // Если действие нельзя подтвердить, кнопку не показываем или показываем неактивной
    // В данном случае просто не показываем (v-if в шаблоне)
    return '';
});

const isButtonActive = computed(() => gameStore.canConfirmAction);

const handleConfirm = () => {
    if (isButtonActive.value) {
        gameStore.confirmAction();
    }
};

</script>

<template>
  <div class="game-controls">
    <!-- Кнопка показывается только если действие можно подтвердить -->
    <button
      v-if="isButtonActive"
      @click="handleConfirm"
      class="control-button"
    >
      {{ buttonText }}
    </button>
  </div>
</template>

<style scoped>
/* Стили из предыдущего ответа */
.game-controls { display: flex; justify-content: center; padding: 5px 0; flex-shrink: 0; min-height: 45px; /* Резервируем место под кнопку */}
.control-button {
  padding: 10px 20px; font-size: clamp(14px, 3.8vw, 17px); font-weight: bold;
  background-color: var(--button-primary-bg); color: white; border: none; border-radius: 25px;
  cursor: pointer; transition: background-color 0.2s, transform 0.1s, opacity 0.2s;
  min-width: 140px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
.control-button:hover:not(:disabled) { background-color: var(--button-primary-hover); }
.control-button:active:not(:disabled) { transform: scale(0.98); box-shadow: 0 1px 2px rgba(0,0,0,0.2); }
/* Убрали стиль :disabled, т.к. кнопка просто не рендерится */
</style>
