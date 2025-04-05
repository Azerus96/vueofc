import { defineStore } from 'pinia';
import type { GameState, PlayerState, Card, PlayerBoard, GamePhase, RoyaltyResult, CombinationResult, ShowdownPairResult, Rank } from '@/types';
import { usePokerLogic } from '@/composables/usePokerLogic';

// --- Helper Functions ---
const createInitialPlayerState = (id: string, name: string, score: number, isDealer = false): PlayerState => ({
    id,
    name,
    score,
    board: { top: Array(3).fill(null), middle: Array(5).fill(null), bottom: Array(5).fill(null) },
    isDealer,
    isActive: false,
    fantasylandState: 'none',
    lastRoundScoreChange: 0,
    royalties: { top: null, middle: null, bottom: null },
    combinations: { top: null, middle: null, bottom: null },
    isFoul: false,
});

const getNextIndex = (currentIndex: number, totalPlayers: number) => (currentIndex + 1) % totalPlayers;

// --- Store Definition ---
export const useGameStore = defineStore('game', {
    state: (): GameState => ({
        players: [],
        deck: [],
        currentStreet: 0,
        gamePhase: 'not_started', // Начальное состояние
        currentPlayerIndex: -1,
        dealerIndex: 0,
        cardsOnHand: [],
        selectedCardToDiscardIndex: null,
        showdownResults: null,
        message: "Нажмите 'Начать Игру'", // Начальное сообщение
        opponentCount: 2, // По умолчанию 2 оппонента
    }),

    getters: {
        // --- Player Info ---
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

        // --- Game Flow ---
        canSelectForDiscard: (state): boolean => {
            return state.isMyTurn && state.gamePhase === 'placing_street_2_5' && state.selectedCardToDiscardIndex === null && state.cardsOnHand.length === 3;
        },
        canConfirmDiscard: (state): boolean => {
            return state.isMyTurn && state.gamePhase === 'placing_street_2_5' && state.selectedCardToDiscardIndex !== null && state.cardsOnHand.length === 1;
        },
        canConfirmStreet1: (state): boolean => {
            return state.isMyTurn && state.gamePhase === 'placing_street_1' && state.cardsOnHand.length === 0;
        },
        canConfirmAction: (state): boolean => {
            return state.canConfirmStreet1 || state.canConfirmDiscard;
        },

        // --- Board State ---
        getBoardCards: (state) => (playerId: string): PlayerBoard | null => {
            return state.players.find(p => p.id === playerId)?.board ?? null;
        },
        isBoardFoul: (state) => (playerId: string): boolean => {
             return state.players.find(p => p.id === playerId)?.isFoul ?? false;
        },
        getCombinedRoyaltiesPoints: (state) => (playerId: string): number => {
            const player = state.players.find(p => p.id === playerId);
            if (!player || player.isFoul) return 0;
            return (player.royalties.top?.points ?? 0) +
                   (player.royalties.middle?.points ?? 0) +
                   (player.royalties.bottom?.points ?? 0);
        }
    },

    actions: {
        // --- Setup ---
        setOpponentCount(count: 1 | 2) {
            // Изменять можно только до начала игры
            if (this.gamePhase === 'not_started') {
                this.opponentCount = count;
            } else {
                console.warn("Нельзя изменить количество оппонентов во время игры.");
            }
        },

        startGame(initialScore: number = 5000) {
            if (this.gamePhase !== 'not_started') {
                // Перезапуск игры, если она уже идет
                console.log("Перезапуск игры...");
            }
            const { createDeck, shuffleDeck } = usePokerLogic();
            const playerNames = ['Вы'];
            for (let i = 1; i <= this.opponentCount; i++) {
                playerNames.push(`Оппонент ${i}`);
            }

            this.players = playerNames.map((name, index) =>
                createInitialPlayerState(`player-${index}`, name, initialScore, index === 0)
            );
            this.deck = shuffleDeck(createDeck());
            this.currentStreet = 0;
            this.currentPlayerIndex = -1;
            this.dealerIndex = this.players.length - 1;
            this.cardsOnHand = [];
            this.selectedCardToDiscardIndex = null;
            this.showdownResults = null;
            this.message = "Начало новой раздачи...";
            console.log("Игра началась с", this.opponentCount, "оппонентами");
            this.startNewHand();
        },

        startNewHand() {
            const { createDeck, shuffleDeck } = usePokerLogic();
            console.log("Начало новой раздачи...");

            this.dealerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.players.forEach((p, index) => p.isDealer = index === this.dealerIndex);

            this.deck = shuffleDeck(createDeck());
            this.currentStreet = 1;
            this.players.forEach(p => {
                p.board = { top: Array(3).fill(null), middle: Array(5).fill(null), bottom: Array(5).fill(null) };
                p.royalties = { top: null, middle: null, bottom: null };
                p.combinations = { top: null, middle: null, bottom: null };
                p.isFoul = false;
                p.isActive = false;
                p.lastRoundScoreChange = 0;
                if (p.fantasylandState === 'earned' || p.fantasylandState === 'pending') {
                    console.warn(`Игрок ${p.id} должен начать Фентези - НЕ РЕАЛИЗОВАНО`);
                    p.fantasylandState = 'none';
                } else {
                    p.fantasylandState = 'none';
                }
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

            let cardsToDeal = 0;
            let nextPhase: GamePhase = 'placing_street_1';

            if (this.currentStreet === 1) {
                cardsToDeal = 5;
                nextPhase = 'placing_street_1';
            } else if (this.currentStreet >= 2 && this.currentStreet <= 5) {
                cardsToDeal = 3;
                nextPhase = 'placing_street_2_5';
            } else {
                this._advanceGamePhase('showdown');
                return;
            }

            const { dealtCards, remainingDeck } = dealCards(this.deck, cardsToDeal);
            this.deck = remainingDeck;
            this.cardsOnHand = dealtCards;
            this.selectedCardToDiscardIndex = null;

            console.log(`Раздача ${cardsToDeal} карт игроку ${player.name} на улице ${this.currentStreet}`);

            if (this.isAiTurn) {
                this._advanceGamePhase('ai_thinking');
            } else {
                this._advanceGamePhase(nextPhase);
                this.message = this.currentStreet === 1 ? "Разместите 5 карт" : "Выберите 1 карту для сброса, разместите 2";
            }
        },

        // --- Player Actions ---
        selectCardForDiscard(cardIndex: number) {
            if (!this.isMyTurn || this.gamePhase !== 'placing_street_2_5' || this.cardsOnHand.length !== 3) return;

            if (this.selectedCardToDiscardIndex === cardIndex) {
                this.selectedCardToDiscardIndex = null;
                this.message = "Выберите 1 карту для сброса, разместите 2";
            } else {
                this.selectedCardToDiscardIndex = cardIndex;
                this.message = "Перетащите карты для размещения";
            }
        },

        dropCard(cardId: string, rowIndex: number, slotIndex: number) {
            const player = this.getCurrentPlayer;
            if (!player || !this.isMyTurn) return;

            const cardIndexInHand = this.cardsOnHand.findIndex(c => c.id === cardId);
            if (cardIndexInHand === -1) return;

            if (this.gamePhase === 'placing_street_2_5' && cardIndexInHand === this.selectedCardToDiscardIndex) {
                this.message = "Нельзя разместить карту, выбранную для сброса";
                return;
            }

            const cardToPlace = this.cardsOnHand[cardIndexInHand];
            const rowKey = rowIndex === 0 ? 'top' : rowIndex === 1 ? 'middle' : 'bottom';
            const targetRow = player.board[rowKey];

            if (slotIndex < targetRow.length && targetRow[slotIndex] === null) {
                targetRow[slotIndex] = { ...cardToPlace };
                this.cardsOnHand = this.cardsOnHand.filter((_, i) => i !== cardIndexInHand);

                if (this.selectedCardToDiscardIndex !== null) {
                    if (cardIndexInHand < this.selectedCardToDiscardIndex) {
                        this.selectedCardToDiscardIndex--;
                    }
                    if (this.cardsOnHand.length === 1) {
                         this.selectedCardToDiscardIndex = 0; // Автовыбор последней карты на сброс
                         this.message = `Подтвердите сброс ${this.cardsOnHand[0]?.rank}?`;
                    } else if (this.cardsOnHand.length === 2) {
                         this.message = "Перетащите еще одну карту";
                    }
                } else if (this.gamePhase === 'placing_street_1') {
                     this.message = this.cardsOnHand.length > 0 ? "Перетащите следующую карту" : "Нажмите 'Готово'";
                }

                console.log(`Игрок ${player.name} разместил ${cardToPlace.display} в ${rowKey}[${slotIndex}]`);
                this.updateBoardState(player.id);
            } else {
                this.message = "Слот занят!";
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
            if (!this.isMyTurn || !this.canConfirmAction) return;
            const player = this.getCurrentPlayer!;
            console.log(`Игрок ${player.name} подтвердил ход на улице ${this.currentStreet}.`);
            this.cardsOnHand = [];
            this.selectedCardToDiscardIndex = null;
            this.moveToNextPlayer();
        },

        // --- AI Logic ---
        _runAiTurn() {
            const aiPlayer = this.getCurrentPlayer;
            if (!aiPlayer || !this.isAiTurn) return;

            console.log(`Ход ИИ: ${aiPlayer.name} на улице ${this.currentStreet}`);
            let currentHand = [...this.cardsOnHand];

            if (this.currentStreet >= 2 && currentHand.length === 3) {
                const discardIndex = Math.floor(Math.random() * 3);
                const cardToDiscard = currentHand.splice(discardIndex, 1)[0];
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
                        placed = true;
                        break;
                    }
                }
                if (!placed) console.error(`ИИ ${aiPlayer.name} не смог разместить карту ${card.display}!`);
            }

            this.updateBoardState(aiPlayer.id);
            this.cardsOnHand = [];
            // ИИ подтвердил ход, передаем дальше
            this.moveToNextPlayer();
        },

        moveToNextPlayer() {
            const currentPlayer = this.getCurrentPlayer;
            if (currentPlayer) {
                currentPlayer.isActive = false;
            }

            const nextPlayerIndex = getNextIndex(this.currentPlayerIndex, this.players.length);
            const firstPlayerIndexOfStreet = getNextIndex(this.dealerIndex, this.players.length);

            // Проверяем, закончили ли все игроки текущую улицу
            if (nextPlayerIndex === firstPlayerIndexOfStreet) {
                // Если следующий игрок - это первый игрок улицы, значит улица закончена
                this.currentStreet++;
                if (this.currentStreet > 5) {
                    this._advanceGamePhase('showdown'); // Все улицы сыграны
                } else {
                     console.log(`--- Начало улицы ${this.currentStreet} ---`);
                     this.currentPlayerIndex = nextPlayerIndex; // Устанавливаем первого игрока новой улицы
                     this._advanceGamePhase(this.currentStreet === 1 ? 'dealing_street_1' : 'dealing_street_2_5');
                }
            } else {
                 // Просто передаем ход следующему игроку на той же улице
                 this.currentPlayerIndex = nextPlayerIndex;
                 const nextPhase = this.currentStreet === 1 ? 'dealing_street_1' : 'dealing_street_2_5';
                 this._advanceGamePhase(nextPhase);
            }
        },

        // --- Showdown ---
        calculateShowdown() {
            console.log("Подсчет результатов...");
            const { compareHands } = usePokerLogic();
            const results: ShowdownPairResult[] = [];
            const numPlayers = this.players.length;

            this.players.forEach(p => this.updateBoardState(p.id));
            this.players.forEach(p => p.lastRoundScoreChange = 0);

            for (let i = 0; i < numPlayers; i++) {
                for (let j = i + 1; j < numPlayers; j++) {
                    const playerA = this.players[i];
                    const playerB = this.players[j];

                    let linePointsA = 0, linePointsB = 0;
                    let lineWinsA = 0, lineWinsB = 0;
                    const linesResult: ShowdownPairResult['lines'] = { top: 0, middle: 0, bottom: 0 };

                    if (!playerA.isFoul && !playerB.isFoul) {
                        const topCompare = compareHands(playerA.combinations.top, playerB.combinations.top);
                        const middleCompare = compareHands(playerA.combinations.middle, playerB.combinations.middle);
                        const bottomCompare = compareHands(playerA.combinations.bottom, playerB.combinations.bottom);

                        if (topCompare > 0) { linePointsA++; lineWinsA++; linesResult.top = 1; }
                        else if (topCompare < 0) { linePointsB++; lineWinsB++; linesResult.top = -1; }
                        if (middleCompare > 0) { linePointsA++; lineWinsA++; linesResult.middle = 1; }
                        else if (middleCompare < 0) { linePointsB++; lineWinsB++; linesResult.middle = -1; }
                        if (bottomCompare > 0) { linePointsA++; lineWinsA++; linesResult.bottom = 1; }
                        else if (bottomCompare < 0) { linePointsB++; lineWinsB++; linesResult.bottom = -1; }

                        if (lineWinsA === 3) linePointsA += 3;
                        if (lineWinsB === 3) linePointsB += 3;
                    } else if (playerA.isFoul && !playerB.isFoul) {
                        linePointsB = 6; lineWinsB = 3;
                        linesResult.top = -1; linesResult.middle = -1; linesResult.bottom = -1;
                    } else if (!playerA.isFoul && playerB.isFoul) {
                        linePointsA = 6; lineWinsA = 3;
                        linesResult.top = 1; linesResult.middle = 1; linesResult.bottom = 1;
                    }

                    const royaltyA = this.getCombinedRoyaltiesPoints(playerA.id);
                    const royaltyB = this.getCombinedRoyaltiesPoints(playerB.id);
                    const totalPointsA = linePointsA + royaltyA;
                    const totalPointsB = linePointsB + royaltyB;
                    const netPointsA = totalPointsA - totalPointsB;
                    const netPointsB = totalPointsB - totalPointsA;

                    // Упрощенное ограничение по стеку
                    const finalPointsA = Math.sign(netPointsA) * Math.min(Math.abs(netPointsA), playerB.score + Math.max(0, -netPointsB));
                    const finalPointsB = Math.sign(netPointsB) * Math.min(Math.abs(netPointsB), playerA.score + Math.max(0, -netPointsA));

                    playerA.lastRoundScoreChange += finalPointsA;
                    playerB.lastRoundScoreChange += finalPointsB;

                    results.push({
                        playerA_id: playerA.id, playerB_id: playerB.id,
                        pointsA: finalPointsA, pointsB: finalPointsB,
                        lines: linesResult,
                        scoopA: lineWinsA === 3 && !playerA.isFoul && !playerB.isFoul,
                        scoopB: lineWinsB === 3 && !playerA.isFoul && !playerB.isFoul,
                        royaltyA: royaltyA, royaltyB: royaltyB,
                    });
                     console.log(`Результат ${playerA.name} vs ${playerB.name}: A=${finalPointsA}, B=${finalPointsB}`);
                }
            }

            this.players.forEach(p => {
                p.score += p.lastRoundScoreChange;
                 const topHand = p.combinations.top;
                 if (!p.isFoul && topHand && ((topHand.name.includes('Пара') && RANK_VALUES[topHand.name.slice(-2,-1) as Rank] >= RANK_VALUES['Q']) || topHand.name.includes('Сет'))) {
                     console.log(`${p.name} заработал Фентези!`);
                     p.fantasylandState = 'earned';
                 }
            });

            this.showdownResults = results;
            this.message = "Раунд завершен!";
            this._advanceGamePhase('round_over');

            setTimeout(() => {
                 this.startNewHand();
            }, 5000);
        },

        // --- Управление фазами ---
        _advanceGamePhase(newPhase: GamePhase) {
            console.log(`Смена фазы: ${this.gamePhase} -> ${newPhase}`);
            this.gamePhase = newPhase;
            const player = this.getCurrentPlayer;

            switch (newPhase) {
                case 'dealing_street_1':
                case 'dealing_street_2_5':
                    if (player) {
                        player.isActive = true;
                        this.message = `Раздача для ${player.name}...`;
                        setTimeout(() => this._dealCurrentPlayer(), 300);
                    }
                    break;
                case 'ai_thinking':
                     if (player) {
                         this.message = `${player.name} думает...`;
                         setTimeout(() => this._runAiTurn(), 750 + Math.random() * 500);
                     }
                    break;
                case 'showdown':
                    this.message = "Подсчет результатов...";
                    this.players.forEach(p => p.isActive = false);
                    setTimeout(() => this.calculateShowdown(), 1000);
                    break;
                case 'round_over':
                     this.message = "Раунд завершен! Обновление счета.";
                     this.players.forEach(p => p.isActive = false);
                     break;
                case 'placing_street_1':
                     this.message = "Разместите 5 карт";
                     break;
                case 'placing_street_2_5':
                     this.message = "Выберите 1 карту для сброса, разместите 2";
                     break;
                 case 'not_started':
                     this.message = "Нажмите 'Начать Игру'";
                     break;
            }
        }
    }
});
