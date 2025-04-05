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
        currentStreet: 0,
        gamePhase: 'not_started', // Убедимся, что начальная фаза правильная
        currentPlayerIndex: -1, dealerIndex: 0,
        cardsOnHand: [], showdownResults: null, message: "Нажмите 'Начать Игру'",
        opponentCount: 1, // Дефолт 1 оппонент
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

        canConfirmAction: (state): boolean => {
            if (!state.isMyTurn) return false;
            const player = state.getMyPlayer;
            if (!player) return false;
            const placedCount = (player.board.top.filter(c => c !== null).length +
                                 player.board.middle.filter(c => c !== null).length +
                                 player.board.bottom.filter(c => c !== null).length);
            if (state.gamePhase === 'placing_street_1') {
                const basePlacedCount = 0;
                return placedCount === basePlacedCount + 5;
            }
            if (state.gamePhase === 'placing_street_2_5') {
                const basePlacedCount = (state.currentStreet - 2) * 2 + 5;
                return placedCount === basePlacedCount + 2;
            }
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
            console.log("[Store Action] startGame called. Current phase:", this.gamePhase); // <-- Лог 1
            // if (this.gamePhase !== 'not_started' && this.gamePhase !== 'round_over') {
            //      console.warn("Попытка начать игру, когда она уже идет:", this.gamePhase);
            //      // return; // Раскомментировать, если рестарт не нужен
            // }
            const { createDeck, shuffleDeck } = usePokerLogic();
            const playerNames = ['Вы'];
            for (let i = 1; i <= this.opponentCount; i++) { playerNames.push(`Оппонент ${i}`); }
            this.players = playerNames.map((name, index) => createInitialPlayerState(`player-${index}`, name, initialScore, index === 0));
            console.log("[Store Action] Players created:", this.players.length, JSON.parse(JSON.stringify(this.players))); // Лог 2
            this.deck = shuffleDeck(createDeck());
            this.discardPile = []; this.currentStreet = 0; this.currentPlayerIndex = -1; this.dealerIndex = this.players.length - 1;
            this.cardsOnHand = []; this.showdownResults = null; this.message = "Начало новой раздачи...";
            this.gamePhase = 'starting'; // Устанавливаем фазу ПЕРЕД вызовом startNewHand
            console.log("[Store Action] Phase set to 'starting'"); // Лог 2.5
            this.startNewHand(); // Переход к началу руки
        },

        startNewHand() {
            console.log("[Store Action] startNewHand called"); // <-- Лог 3
            const { createDeck, shuffleDeck } = usePokerLogic();
            this.dealerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.players.forEach((p, index) => p.isDealer = index === this.dealerIndex);
            this.deck = shuffleDeck(createDeck());
            this.discardPile = [];
            this.currentStreet = 1;
            this.players.forEach(p => {
                p.board = { top: Array(3).fill(null), middle: Array(5).fill(null), bottom: Array(5).fill(null) };
                p.royalties = { top: null, middle: null, bottom: null }; p.combinations = { top: null, middle: null, bottom: null };
                p.isFoul = false; p.isActive = false; p.lastRoundScoreChange = 0;
                if (p.fantasylandState === 'earned' || p.fantasylandState === 'pending') { p.fantasylandState = 'none'; }
                else { p.fantasylandState = 'none'; }
            });
            this.currentPlayerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.showdownResults = null;
            console.log("[Store Action] Starting street 1, first player:", this.players[this.currentPlayerIndex]?.name); // <-- Лог 4
            this._advanceGamePhase('dealing_street_1'); // Начинаем раздачу
        },

        // --- Dealing ---
        _dealCurrentPlayer() {
            console.log("[Store Action] _dealCurrentPlayer for:", this.getCurrentPlayer?.name); // <-- Лог 5
            const { dealCards } = usePokerLogic();
            const player = this.getCurrentPlayer; if (!player || !player.isActive) { console.error("Deal Error: No active player"); return; }
            let cardsToDeal = 0; let nextPhase: GamePhase = 'placing_street_1';
            if (this.currentStreet === 1) { cardsToDeal = 5; nextPhase = 'placing_street_1'; }
            else if (this.currentStreet >= 2 && this.currentStreet <= 5) { cardsToDeal = 3; nextPhase = 'placing_street_2_5'; }
            else { this._advanceGamePhase('showdown'); return; }
            const { dealtCards, remainingDeck } = dealCards(this.deck, cardsToDeal);
            this.deck = remainingDeck; this.cardsOnHand = dealtCards;
            console.log(`[Store Action] Dealt ${cardsToDeal} cards to ${player.name}`); // <-- Лог 6
            if (this.isAiTurn) { this._advanceGamePhase('ai_thinking'); }
            else { this._advanceGamePhase(nextPhase); this.message = this.currentStreet === 1 ? "Разместите 5 карт" : "Разместите 2 карты"; }
        },

        // --- Player Actions ---
        dropCard(cardId: string, target: { type: 'slot', rowIndex: number, slotIndex: number } | { type: 'hand' }) {
            console.log(`[Store Action] dropCard: cardId=${cardId}, targetType=${target.type}`); // Лог
            const player = this.getCurrentPlayer;
            if (!player || player.id !== this.getMyPlayer?.id || !(this.gamePhase === 'placing_street_1' || this.gamePhase === 'placing_street_2_5')) {
                 console.warn("Нельзя разместить карту сейчас. Phase:", this.gamePhase, "IsMyTurn:", this.isMyTurn);
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

            if (target.type === 'slot') {
                const { rowIndex, slotIndex } = target;
                const maxPlaceable = this.currentStreet === 1 ? 5 : 2;
                const basePlacedCount = (this.currentStreet - 1) * (this.currentStreet === 1 ? 0 : 2) + (this.currentStreet > 1 ? 5 : 0);
                const currentPlacedCount = (player.board.top.filter(c => c !== null).length + player.board.middle.filter(c => c !== null).length + player.board.bottom.filter(c => c !== null).length) - basePlacedCount;

                if (source === 'hand' && currentPlacedCount >= maxPlaceable) {
                     this.message = `Уже размещено ${maxPlaceable} карт на этой улице`;
                     console.warn("Попытка разместить больше карт, чем разрешено");
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
            else if (target.type === 'hand' && source === 'board') {
                 if (this.currentStreet > 1) { this.message = "Нельзя вернуть карту на этой улице"; return; }
                const sourceRowKey = sourceRowIndex === 0 ? 'top' : sourceRowIndex === 1 ? 'middle' : 'bottom';
                player.board[sourceRowKey][sourceSlotIndex] = null;
                const { originalPosition, ...cardData } = card; this.cardsOnHand.push(cardData);
                console.log(`Игрок ${player.name} вернул ${card.display} в руку`);
                this.updateBoardState(player.id); this.updateMessage();
            }
        },

        updateBoardState(playerId: string) {
            const player = this.getPlayerById(playerId);
            if (!player) return;

            const { evaluateThreeCardHand, evaluateFiveCardHand, isBoardValid } = usePokerLogic();
            const board = player.board;
            const filledCards = (row: (Card | null)[]) => row.filter(c => c !== null) as Card[];

            const topCards = filledCards(board.top);
            const middleCards = filledCards(board.middle);
            const bottomCards = filledCards(board.bottom);

            player.combinations.top = topCards.length === 3 ? evaluateThreeCardHand(topCards) : null;
            player.combinations.middle = middleCards.length === 5 ? evaluateFiveCardHand(middleCards) : null;
            player.combinations.bottom = bottomCards.length === 5 ? evaluateFiveCardHand(bottomCards) : null;

            player.royalties.top = player.combinations.top?.royalty ?? null;
            player.royalties.middle = player.combinations.middle?.royalty ?? null;
            player.royalties.bottom = player.combinations.bottom?.royalty ?? null;

            const totalPlaced = topCards.length + middleCards.length + bottomCards.length;
            if (totalPlaced === 13) {
                 player.isFoul = !isBoardValid(player.combinations);
                 if(player.isFoul) {
                     console.warn(`Игрок ${playerId} собрал МЕРТВУЮ РУКУ!`);
                     player.royalties = { top: null, middle: null, bottom: null };
                 }
            } else {
                player.isFoul = false;
            }
        },

        confirmAction() {
            console.log("[Store Action] confirmAction called. Can confirm:", this.canConfirmAction); // Лог
            if (!this.isMyTurn || !this.canConfirmAction) { console.warn("Нельзя подтвердить действие сейчас"); return; }
            const player = this.getCurrentPlayer!; let discardedCard: Card | null = null;
            if (this.gamePhase === 'placing_street_1') { console.log(`Игрок ${player.name} подтвердил улицу 1.`); }
            else if (this.gamePhase === 'placing_street_2_5') {
                if (this.cardsOnHand.length === 1) {
                    discardedCard = this.cardsOnHand[0]; this.discardPile.push({ ...discardedCard });
                    console.log(`Игрок ${player.name} сбросил ${discardedCard.display} и подтвердил улицу ${this.currentStreet}.`);
                } else { console.error("Ошибка подтверждения: неверное кол-во карт."); this.message = "Ошибка: разместите ровно 2 карты."; return; }
            }
            this.cardsOnHand = []; this.moveToNextPlayer();
        },

        // --- AI Logic ---
        _runAiTurn() {
            const aiPlayer = this.getCurrentPlayer; if (!aiPlayer || !this.isAiTurn) return;
            console.log(`[Store Action] _runAiTurn for: ${aiPlayer.name} on street ${this.currentStreet}`); // <-- Лог 7
            let currentHand = [...this.cardsOnHand]; let cardToDiscard: Card | null = null;
            if (this.currentStreet >= 2 && currentHand.length === 3) {
                const discardIndex = Math.floor(Math.random() * 3);
                cardToDiscard = currentHand.splice(discardIndex, 1)[0];
                this.discardPile.push({ ...cardToDiscard });
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
            console.log(`[Store Action] AI ${aiPlayer.name} завершил ход.`); // <-- Лог 8
            this.moveToNextPlayer();
        },

        moveToNextPlayer() {
            console.log("[Store Action] moveToNextPlayer called"); // <-- Лог 9
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
        calculateShowdown() {
            console.log("[Store Action] calculateShowdown called");
            const { compareHands } = usePokerLogic();
            const results: ShowdownPairResult[] = [];
            const numPlayers = this.players.length;
            this.players.forEach(p => this.updateBoardState(p.id));
            this.players.forEach(p => p.lastRoundScoreChange = 0);
            for (let i = 0; i < numPlayers; i++) {
                for (let j = i + 1; j < numPlayers; j++) {
                    const playerA = this.players[i]; const playerB = this.players[j];
                    let linePointsA = 0, linePointsB = 0; let lineWinsA = 0, lineWinsB = 0;
                    const linesResult: ShowdownPairResult['lines'] = { top: 0, middle: 0, bottom: 0 };
                    if (!playerA.isFoul && !playerB.isFoul) {
                        const topCompare = compareHands(playerA.combinations.top, playerB.combinations.top);
                        const middleCompare = compareHands(playerA.combinations.middle, playerB.combinations.middle);
                        const bottomCompare = compareHands(playerA.combinations.bottom, playerB.combinations.bottom);
                        if (topCompare > 0) { linePointsA++; lineWinsA++; linesResult.top = 1; } else if (topCompare < 0) { linePointsB++; lineWinsB++; linesResult.top = -1; }
                        if (middleCompare > 0) { linePointsA++; lineWinsA++; linesResult.middle = 1; } else if (middleCompare < 0) { linePointsB++; lineWinsB++; linesResult.middle = -1; }
                        if (bottomCompare > 0) { linePointsA++; lineWinsA++; linesResult.bottom = 1; } else if (bottomCompare < 0) { linePointsB++; lineWinsB++; linesResult.bottom = -1; }
                        if (lineWinsA === 3) linePointsA += 3; if (lineWinsB === 3) linePointsB += 3;
                    } else if (playerA.isFoul && !playerB.isFoul) { linePointsB = 6; lineWinsB = 3; linesResult.top = -1; linesResult.middle = -1; linesResult.bottom = -1; }
                    else if (!playerA.isFoul && playerB.isFoul) { linePointsA = 6; lineWinsA = 3; linesResult.top = 1; linesResult.middle = 1; linesResult.bottom = 1; }
                    const royaltyA = this.getCombinedRoyaltiesPoints(playerA.id); const royaltyB = this.getCombinedRoyaltiesPoints(playerB.id);
                    const totalPointsA = linePointsA + royaltyA; const totalPointsB = linePointsB + royaltyB;
                    const netPointsA = totalPointsA - totalPointsB; const netPointsB = totalPointsB - totalPointsA;
                    const finalPointsA = Math.sign(netPointsA) * Math.min(Math.abs(netPointsA), playerB.score + Math.max(0, -netPointsB));
                    const finalPointsB = Math.sign(netPointsB) * Math.min(Math.abs(netPointsB), playerA.score + Math.max(0, -netPointsA));
                    playerA.lastRoundScoreChange += finalPointsA; playerB.lastRoundScoreChange += finalPointsB;
                    results.push({ playerA_id: playerA.id, playerB_id: playerB.id, pointsA: finalPointsA, pointsB: finalPointsB, lines: linesResult, scoopA: lineWinsA === 3 && !playerA.isFoul && !playerB.isFoul, scoopB: lineWinsB === 3 && !playerA.isFoul && !playerB.isFoul, royaltyA: royaltyA, royaltyB: royaltyB, });
                    console.log(`Результат ${playerA.name} vs ${playerB.name}: A=${finalPointsA}, B=${finalPointsB}`);
                }
            }
            this.players.forEach(p => {
                p.score += p.lastRoundScoreChange;
                 const topHand = p.combinations.top;
                 if (!p.isFoul && topHand && ((topHand.name.includes('Пара') && RANK_VALUES[topHand.name.slice(-2,-1) as Rank] >= RANK_VALUES['Q']) || topHand.name.includes('Сет'))) {
                     console.log(`${p.name} заработал Фентези!`); p.fantasylandState = 'earned';
                 }
            });
            this.showdownResults = results; this.message = "Раунд завершен!"; this._advanceGamePhase('round_over');
            setTimeout(() => { this.startNewHand(); }, 5000);
        },

        // --- Управление фазами и сообщениями ---
        _advanceGamePhase(newPhase: GamePhase) {
            console.log(`[Store Action] _advanceGamePhase: ${this.gamePhase} -> ${newPhase}`); // <-- Лог 10
            this.gamePhase = newPhase;
            const player = this.getCurrentPlayer;
            switch (newPhase) {
                case 'dealing_street_1': case 'dealing_street_2_5':
                    if (player) { player.isActive = true; this.message = `Раздача для ${player.name}...`; setTimeout(() => this._dealCurrentPlayer(), 300); }
                    else { console.error("Не найден игрок для раздачи"); }
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
            if (this.gamePhase === 'placing_street_1') { this.message = this.cardsOnHand.length > 0 ? `Разместите еще ${this.cardsOnHand.length} карт` : "Нажмите 'Готово'"; }
            else if (this.gamePhase === 'placing_street_2_5') {
                const neededToPlace = 2 - (3 - this.cardsOnHand.length);
                if (neededToPlace > 0) { this.message = `Разместите еще ${neededToPlace} карт`; }
                else if (this.cardsOnHand.length === 1) { this.message = `Нажмите 'Готово' (сброс ${this.cardsOnHand[0]?.rank})`; }
                else { this.message = "Подтвердите ход"; }
            }
        }
    }
});
