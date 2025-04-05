<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useGameStore } from '@/stores/game';
import PlayerBoard from '@/components/board/PlayerBoard.vue';
import OpponentBoard from '@/components/board/OpponentBoard.vue';
import PlayerHand from '@/components/ui/PlayerHand.vue';
import GameControls from '@/components/ui/GameControls.vue';
import DiscardPile from '@/components/ui/DiscardPile.vue';
import type { Card } from '@/types';

const gameStore = useGameStore();
const isMenuOpen = ref(false);
const selectedOpponentCount = ref<1 | 2>(gameStore.opponentCount);
const draggedCardId = ref<string | null>(null);
const draggedCardSource = ref<'hand' | 'board' | null>(null);
const isDragging = ref(false);
const menuElement = ref<HTMLElement | null>(null);
const isFullscreen = ref(!!document.fullscreenElement);

// --- Управление меню ---
const toggleMenu = () => { isMenuOpen.value = !isMenuOpen.value; };
const closeMenu = () => { isMenuOpen.value = false; };
const confirmSettings = () => {
    gameStore.setOpponentCount(selectedOpponentCount.value);
    closeMenu();
    if (gameStore.isGameInProgress) { alert("Настройки количества оппонентов применятся со следующей игры."); }
};
const handleClickOutside = (event: MouseEvent) => {
    const menuButton = document.querySelector('.menu-button');
    if (isMenuOpen.value && menuElement.value && !menuElement.value.contains(event.target as Node) && (!menuButton || !menuButton.contains(event.target as Node))) {
        closeMenu();
    }
};
watch(isMenuOpen, (isOpen) => {
    if (isOpen) { setTimeout(() => document.addEventListener('click', handleClickOutside, true), 0); }
    else { document.removeEventListener('click', handleClickOutside, true); }
});

// --- Старт игры ---
const handleStartGame = () => {
    console.log("Нажата кнопка 'Начать Игру'"); // <-- Добавлен лог
    gameStore.startGame();
};

// --- Полноэкранный режим ---
const toggleFullScreen = () => {
  if (!document.fullscreenElement) { document.documentElement.requestFullscreen().catch(err => console.error(`Ошибка входа в полноэкранный режим: ${err.message} (${err.name})`)).then(() => isFullscreen.value = !!document.fullscreenElement); }
  else { if (document.exitFullscreen) { document.exitFullscreen().then(() => isFullscreen.value = false); } }
};
document.addEventListener('fullscreenchange', () => { isFullscreen.value = !!document.fullscreenElement; });

// --- Логика Drag & Drop ---
const handleCardDragStart = (event: DragEvent, card: Card, source: 'hand' | 'board') => {
    if (!gameStore.isMyTurn) return;
    if (source === 'board' && gameStore.currentStreet > 1) { event.preventDefault(); gameStore.message = "Нельзя вернуть карту на этой улице"; return; }
    draggedCardId.value = card.id; draggedCardSource.value = source; isDragging.value = true;
    event.dataTransfer!.setData('text/plain', card.id); event.dataTransfer!.effectAllowed = 'move';
};
const handleCardDragEnd = () => {
    draggedCardId.value = null; draggedCardSource.value = null; isDragging.value = false;
    document.querySelectorAll('.card-slot.drag-over, .player-hand.drag-over').forEach(el => el.classList.remove('drag-over'));
};
const handleSlotDragOver = (event: DragEvent) => {
    event.preventDefault();
    if (draggedCardId.value) { (event.currentTarget as HTMLElement).classList.add('drag-over'); event.dataTransfer!.dropEffect = 'move'; }
    else { event.dataTransfer!.dropEffect = 'none'; }
};
const handleSlotDragLeave = (event: DragEvent) => { (event.currentTarget as HTMLElement).classList.remove('drag-over'); };
const handleSlotDrop = (event: DragEvent, rowIndex: number, slotIndex: number) => {
    event.preventDefault(); (event.currentTarget as HTMLElement).classList.remove('drag-over');
    const droppedCardId = event.dataTransfer!.getData('text/plain');
    if (droppedCardId && draggedCardId.value === droppedCardId) {
        gameStore.dropCard(droppedCardId, { type: 'slot', rowIndex, slotIndex });
    }
    draggedCardId.value = null; draggedCardSource.value = null; isDragging.value = false;
};
const handleHandDragOver = (event: DragEvent) => {
    event.preventDefault();
    if (draggedCardSource.value === 'board' && gameStore.currentStreet === 1) { (event.currentTarget as HTMLElement).classList.add('drag-over'); event.dataTransfer!.dropEffect = 'move'; }
    else { event.dataTransfer!.dropEffect = 'none'; }
};
const handleHandDragLeave = (event: DragEvent) => { (event.currentTarget as HTMLElement).classList.remove('drag-over'); };
const handleHandDrop = (event: DragEvent) => {
    event.preventDefault(); (event.currentTarget as HTMLElement).classList.remove('drag-over');
    const droppedCardId = event.dataTransfer!.getData('text/plain');
    if (droppedCardId && draggedCardId.value === droppedCardId && draggedCardSource.value === 'board' && gameStore.currentStreet === 1) {
        gameStore.dropCard(droppedCardId, { type: 'hand' });
    }
    draggedCardId.value = null; draggedCardSource.value = null; isDragging.value = false;
};

