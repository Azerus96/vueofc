<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useGameStore } from '@/stores/game';
import PlayerBoard from '@/components/board/PlayerBoard.vue';
import OpponentBoard from '@/components/board/OpponentBoard.vue';
import PlayerHand from '@/components/ui/PlayerHand.vue';
import GameControls from '@/components/ui/GameControls.vue';
import type { Card } from '@/types'; // Импортируем тип Card

const gameStore = useGameStore();

// Состояние для меню
const isMenuOpen = ref(false);
const selectedOpponentCount = ref<1 | 2>(gameStore.opponentCount);

// Состояние для Drag & Drop
const draggedCardId = ref<string | null>(null);
const isDragging = ref(false); // Флаг активного перетаскивания

// --- Управление меню ---
const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value;
};

const closeMenu = () => {
  isMenuOpen.value = false;
};

const confirmSettings = () => {
    gameStore.setOpponentCount(selectedOpponentCount.value);
    closeMenu();
    if (gameStore.isGameInProgress) {
        alert("Настройки количества оппонентов применятся со следующей игры.");
    }
};

const menuElement = ref<HTMLElement | null>(null);
const handleClickOutside = (event: MouseEvent) => {
    if (isMenuOpen.value && menuElement.value && !menuElement.value.contains(event.target as Node)) {
        // Игнорируем клик по кнопке меню
        const menuButton = document.querySelector('.menu-button');
        if (!menuButton || !menuButton.contains(event.target as Node)) {
            closeMenu();
        }
    }
};

watch(isMenuOpen, (isOpen) => {
    if (isOpen) {
        // Используем setTimeout, чтобы listener добавился после текущего клика
        setTimeout(() => document.addEventListener('click', handleClickOutside, true), 0);
    } else {
        document.removeEventListener('click', handleClickOutside, true);
    }
});

// --- Старт игры ---
const handleStartGame = () => {
    gameStore.startGame();
};

// --- Полноэкранный режим ---
const isFullscreen = ref(!!document.fullscreenElement);
const toggleFullScreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(err => {
      console.error(`Ошибка входа в полноэкранный режим: ${err.message} (${err.name})`);
    }).then(() => isFullscreen.value = !!document.fullscreenElement);
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen().then(() => isFullscreen.value = false);
    }
  }
};
document.addEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement;
});

// --- Логика Drag & Drop ---
const handleCardDragStart = (event: DragEvent, card: Card) => {
    if (!gameStore.isMyTurn) return;
    const cardIndex = gameStore.cardsOnHand.findIndex(c => c.id === card.id);
    if (gameStore.gamePhase === 'placing_street_2_5' && cardIndex === gameStore.selectedCardToDiscardIndex) {
        event.preventDefault();
        gameStore.message = "Нельзя перетащить карту для сброса";
        return;
    }
    draggedCardId.value = card.id;
    isDragging.value = true; // Устанавливаем флаг
    event.dataTransfer!.setData('text/plain', card.id);
    event.dataTransfer!.effectAllowed = 'move';
};

const handleCardDragEnd = () => {
    // Сбрасываем флаг только если это была та карта, которую тащили
    // (на случай если событие сработает не на той карте)
    // if (draggedCardId.value) {
        draggedCardId.value = null;
        isDragging.value = false;
    // }
    // Убираем подсветку со всех слотов
    document.querySelectorAll('.card-slot.drag-over').forEach(el => el.classList.remove('drag-over'));
};

const handleSlotDragOver = (event: DragEvent) => {
    event.preventDefault();
    if (draggedCardId.value) {
        (event.currentTarget as HTMLElement).classList.add('drag-over');
        event.dataTransfer!.dropEffect = 'move';
    } else {
         event.dataTransfer!.dropEffect = 'none';
    }
};

const handleSlotDragLeave = (event: DragEvent) => {
    (event.currentTarget as HTMLElement).classList.remove('drag-over');
};

const handleSlotDrop = (event: DragEvent, rowIndex: number, slotIndex: number) => {
    event.preventDefault();
    (event.currentTarget as HTMLElement).classList.remove('drag-over');
    const droppedCardId = event.dataTransfer!.getData('text/plain');
    if (droppedCardId && draggedCardId.value === droppedCardId) {
        gameStore.dropCard(droppedCardId, rowIndex, slotIndex);
    }
    // Сбрасываем состояние D&D после успешного или неуспешного drop
    draggedCardId.value = null;
    isDragging.value = false;
};

