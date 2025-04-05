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
        currentStreet: 0, gamePhase: 'not_started', // Убедимся, что начальная фаза правильная
        currentPlayerIndex: -1, dealerIndex: 0,
        cardsOnHand: [], showdownResults: null, message: "Нажмите 'Начать Игру'",
        opponentCount: 1, // Дефолт 1 оппонент
    }),

    getters: {
        // ... (геттеры без изменений) ...
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
        canConfirmAction: (state): boolean => {
            if (!state.isMyTurn) return false;
            if (state.gamePhase === 'placing_street_1') { return state.cardsOnHand.length === 0; }
            if (state.gamePhase === 'placing_street_2_5') { return state.cardsOnHand.length === 1; }
            return false;
        },
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
            console.log("Вызов startGame, текущая фаза:", this.gamePhase); // <-- Лог 1
            // Убрал проверку !='not_started', чтобы перезапуск работал
            // if (this.gamePhase !== 'not_started') {
            //     console.log("Перезапуск игры...");
            // }
            const { createDeck, shuffleDeck } = usePokerLogic();
            const playerNames = ['Вы'];
            for (let i = 1; i <= this.opponentCount; i++) { playerNames.push(`Оппонент ${i}`); }
            this.players = playerNames.map((name, index) => createInitialPlayerState(`player-${index}`, name, initialScore, index === 0));
            console.log("Игроки созданы:", this.players.length); // <-- Лог 2
            this.deck = shuffleDeck(createDeck());
            this.discardPile = [];
            this.currentStreet = 0; this.currentPlayerIndex = -1; this.dealerIndex = this.players.length - 1;
            this.cardsOnHand = []; this.showdownResults = null; this.message = "Начало новой раздачи...";
            console.log("Игра началась с", this.opponentCount, "оппонентами");
            this.startNewHand(); // Переход к началу руки
        },

        startNewHand() {
            console.log("Вызов startNewHand"); // <-- Лог 3
            const { createDeck, shuffleDeck } = usePokerLogic();
            this.dealerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.players.forEach((p, index) => p.isDealer = index === this.dealerIndex);
            this.deck = shuffleDeck(createDeck());
            this.discardPile = [];
            this.currentStreet = 1;
            this.players.forEach(p => { /* ... сброс состояния ... */ });
            this.currentPlayerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.showdownResults = null;
            console.log("Начало улицы 1, первый ход:", this.players[this.currentPlayerIndex]?.name); // <-- Лог 4
            this._advanceGamePhase('dealing_street_1'); // Начинаем раздачу
        },

        // --- Dealing ---
        _dealCurrentPlayer() {
            console.log("Вызов _dealCurrentPlayer для", this.getCurrentPlayer?.name); // <-- Лог 5
            const { dealCards } = usePokerLogic();
            const player = this.getCurrentPlayer; if (!player || !player.isActive) return;
            let cardsToDeal = 0; let nextPhase: GamePhase = 'placing_street_1';
            if (this.currentStreet === 1) { cardsToDeal = 5; nextPhase = 'placing_street_1'; }
            else if (this.currentStreet >= 2 && this.currentStreet <= 5) { cardsToDeal = 3; nextPhase = 'placing_street_2_5'; }
            else { this._advanceGamePhase('showdown'); return; }
            const { dealtCards, remainingDeck } = dealCards(this.deck, cardsToDeal);
            this.deck = remainingDeck; this.cardsOnHand = dealtCards;
            console.log(`Раздано ${cardsToDeal} карт игроку ${player.name}`); // <-- Лог 6
            if (this.isAiTurn) { this._advanceGamePhase('ai_thinking'); }
            else { this._advanceGamePhase(nextPhase); this.message = this.currentStreet === 1 ? "Разместите 5 карт" : "Разместите 2 карты"; }
        },

        // --- Player Actions ---
        dropCard(cardId: string, target: { type: 'slot', rowIndex: number, slotIndex: number } | { type: 'hand' }) {
            const player = this.getCurrentPlayer; if (!player || !this.isMyTurn) return;
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

            if (target.type === 'slot') {
                const { rowIndex, slotIndex } = target;
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
            else if (target.type === 'hand' && source === 'board') {
                 if (this.currentStreet > 1) { this.message = "Нельзя вернуть карту на этой улице"; return; }
                const sourceRowKey = sourceRowIndex === 0 ? 'top' : sourceRowIndex === 1 ? 'middle' : 'bottom';
                player.board[sourceRowKey][sourceSlotIndex] = null;
                const { originalPosition, ...cardData } = card; this.cardsOnHand.push(cardData);
                console.log(`Игрок ${player.name} вернул ${card.display} в руку`);
                this.updateBoardState(player.id); this.updateMessage();
            }
        },

        updateBoardState(playerId: string) { /* ... (код без изменений) ... */ },

        confirmAction() {
            if (!this.isMyTurn || !this.canConfirmAction) return;
            const player = this.getCurrentPlayer!;
            let discardedCard: Card | null = null;
            if (this.gamePhase === 'placing_street_1') { console.log(`Игрок ${player.name} подтвердил улицу 1.`); }
            else if (this.gamePhase === 'placing_street_2_5') {
                if (this.cardsOnHand.length === 1) {
                    discardedCard = this.cardsOnHand[0];
                    this.discardPile.push({ ...discardedCard });
                    console.log(`Игрок ${player.name} сбросил ${discardedCard.display} и подтвердил улицу ${this.currentStreet}.`);
                } else { console.error("Ошибка подтверждения: неверное кол-во карт."); return; }
            }
            this.cardsOnHand = []; this.moveToNextPlayer();
        },

        // --- AI Logic ---
        _runAiTurn() {
            const aiPlayer = this.getCurrentPlayer; if (!aiPlayer || !this.isAiTurn) return;
            console.log(`Ход ИИ: ${aiPlayer.name} на улице ${this.currentStreet}`); // <-- Лог 7
            let currentHand = [...this.cardsOnHand]; let cardToDiscard: Card | null = null;
            if (this.currentStreet >= 2 && currentHand.length === 3) {
                const discardIndex = Math.floor(Math.random() * 3);
                cardToDiscard = currentHand.splice(discardIndex, 1)[0];
                this.discardPile.push({ ...cardToDiscard });
                console.log(`ИИ ${aiPlayer.name} сбрасывает ${cardToDiscard.display}`);
            }
            const placeOrder: { row: keyof PlayerBoard, index: number }[] = [ /* ... */ ];
            for (const card of currentHand) { /* ... */ } // Логика размещения ИИ без изменений
            this.updateBoardState(aiPlayer.id); this.cardsOnHand = [];
            console.log(`ИИ ${aiPlayer.name} завершил ход.`); // <-- Лог 8
            this.moveToNextPlayer();
        },

        moveToNextPlayer() {
            console.log("Вызов moveToNextPlayer"); // <-- Лог 9
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
        _advanceGamePhase(newPhase: GamePhase) {
            console.log(`Смена фазы: ${this.gamePhase} -> ${newPhase}`); // <-- Лог 10
            this.gamePhase = newPhase;
            const player = this.getCurrentPlayer;
            switch (newPhase) {
                case 'dealing_street_1': case 'dealing_street_2_5':
                    if (player) { player.isActive = true; this.message = `Раздача для ${player.name}...`; setTimeout(() => this._dealCurrentPlayer(), 300); }
                    else { console.error("Не найден игрок для раздачи"); } // <-- Добавлена проверка
                    break;
                case 'ai_thinking': if (player) { this.message = `${player.name} думает...`; setTimeout(() => this._runAiTurn(), 750 + Math.random() * 500); } break;
                case 'showdown': this.message = "Подсчет результатов..."; this.players.forEach(p => p.isActive = false); setTimeout(() => this.calculateShowdown(), 1000); break;
                case 'round_over': this.message = "Раунд завершен! Обновление счета."; this.players.forEach(p => p.isActive = false); break;
                case 'placing_street_1': this.message = "Разместите 5 карт"; break;
                case 'placing_street_2_5': this.message = "Разместите 2 карты"; break;
                case 'not_started': this.message = "Нажмите 'Начать Игру'"; break;
            }
        },
        updateMessage() {
            if (!this.isMyTurn) return;
            if (this.gamePhase === 'placing_street_1') { this.message = this.cardsOnHand.length > 0 ? "Перетащите следующую карту" : "Нажмите 'Готово'"; }
            else if (this.gamePhase === 'placing_street_2_5') { this.message = this.cardsOnHand.length > 1 ? "Перетащите еще одну карту" : (this.cardsOnHand.length === 1 ? `Нажмите 'Готово' (сброс ${this.cardsOnHand[0]?.rank})` : "Ошибка!"); }
        }
    }
});
