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
        players: [], deck: [], discardPile: [], // Инициализация сброса
        currentStreet: 0, gamePhase: 'not_started', currentPlayerIndex: -1, dealerIndex: 0,
        cardsOnHand: [], showdownResults: null, message: "Нажмите 'Начать Игру'",
        opponentCount: 1, // По умолчанию 1 оппонент
    }),

    getters: {
        getPlayerById: (state) => (id: string): PlayerState | undefined => state.players.find(p => p.id === id),
        getMyPlayer: (state): PlayerState | undefined => state.players[0],
        getOpponents: (state): PlayerState[] => state.players.slice(1),
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
            if (state.gamePhase === 'placing_street_1') {
                // Можно подтвердить, если в руке 0 карт
                return state.cardsOnHand.length === 0;
            }
            if (state.gamePhase === 'placing_street_2_5') {
                // Можно подтвердить, если в руке осталась 1 карта (значит 2 размещены)
                return state.cardsOnHand.length === 1;
            }
            return false;
        },

        // --- Board State ---
        getBoardCards: (state) => (playerId: string): PlayerBoard | null => state.players.find(p => p.id === playerId)?.board ?? null,
        isBoardFoul: (state) => (playerId: string): boolean => state.players.find(p => p.id === playerId)?.isFoul ?? false,
        getCombinedRoyaltiesPoints: (state) => (playerId: string): number => {
            const player = state.players.find(p => p.id === playerId);
            if (!player || player.isFoul) return 0;
            return (player.royalties.top?.points ?? 0) + (player.royalties.middle?.points ?? 0) + (player.royalties.bottom?.points ?? 0);
        }
    },

    actions: {
        // --- Setup ---
        setOpponentCount(count: 1 | 2) {
            if (this.gamePhase === 'not_started') { this.opponentCount = count; }
            else { console.warn("Нельзя изменить количество оппонентов во время игры."); }
        },

        startGame(initialScore: number = 5000) {
            if (this.gamePhase !== 'not_started') { console.log("Перезапуск игры..."); }
            const { createDeck, shuffleDeck } = usePokerLogic();
            const playerNames = ['Вы'];
            for (let i = 1; i <= this.opponentCount; i++) { playerNames.push(`Оппонент ${i}`); }
            this.players = playerNames.map((name, index) => createInitialPlayerState(`player-${index}`, name, initialScore, index === 0));
            this.deck = shuffleDeck(createDeck());
            this.discardPile = []; // Очищаем сброс
            this.currentStreet = 0; this.currentPlayerIndex = -1; this.dealerIndex = this.players.length - 1;
            this.cardsOnHand = []; this.showdownResults = null; this.message = "Начало новой раздачи...";
            console.log("Игра началась с", this.opponentCount, "оппонентами");
            this.startNewHand();
        },

        startNewHand() {
            const { createDeck, shuffleDeck } = usePokerLogic();
            console.log("Начало новой раздачи...");
            this.dealerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.players.forEach((p, index) => p.isDealer = index === this.dealerIndex);
            this.deck = shuffleDeck(createDeck());
            this.discardPile = []; // Очищаем сброс в начале каждой руки
            this.currentStreet = 1;
            this.players.forEach(p => {
                p.board = { top: Array(3).fill(null), middle: Array(5).fill(null), bottom: Array(5).fill(null) };
                p.royalties = { top: null, middle: null, bottom: null }; p.combinations = { top: null, middle: null, bottom: null };
                p.isFoul = false; p.isActive = false; p.lastRoundScoreChange = 0;
                if (p.fantasylandState === 'earned' || p.fantasylandState === 'pending') {
                    console.warn(`Игрок ${p.id} должен начать Фентези - НЕ РЕАЛИЗОВАНО`); p.fantasylandState = 'none';
                } else { p.fantasylandState = 'none'; }
            });
            this.currentPlayerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.showdownResults = null;
            this._advanceGamePhase('dealing_street_1');
        },

        // --- Dealing ---
        _dealCurrentPlayer() {
            const { dealCards } = usePokerLogic();
            const player = this.getCurrentPlayer;
            if (!player || !player.isActive) return;
            let cardsToDeal = 0; let nextPhase: GamePhase = 'placing_street_1';
            if (this.currentStreet === 1) { cardsToDeal = 5; nextPhase = 'placing_street_1'; }
            else if (this.currentStreet >= 2 && this.currentStreet <= 5) { cardsToDeal = 3; nextPhase = 'placing_street_2_5'; }
            else { this._advanceGamePhase('showdown'); return; }
            const { dealtCards, remainingDeck } = dealCards(this.deck, cardsToDeal);
            this.deck = remainingDeck; this.cardsOnHand = dealtCards;
            console.log(`Раздача ${cardsToDeal} карт игроку ${player.name} на улице ${this.currentStreet}`);
            if (this.isAiTurn) { this._advanceGamePhase('ai_thinking'); }
            else { this._advanceGamePhase(nextPhase); this.message = this.currentStreet === 1 ? "Разместите 5 карт" : "Разместите 2 карты"; }
        },

        // --- Player Actions ---
        // Размещение карты через Drag & Drop
        dropCard(cardId: string, target: { type: 'slot', rowIndex: number, slotIndex: number } | { type: 'hand' }) {
            const player = this.getCurrentPlayer;
            if (!player || !this.isMyTurn) return;

            // Найти карту (либо в руке, либо на доске)
            let card: Card | null = null;
            let source: 'hand' | 'board' = 'hand';
            let cardIndexInHand = this.cardsOnHand.findIndex(c => c.id === cardId);
            let sourceRowIndex = -1, sourceSlotIndex = -1;

            if (cardIndexInHand !== -1) {
                card = this.cardsOnHand[cardIndexInHand];
                source = 'hand';
            } else {
                // Ищем на доске
                for (let r = 0; r < 3; r++) {
                    const rowKey = r === 0 ? 'top' : r === 1 ? 'middle' : 'bottom';
                    const slotIndex = player.board[rowKey].findIndex(c => c?.id === cardId);
                    if (slotIndex !== -1) {
                        card = player.board[rowKey][slotIndex];
                        source = 'board';
                        sourceRowIndex = r;
                        sourceSlotIndex = slotIndex;
                        break;
                    }
                }
            }

            if (!card) { console.error("Перетаскиваемая карта не найдена:", cardId); return; }

            // --- Обработка Drop на СЛОТ ---
            if (target.type === 'slot') {
                const { rowIndex, slotIndex } = target;
                const rowKey = rowIndex === 0 ? 'top' : rowIndex === 1 ? 'middle' : 'bottom';
                const targetRow = player.board[rowKey];

                if (slotIndex < targetRow.length && targetRow[slotIndex] === null) {
                    // Помещаем карту
                    targetRow[slotIndex] = { ...card, originalPosition: { row: rowKey, index: slotIndex } }; // Сохраняем позицию на доске

                    // Удаляем из источника
                    if (source === 'hand') {
                        this.cardsOnHand = this.cardsOnHand.filter(c => c.id !== cardId);
                    } else if (source === 'board') {
                        const sourceRowKey = sourceRowIndex === 0 ? 'top' : sourceRowIndex === 1 ? 'middle' : 'bottom';
                        player.board[sourceRowKey][sourceSlotIndex] = null;
                    }

                    console.log(`Игрок ${player.name} разместил ${card.display} в ${rowKey}[${slotIndex}]`);
                    this.updateBoardState(player.id);
                    this.updateMessage(); // Обновляем сообщение после хода
                } else {
                    this.message = "Слот занят!";
                }
            }
            // --- Обработка Drop на РУКУ (возврат с доски) ---
            else if (target.type === 'hand' && source === 'board') {
                 // Нельзя вернуть карту на улицах 2-5 (по правилам)
                 if (this.currentStreet > 1) {
                     this.message = "Нельзя вернуть карту на этой улице";
                     return;
                 }
                // Удаляем с доски
                const sourceRowKey = sourceRowIndex === 0 ? 'top' : sourceRowIndex === 1 ? 'middle' : 'bottom';
                player.board[sourceRowKey][sourceSlotIndex] = null;
                // Возвращаем в руку (без originalPosition, т.к. она теперь в руке)
                const { originalPosition, ...cardData } = card;
                this.cardsOnHand.push(cardData);

                console.log(`Игрок ${player.name} вернул ${card.display} в руку`);
                this.updateBoardState(player.id);
                this.updateMessage();
            }
        },

        updateBoardState(playerId: string) {
            const player = this.getPlayerById(playerId); if (!player) return;
            const { evaluateThreeCardHand, evaluateFiveCardHand, isBoardValid } = usePokerLogic();
            const board = player.board;
            const filledCards = (row: (Card | null)[]) => row.filter(c => c !== null) as Card[];
            const topCards = filledCards(board.top); const middleCards = filledCards(board.middle); const bottomCards = filledCards(board.bottom);
            player.combinations.top = topCards.length === 3 ? evaluateThreeCardHand(topCards) : null;
            player.combinations.middle = middleCards.length === 5 ? evaluateFiveCardHand(middleCards) : null;
            player.combinations.bottom = bottomCards.length === 5 ? evaluateFiveCardHand(bottomCards) : null;
            player.royalties.top = player.combinations.top?.royalty ?? null;
            player.royalties.middle = player.combinations.middle?.royalty ?? null;
            player.royalties.bottom = player.combinations.bottom?.royalty ?? null;
            const totalPlaced = topCards.length + middleCards.length + bottomCards.length;
            if (totalPlaced === 13) {
                 player.isFoul = !isBoardValid(player.combinations);
                 if(player.isFoul) { console.warn(`Игрок ${playerId} собрал МЕРТВУЮ РУКУ!`); player.royalties = { top: null, middle: null, bottom: null }; }
            } else { player.isFoul = false; }
        },

        // Подтверждение хода (новая логика)
        confirmAction() {
            if (!this.isMyTurn || !this.canConfirmAction) return;
            const player = this.getCurrentPlayer!;
            let discardedCard: Card | null = null;

            if (this.gamePhase === 'placing_street_1') {
                console.log(`Игрок ${player.name} подтвердил улицу 1.`);
            } else if (this.gamePhase === 'placing_street_2_5') {
                if (this.cardsOnHand.length === 1) {
                    discardedCard = this.cardsOnHand[0];
                    this.discardPile.push({ ...discardedCard }); // Добавляем копию в сброс
                    console.log(`Игрок ${player.name} сбросил ${discardedCard.display} и подтвердил улицу ${this.currentStreet}.`);
                } else {
                    console.error("Ошибка подтверждения: неверное количество карт в руке.");
                    return;
                }
            }
            this.cardsOnHand = []; // Очищаем руку
            this.moveToNextPlayer();
        },

        // --- AI Logic ---
        _runAiTurn() {
            const aiPlayer = this.getCurrentPlayer; if (!aiPlayer || !this.isAiTurn) return;
            console.log(`Ход ИИ: ${aiPlayer.name} на улице ${this.currentStreet}`);
            let currentHand = [...this.cardsOnHand]; let cardToDiscard: Card | null = null;
            if (this.currentStreet >= 2 && currentHand.length === 3) {
                const discardIndex = Math.floor(Math.random() * 3);
                cardToDiscard = currentHand.splice(discardIndex, 1)[0];
                this.discardPile.push({ ...cardToDiscard }); // ИИ тоже сбрасывает в общую кучу
                console.log(`ИИ ${aiPlayer.name} сбрасывает ${cardToDiscard.display}`);
            }
            const placeOrder: { row: keyof PlayerBoard, index: number }[] = [
                { row: 'bottom', index: 0 }, { row: 'bottom', index: 1 }, { row: 'bottom', index: 2 }, { row: 'bottom', index: 3 }, { row: 'bottom', index: 4 },
                { row: 'middle', index: 0 }, { row: 'middle', index: 1 }, { row: 'middle', index: 2 }, { row: 'middle', index: 3 }, { row: 'middle', index: 4 },
                { row: 'top', index: 0 }, { row: 'top', index: 1 }, { row: 'top', index: 2 },
            ];
            for (const card of currentHand) {
                let placed = false;
                for (const target of placeOrder) {
                    if (aiPlayer.board[target.row][target.index] === null) {
                        aiPlayer.board[target.row][target.index] = { ...card };
                        console.log(`ИИ ${aiPlayer.name} разместил ${card.display} в ${target.row}[${target.index}]`);
                        placed = true; break;
                    }
                }
                if (!placed) console.error(`ИИ ${aiPlayer.name} не смог разместить карту ${card.display}!`);
            }
            this.updateBoardState(aiPlayer.id); this.cardsOnHand = [];
            // ИИ подтвердил ход, передаем дальше
            this.moveToNextPlayer();
        },

        moveToNextPlayer() {
            const currentPlayer = this.getCurrentPlayer; if (currentPlayer) { currentPlayer.isActive = false; }
            const nextPlayerIndex = getNextIndex(this.currentPlayerIndex, this.players.length);
            const firstPlayerIndexOfStreet = getNextIndex(this.dealerIndex, this.players.length);
            if (nextPlayerIndex === firstPlayerIndexOfStreet) {
                this.currentStreet++;
                if (this.currentStreet > 5) { this._advanceGamePhase('showdown'); }
                else { console.log(`--- Начало улицы ${this.currentStreet} ---`); this.currentPlayerIndex = nextPlayerIndex; this._advanceGamePhase('dealing_street_2_5'); }
            } else { this.currentPlayerIndex = nextPlayerIndex; const nextPhase = this.currentStreet === 1 ? 'dealing_street_1' : 'dealing_street_2_5'; this._advanceGamePhase(nextPhase); }
        },

        // --- Showdown ---
        calculateShowdown() { /* ... (код без изменений) ... */ },

        // --- Управление фазами и сообщениями ---
        _advanceGamePhase(newPhase: GamePhase) { /* ... (код без изменений, но сообщения обновлены) ... */ },
        updateMessage() { // Новая функция для обновления сообщения после хода игрока
            if (!this.isMyTurn) return;
            if (this.gamePhase === 'placing_street_1') {
                this.message = this.cardsOnHand.length > 0 ? "Перетащите следующую карту" : "Нажмите 'Готово'";
            } else if (this.gamePhase === 'placing_street_2_5') {
                this.message = this.cardsOnHand.length > 1 ? "Перетащите еще одну карту" : (this.cardsOnHand.length === 1 ? `Нажмите 'Готово' (сброс ${this.cardsOnHand[0]?.rank})` : "Ошибка!");
            }
        }
    }
});