// --- Touch Drag & Drop ---
let touchStartX = 0;
let touchStartY = 0;
let ghostElement: HTMLElement | null = null;
let currentDropTarget: HTMLElement | null = null;
let touchMoved = false; // Флаг, чтобы отличить тап от начала перетаскивания

const handleCardTouchStart = (event: TouchEvent, card: Card) => {
    if (!gameStore.isMyTurn || isDragging.value) return;

    const cardIndex = gameStore.cardsOnHand.findIndex(c => c.id === card.id);
    if (gameStore.gamePhase === 'placing_street_2_5' && cardIndex === gameStore.selectedCardToDiscardIndex) {
        gameStore.message = "Нельзя перетащить карту для сброса";
        return;
    }

    draggedCardId.value = card.id;
    touchMoved = false; // Сбрасываем флаг движения

    const touch = event.touches[0];
    touchStartX = touch.clientX;
    touchStartY = touch.clientY;

    // Создаем "призрак" карты ПОСЛЕ небольшой задержки, чтобы обработать тап
    // setTimeout(() => {
        // if (!touchMoved && draggedCardId.value === card.id) { // Если палец не сдвинулся и карта та же
            isDragging.value = true; // Устанавливаем флаг перетаскивания
            const cardElement = event.currentTarget as HTMLElement;
            ghostElement = cardElement.cloneNode(true) as HTMLElement;
            ghostElement.style.position = 'fixed';
            ghostElement.style.zIndex = '2000';
            ghostElement.style.opacity = '0.8';
            ghostElement.style.pointerEvents = 'none';
            ghostElement.style.width = `${cardElement.offsetWidth}px`;
            ghostElement.style.height = `${cardElement.offsetHeight}px`;
            // Центрируем призрак под пальцем
            ghostElement.style.left = `${touch.clientX - cardElement.offsetWidth / 2}px`;
            ghostElement.style.top = `${touch.clientY - cardElement.offsetHeight / 2}px`;
            document.body.appendChild(ghostElement);
            cardElement.classList.add('dragging'); // Используем CSS класс для оригинала
            document.body.style.overflow = 'hidden'; // Отключаем скролл
        // }
    // }, 100); // Задержка для обработки тапа

};

const handleCardTouchMove = (event: TouchEvent) => {
    if (!draggedCardId.value) return; // Двигаем только если начали перетаскивание

    touchMoved = true; // Палец сдвинулся

    if (!isDragging.value) { // Если флаг isDragging еще не установлен (т.е. задержка не прошла)
         // Можно установить его здесь или просто игнорировать движение до установки флага
         return;
    }
    if (!ghostElement) return; // Если призрак еще не создан

    // event.preventDefault(); // Может мешать нативному скроллу, если нужно

    const touch = event.touches[0];
    ghostElement.style.left = `${touch.clientX - ghostElement.offsetWidth / 2}px`;
    ghostElement.style.top = `${touch.clientY - ghostElement.offsetHeight / 2}px`;

    ghostElement.style.display = 'none';
    const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
    ghostElement.style.display = '';

    if (currentDropTarget && currentDropTarget !== elementBelow?.closest('.card-slot')) {
        currentDropTarget.classList.remove('drag-over');
        currentDropTarget = null;
    }

    const slotElement = elementBelow?.closest('.card-slot') as HTMLElement | null;
    if (slotElement) {
        const hasCard = slotElement.querySelector('.card');
        if (!hasCard) {
            slotElement.classList.add('drag-over');
            currentDropTarget = slotElement;
        }
    }
};

const handleCardTouchEnd = (event: TouchEvent) => {
    document.body.style.overflow = ''; // Восстанавливаем скролл

    if (ghostElement) {
        ghostElement.remove();
        ghostElement = null;
    }

    // Убираем класс dragging с оригинала
    const originalCardElement = document.querySelector(`.player-hand .card[data-id="${draggedCardId.value}"]`) as HTMLElement | null;
     if (originalCardElement) {
         originalCardElement.classList.remove('dragging');
     }

    if (currentDropTarget) {
        currentDropTarget.classList.remove('drag-over');
        const rowIndex = parseInt(currentDropTarget.dataset.rowIndex || '-1', 10);
        const slotIndex = parseInt(currentDropTarget.dataset.slotIndex || '-1', 10);

        if (draggedCardId.value && rowIndex !== -1 && slotIndex !== -1) {
            gameStore.dropCard(draggedCardId.value, rowIndex, slotIndex);
        }
    }

    // Сбрасываем состояние D&D только если это было перетаскивание
    if (isDragging.value) {
        draggedCardId.value = null;
        isDragging.value = false;
        currentDropTarget = null;
    }
};

