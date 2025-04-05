import { defineStore } from 'pinia';
import type { GameState, PlayerState, Card, PlayerBoard, GamePhase, RoyaltyResult, CombinationResult, ShowdownPairResult, Rank } from '@/types';
import { usePokerLogic } from '@/composables/usePokerLogic';

// --- Helper Functions ---
const createInitialPlayerState = (id: string, name: string, score: number, isDealer = false): PlayerState => ({
    id, name, score, isDealer,
    board: { top: Array(3).fill(null), middle: Array(5).fill(null), bottom: Array(5).fill(null) },
    isActive: false, fantasylandState: 'none', lastRoundScoreChange: 0,
    royalties: { top: null, middle: null, bottom: null },
    combinations: { top: null, middle: null, bottom: null },
    isFoul: false,
});

const getNextIndex = (currentIndex: number, totalPlayers: number) => (currentIndex + 1) % totalPlayers;

// --- Store Definition ---
export const useGameStore = defineStore('game', {
    state: (): GameState => ({
        players: [], deck: [], discardPile: [],
        currentStreet: 0, gamePhase: 'not_started', currentPlayerIndex: -1, dealerIndex: 0,
        cardsOnHand: [], showdownResults: null, message: "Нажмите 'Начать Игру'",
        opponentCount: 1,
    }),

    getters: {
        getPlayerById: (state) => (id: string): PlayerState | undefined => state.players.find(p => p.id === id),
        getMyPlayer: (state): PlayerState | undefined => state.players[0],
        getOpponents: (state): PlayerState[] => state.players.slice(1), // Должен работать
        getCurrentPlayer: (state): PlayerState | null => {
            return state.currentPlayerIndex >= 0 && state.currentPlayerIndex < state.players.length
                   ? state.players[state.currentPlayerIndex]
                   : null;
        },
        isMyTurn: (state): boolean => {
            const me = state.players[0];
            const current = state.getCurrentPlayer;
            const isPlacingPhase = state.gamePhase === 'placing_street_1' || state.gamePhase === 'placing_street_2_5';
            return !!me && !!current && me.id === current.id && current.isActive && isPlacingPhase;
        },
        isAiTurn: (state): boolean => {
            const current = state.getCurrentPlayer;
            return !!current && current.id !== state.players[0]?.id && current.isActive;
        },
        isGameInProgress: (state): boolean => state.gamePhase !== 'not_started',

        // --- Game Flow --- Новая логика кнопки Готово ---
        canConfirmAction: (state): boolean => {
            if (!state.isMyTurn) return false;
            const player = state.getMyPlayer;
            if (!player) return false;

            const placedCount = (player.board.top.filter(c => c !== null).length +
                                 player.board.middle.filter(c => c !== null).length +
                                 player.board.bottom.filter(c => c !== null).length);

            if (state.gamePhase === 'placing_street_1') {
                // Можно подтвердить, если размещено 5 карт
                return placedCount === 5;
            }
            if (state.gamePhase === 'placing_street_2_5') {
                // Можно подтвердить, если размещено N*2+5 карт (где N - номер улицы > 1)
                // ИЛИ проще: если в руке осталась 1 карта
                const expectedPlaced = (state.currentStreet - 1) * 2 + 5;
                return placedCount === expectedPlaced + 2; // Размещено 2 карты на текущей улице
            }
            return false;
        },
        // --- Board State --- (без изменений)
        getBoardCards: (state) => (playerId: string): PlayerBoard | null => state.players.find(p => p.id === playerId)?.board ?? null,
        isBoardFoul: (state) => (playerId: string): boolean => state.players.find(p => p.id === playerId)?.isFoul ?? false,
        getCombinedRoyaltiesPoints: (state) => (playerId: string): number => { /* ... */ }
    },

    actions: {
        // --- Setup ---
        setOpponentCount(count: 1 | 2) { /* ... */ },

        startGame(initialScore: number = 5000) {
            console.log("startGame Action Called"); // Лог
            if (this.gamePhase !== 'not_started' && this.gamePhase !== 'round_over') {
                 console.warn("Игра уже идет, перезапуск..."); // Разрешаем перезапуск
            }
            const { createDeck, shuffleDeck } = usePokerLogic();
            const playerNames = ['Вы'];
            for (let i = 1; i <= this.opponentCount; i++) { playerNames.push(`Оппонент ${i}`); }
            this.players = playerNames.map((name, index) => createInitialPlayerState(`player-${index}`, name, initialScore, index === 0));
            console.log("Игроки созданы:", JSON.parse(JSON.stringify(this.players))); // Лог
            this.deck = shuffleDeck(createDeck());
            this.discardPile = []; this.currentStreet = 0; this.currentPlayerIndex = -1; this.dealerIndex = this.players.length - 1;
            this.cardsOnHand = []; this.showdownResults = null; this.message = "Начало новой раздачи...";
            this.startNewHand();
        },

        startNewHand() { /* ... (без изменений) ... */ },

        // --- Dealing ---
        _dealCurrentPlayer() { /* ... (без изменений) ... */ },

        // --- Player Actions ---
        // Убрали selectCardForDiscard

        dropCard(cardId: string, target: { type: 'slot', rowIndex: number, slotIndex: number } | { type: 'hand' }) {
            console.log(`dropCard called: cardId=${cardId}, targetType=${target.type}`); // Лог
            const player = this.getCurrentPlayer;
            // Разрешаем ход только если это наш ход И мы в фазе размещения
            if (!player || player.id !== this.getMyPlayer?.id || !(this.gamePhase === 'placing_street_1' || this.gamePhase === 'placing_street_2_5')) {
                 console.warn("Нельзя разместить карту сейчас");
                 return;
            }

            let card: Card | null = null; let source: 'hand' | 'board' = 'hand';
            let cardIndexInHand = this.cardsOnHand.findIndex(c => c.id === cardId);
            let sourceRowIndex = -1, sourceSlotIndex = -1;

            if (cardIndexInHand !== -1) { card = this.cardsOnHand[cardIndexInHand]; source = 'hand'; }
            else {
                for (let r = 0; r < 3; r++) {
                    const rowKey = r === 0 ? 'top' : r === 1 ? 'middle' : 'bottom';
                    const slotIndex = player.board[rowKey].findIndex(c => c?.id === cardId);
                    if (slotIndex !== -1) { card = player.board[rowKey][slotIndex]; source = 'board'; sourceRowIndex = r; sourceSlotIndex = slotIndex; break; }
                }
            }
            if (!card) { console.error("Карта не найдена:", cardId); return; }

            // --- Обработка Drop на СЛОТ ---
            if (target.type === 'slot') {
                const { rowIndex, slotIndex } = target;
                // Запрещаем ставить больше карт, чем нужно на улице
                const placedOnStreet = this.cardsOnHand.length < (this.currentStreet === 1 ? 5 : 2); // Проверяем, сколько карт УЖЕ размещено на этой улице
                const maxPlaceable = this.currentStreet === 1 ? 5 : 2;
                const currentPlacedCount = (player.board.top.filter(c => c !== null).length +
                                            player.board.middle.filter(c => c !== null).length +
                                            player.board.bottom.filter(c => c !== null).length) - ((this.currentStreet - 1) * 2 + (this.currentStreet > 1 ? 5 : 0));

                if (source === 'hand' && currentPlacedCount >= maxPlaceable) {
                     this.message = `Уже размещено ${maxPlaceable} карт на этой улице`;
                     console.warn("Попытка разместить больше карт, чем разрешено на улице");
                     return;
                }


                const rowKey = rowIndex === 0 ? 'top' : rowIndex === 1 ? 'middle' : 'bottom';
                const targetRow = player.board[rowKey];
                if (slotIndex < targetRow.length && targetRow[slotIndex] === null) {
                    targetRow[slotIndex] = { ...card, originalPosition: { row: rowKey, index: slotIndex } };
                    if (source === 'hand') { this.cardsOnHand = this.cardsOnHand.filter(c => c.id !== cardId); }
                    else if (source === 'board') { const sourceRowKey = sourceRowIndex === 0 ? 'top' : sourceRowIndex === 1 ? 'middle' : 'bottom'; player.board[sourceRowKey][sourceSlotIndex] = null; }
                    console.log(`Игрок ${player.name} разместил ${card.display} в ${rowKey}[${slotIndex}]`);
                    this.updateBoardState(player.id); this.updateMessage();
                } else { this.message = "Слот занят!"; }
            }
            // --- Обработка Drop на РУКУ (возврат с доски) ---
            else if (target.type === 'hand' && source === 'board') {
                 if (this.currentStreet > 1) { this.message = "Нельзя вернуть карту на этой улице"; return; }
                const sourceRowKey = sourceRowIndex === 0 ? 'top' : sourceRowIndex === 1 ? 'middle' : 'bottom';
                player.board[sourceRowKey][sourceSlotIndex] = null;
                const { originalPosition, ...cardData } = card; this.cardsOnHand.push(cardData);
                console.log(`Игрок ${player.name} вернул ${card.display} в руку`);
                this.updateBoardState(player.id); this.updateMessage();
            }
        },

        updateBoardState(playerId: string) { /* ... (без изменений) ... */ },

        confirmAction() {
            if (!this.isMyTurn || !this.canConfirmAction) {
                console.warn("Нельзя подтвердить действие сейчас");
                return;
            }
            const player = this.getCurrentPlayer!;
            let discardedCard: Card | null = null;

            if (this.gamePhase === 'placing_street_1') {
                console.log(`Игрок ${player.name} подтвердил улицу 1.`);
            } else if (this.gamePhase === 'placing_street_2_5') {
                if (this.cardsOnHand.length === 1) { // Должна остаться 1 карта для сброса
                    discardedCard = this.cardsOnHand[0];
                    this.discardPile.push({ ...discardedCard });
                    console.log(`Игрок ${player.name} сбросил ${discardedCard.display} и подтвердил улицу ${this.currentStreet}.`);
                } else {
                    console.error("Ошибка подтверждения: неверное количество карт в руке для сброса.");
                    this.message = "Ошибка: разместите ровно 2 карты.";
                    return; // Не продолжаем, если некорректное состояние
                }
            }
            this.cardsOnHand = []; // Очищаем руку
            this.moveToNextPlayer();
        },

        // --- AI Logic ---
        _runAiTurn() { /* ... (без изменений) ... */ },
        moveToNextPlayer() { /* ... (без изменений) ... */ },
        calculateShowdown() { /* ... (без изменений) ... */ },
        _advanceGamePhase(newPhase: GamePhase) { /* ... (без изменений) ... */ },

        // Обновляем сообщение в зависимости от состояния
        updateMessage() {
            if (!this.isMyTurn) return;
            if (this.gamePhase === 'placing_street_1') {
                this.message = this.cardsOnHand.length > 0 ? `Разместите еще ${this.cardsOnHand.length} карт` : "Нажмите 'Готово'";
            } else if (this.gamePhase === 'placing_street_2_5') {
                const neededToPlace = 2 - (3 - this.cardsOnHand.length); // Сколько еще нужно разместить
                if (neededToPlace > 0) {
                    this.message = `Разместите еще ${neededToPlace} карт`;
                } else if (this.cardsOnHand.length === 1) {
                    this.message = `Нажмите 'Готово' (сброс ${this.cardsOnHand[0]?.rank})`;
                } else {
                     this.message = "Подтвердите ход"; // Если 0 карт в руке (не должно быть, но на всякий случай)
                }
            }
        }
    }
});