// --- Touch Drag & Drop --- (Без изменений)
let touchStartX = 0; let touchStartY = 0; let ghostElement: HTMLElement | null = null;
let currentDropTarget: HTMLElement | null = null; let touchMoved = false;
const handleCardTouchStart = (event: TouchEvent, card: Card) => { /* ... */ };
const handleCardTouchMove = (event: TouchEvent) => { /* ... */ };
const handleCardTouchEnd = (event: TouchEvent) => { /* ... */ };

const gameContainerClass = computed(() => ({ 'game-container': true, 'one-opponent': gameStore.opponentCount === 1, }));

</script>

<template>
  <div id="app-container">
    <button class="app-button menu-button" @click="toggleMenu"><span class="material-icons-outlined">menu</span></button>
    <button class="app-button fullscreen-button" @click="toggleFullScreen"><span class="material-icons-outlined">{{ isFullscreen ? 'fullscreen_exit' : 'fullscreen' }}</span></button>

    <div class="menu-overlay" :class="{ open: isMenuOpen }"></div>
    <div class="settings-menu" :class="{ open: isMenuOpen }" ref="menuElement">
        <h2>Настройки</h2>
        <div class="setting-group">
            <label>Количество оппонентов:</label>
            <div class="opponent-options">
                <label><input type="radio" name="opponentCount" :value="1" v-model.number="selectedOpponentCount" :disabled="gameStore.isGameInProgress"> 1</label>
                <label><input type="radio" name="opponentCount" :value="2" v-model.number="selectedOpponentCount" :disabled="gameStore.isGameInProgress"> 2</label>
            </div>
        </div>
        <button class="confirm-button" @click="confirmSettings">Применить</button>
         <p v-if="gameStore.isGameInProgress" style="font-size: 0.8em; margin-top: 10px;">Изменения вступят в силу со следующей игры.</p>
    </div>

    <div :class="gameContainerClass">
      <button v-if="!gameStore.isGameInProgress" @click="handleStartGame" class="start-game-button">
          Начать Игру
      </button>

      <template v-if="gameStore.isGameInProgress">
        <div class="opponents-area" :class="{ 'center-opponent': gameStore.opponentCount === 1 }">
          <OpponentBoard v-for="opponent in gameStore.getOpponents" :key="opponent.id" :player="opponent" />
        </div>

        <div class="game-message" v-if="gameStore.message">{{ gameStore.message }}</div>

        <div class="player-section">
            <DiscardPile :cards="gameStore.discardPile" />
            <div class="player-area">
               <PlayerBoard :player="gameStore.getMyPlayer" v-if="gameStore.getMyPlayer"
                 @slot-dragover="handleSlotDragOver" @slot-dragleave="handleSlotDragLeave" @slot-drop="handleSlotDrop"
                 @card-dragstart="(event: DragEvent, card: Card) => handleCardDragStart(event, card, 'board')"
                 @card-dragend="handleCardDragEnd"
                 />
            </div>
            <div class="discard-placeholder"></div>
        </div>

        <PlayerHand
            v-if="gameStore.cardsOnHand.length > 0 && gameStore.getMyPlayer?.isActive"
            :cards="gameStore.cardsOnHand"
            :is-dragging-active="isDragging"
            :dragged-card-id="draggedCardId"
            @card-dragstart="(event: DragEvent, card: Card) => handleCardDragStart(event, card, 'hand')"
            @card-dragend="handleCardDragEnd"
            @card-touchstart="(event: TouchEvent, card: Card) => handleCardTouchStart(event, card)"
            @card-touchmove="handleCardTouchMove"
            @card-touchend="handleCardTouchEnd"
            @zone-dragover="handleHandDragOver"
            @zone-dragleave="handleHandDragLeave"
            @zone-drop="handleHandDrop"
         />

        <GameControls v-if="gameStore.isMyTurn" />
      </template>
    </div>
  </div>
</template>

<style scoped>
/* Стили из main.css */
#app-container { position: relative; min-height: 100vh; }
.game-container { display: flex; flex-direction: column; min-height: 100vh; padding: 5px; padding-top: 50px; gap: 5px; }
.game-container.one-opponent .opponents-area { justify-content: center; }
.game-container.one-opponent .opponent-board { width: 65%; }
.game-container.one-opponent .player-board { max-width: 380px; }
.opponents-area { display: flex; justify-content: space-around; gap: 4px; flex-shrink: 0; }
.game-message { text-align: center; padding: 3px; font-size: 0.85em; min-height: 1.1em; flex-shrink: 0; color: var(--text-light); background-color: rgba(0,0,0,0.2); border-radius: 4px; }
.player-section { display: flex; align-items: flex-start; gap: 5px; flex-grow: 1; }
.player-area { flex-grow: 1; display: flex; justify-content: center; align-items: center; }
.discard-placeholder, .discard-pile { width: 55px; flex-shrink: 0; }
</style>