// Обработчик тапа по карте в руке (для выбора сброса)
const handleCardTap = (cardIndex: number) => {
    // Срабатывает только если не было движения (touchMoved == false)
    // и если это не было началом перетаскивания (isDragging == false)
    if (!touchMoved && !isDragging.value && gameStore.gamePhase === 'placing_street_2_5') {
        gameStore.selectCardForDiscard(cardIndex);
    }
    // Сбрасываем флаг движения после обработки тапа/конца перетаскивания
    touchMoved = false;
};


</script>

<template>
  <div id="app-container">
    <!-- Кнопки управления приложением -->
    <button class="app-button menu-button" @click="toggleMenu">
        <span class="material-icons-outlined">menu</span>
    </button>
    <button class="app-button fullscreen-button" @click="toggleFullScreen">
        <span class="material-icons-outlined">{{ isFullscreen ? 'fullscreen_exit' : 'fullscreen' }}</span>
    </button>

    <!-- Оверлей и Меню настроек -->
    <div class="menu-overlay" :class="{ open: isMenuOpen }"></div> <!-- Убрал @click, т.к. есть listener -->
    <div class="settings-menu" :class="{ open: isMenuOpen }" ref="menuElement">
        <h2>Настройки</h2>
        <div class="setting-group">
            <label>Количество оппонентов:</label>
            <div class="opponent-options">
                <label>
                    <input type="radio" name="opponentCount" :value="1" v-model.number="selectedOpponentCount" :disabled="gameStore.isGameInProgress"> 1
                </label>
                <label>
                    <input type="radio" name="opponentCount" :value="2" v-model.number="selectedOpponentCount" :disabled="gameStore.isGameInProgress"> 2
                </label>
            </div>
        </div>
        <button class="confirm-button" @click="confirmSettings">Применить</button>
         <p v-if="gameStore.isGameInProgress" style="font-size: 0.8em; margin-top: 10px;">Изменения вступят в силу со следующей игры.</p>
    </div>

    <!-- Основной контейнер игры -->
    <div class="game-container">
      <button v-if="!gameStore.isGameInProgress" @click="handleStartGame" class="start-game-button">
          Начать Игру
      </button>

      <template v-if="gameStore.isGameInProgress">
        <div class="opponents-area">
          <OpponentBoard
            v-for="opponent in gameStore.getOpponents"
            :key="opponent.id"
            :player="opponent"
          />
        </div>

        <div class="game-message" v-if="gameStore.message">
            {{ gameStore.message }}
        </div>

        <div class="player-area">
           <PlayerBoard
             :player="gameStore.getMyPlayer"
             v-if="gameStore.getMyPlayer"
             @slot-dragover="handleSlotDragOver"
             @slot-dragleave="handleSlotDragLeave"
             @slot-drop="handleSlotDrop"
           />
        </div>

        <PlayerHand
            v-if="gameStore.cardsOnHand.length > 0 && gameStore.getMyPlayer?.isActive"
            :cards="gameStore.cardsOnHand"
            :selected-discard-index="gameStore.selectedCardToDiscardIndex"
            :is-dragging-active="isDragging"
            :dragged-card-id="draggedCardId"
            @card-dragstart="handleCardDragStart"
            @card-dragend="handleCardDragEnd"
            @card-touchstart="handleCardTouchStart"
            @card-touchmove="handleCardTouchMove"
            @card-touchend="handleCardTouchEnd"
            @card-tap="handleCardTap"
         />

        <GameControls v-if="gameStore.isMyTurn" />
      </template>
    </div>
  </div>
</template>

<style scoped>
/* Стили из main.css */
#app-container { position: relative; min-height: 100vh; }
.game-container {
  display: flex; flex-direction: column; min-height: 100vh;
  padding: 5px; padding-top: 60px; gap: 8px;
}
.opponents-area { display: flex; justify-content: space-around; gap: 8px; flex-shrink: 0; }
.game-message {
    text-align: center; padding: 5px; font-size: 0.9em; min-height: 1.2em; flex-shrink: 0;
    color: var(--text-light); background-color: rgba(0,0,0,0.2); border-radius: 4px;
}
.player-area { flex-grow: 1; display: flex; justify-content: center; align-items: center; min-height: 250px; }
</style>
