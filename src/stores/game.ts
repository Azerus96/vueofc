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
        gamePhase: 'waiting',
        currentPlayerIndex: -1,
        dealerIndex: 0,
        cardsOnHand: [],
        selectedCardToDiscardIndex: null,
        selectedCardToPlaceIndex: null,
        showdownResults: null,
        message: null,
    }),

    getters: {
        // --- Player Info ---
        getPlayerById: (state) => (id: string): PlayerState | undefined => state.players.find(p => p.id === id),
        getMyPlayer: (state): PlayerState | undefined => state.players[0], // Игрок всегда первый
        getOpponents: (state): PlayerState[] => state.players.slice(1),
        getCurrentPlayer: (state): PlayerState | null => {
            return state.currentPlayerIndex >= 0 && state.currentPlayerIndex < state.players.length
                   ? state.players[state.currentPlayerIndex]
                   : null;
        },
        isMyTurn: (state): boolean => {
            const me = state.players[0];
            const current = state.getCurrentPlayer;
            // Проверяем фазу игры - ход игрока только в фазах размещения
            const isPlacingPhase = state.gamePhase === 'placing_street_1' || state.gamePhase === 'placing_street_2_5';
            return !!me && !!current && me.id === current.id && current.isActive && isPlacingPhase;
        },
        isAiTurn: (state): boolean => {
            const current = state.getCurrentPlayer;
            return !!current && current.id !== state.players[0]?.id && current.isActive;
        },

        // --- Game Flow ---
        canPlaceCard: (state): boolean => {
            return state.selectedCardToPlaceIndex !== null &&
                   (state.gamePhase === 'placing_street_1' || state.gamePhase === 'placing_street_2_5');
        },
        canSelectForDiscard: (state): boolean => {
            return state.gamePhase === 'placing_street_2_5' && state.selectedCardToDiscardIndex === null && state.cardsOnHand.length === 3;
        },
        canSelectForPlacement: (state): boolean => {
             return state.gamePhase === 'placing_street_1' ||
                    (state.gamePhase === 'placing_street_2_5' && state.selectedCardToDiscardIndex !== null);
        },
        canConfirmDiscard: (state): boolean => {
            if (state.gamePhase !== 'placing_street_2_5' || state.selectedCardToDiscardIndex === null) return false;
            return state.cardsOnHand.length === 1;
        },
        canConfirmStreet1: (state): boolean => {
            if (state.gamePhase !== 'placing_street_1') return false;
            return state.cardsOnHand.length === 0;
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
        initializeGame(playerNames: string[], initialScore: number) {
            const { createDeck, shuffleDeck } = usePokerLogic();
            this.players = playerNames.map((name, index) =>
                createInitialPlayerState(`player-${index}`, name, initialScore, index === 0)
            );
            this.deck = shuffleDeck(createDeck());
            this.currentStreet = 0;
            this.currentPlayerIndex = -1;
            this.dealerIndex = 0;
            this.gamePhase = 'waiting';
            this.cardsOnHand = [];
            this.selectedCardToDiscardIndex = null;
            this.selectedCardToPlaceIndex = null;
            this.showdownResults = null;
            this.message = "Starting Game...";
            console.log("Game Initialized");
            // Начинаем первую руку после небольшой паузы
            setTimeout(() => this.startNewHand(), 500);
        },

        startNewHand() {
            const { createDeck, shuffleDeck } = usePokerLogic();
            console.log("Starting new hand...");

            // Сдвиг дилера (если не первая рука)
            if (this.currentStreet > 0 || this.gamePhase === 'round_over') {
                 this.dealerIndex = getNextIndex(this.dealerIndex, this.players.length);
            }
            this.players.forEach((p, index) => p.isDealer = index === this.dealerIndex);

            // Сброс состояния рук/полей/статусов
            this.deck = shuffleDeck(createDeck());
            this.currentStreet = 1;
            this.players.forEach(p => {
                p.board = { top: Array(3).fill(null), middle: Array(5).fill(null), bottom: Array(5).fill(null) };
                p.royalties = { top: null, middle: null, bottom: null };
                p.combinations = { top: null, middle: null, bottom: null };
                p.isFoul = false;
                p.isActive = false;
                p.lastRoundScoreChange = 0;
                // Обработка Fantasyland (перевод из earned/pending в active)
                if (p.fantasylandState === 'earned' || p.fantasylandState === 'pending') {
                    console.warn(`Player ${p.id} should start Fantasyland - NOT IMPLEMENTED`);
                    p.fantasylandState = 'none'; // Сбрасываем, т.к. не реализовано
                } else {
                    p.fantasylandState = 'none';
                }
            });

            // Определяем первого ходящего
            this.currentPlayerIndex = getNextIndex(this.dealerIndex, this.players.length);
            this.showdownResults = null; // Очищаем результаты предыдущего раунда
            this._advanceGamePhase('dealing_street_1');
        },

        // --- Dealing ---
        _dealCurrentPlayer() {
            const { dealCards } = usePokerLogic();
            const player = this.getCurrentPlayer;
            if (!player || !player.isActive) {
                 console.error("Cannot deal: No active player or player not active");
                 return;
            }

            let cardsToDeal = 0;
            let nextPhase: GamePhase = 'placing_street_1';

            if (this.currentStreet === 1) {
                cardsToDeal = 5;
                nextPhase = 'placing_street_1';
            } else if (this.currentStreet >= 2 && this.currentStreet <= 5) {
                cardsToDeal = 3;
                nextPhase = 'placing_street_2_5';
            } else {
                console.error("Invalid street to deal:", this.currentStreet);
                this._advanceGamePhase('showdown');
                return;
            }

            const { dealtCards, remainingDeck } = dealCards(this.deck, cardsToDeal);
            this.deck = remainingDeck;
            this.cardsOnHand = dealtCards; // Карты сохраняются в общем состоянии для текущего игрока
            this.selectedCardToDiscardIndex = null;
            this.selectedCardToPlaceIndex = null;

            console.log(`Dealt ${cardsToDeal} cards to ${player.name} on street ${this.currentStreet}`);

            // Если это ход ИИ, сразу запускаем его логику
            if (this.isAiTurn) {
                this._advanceGamePhase('ai_thinking');
            } else {
                // Иначе, переходим в фазу размещения для игрока
                this._advanceGamePhase(nextPhase);
                this.message = this.currentStreet === 1 ? "Place 5 cards" : "Select 1 card to discard, place 2";
            }
        },

        // --- Player Actions ---
        selectCard(index: number) {
            if (!this.isMyTurn || index < 0 || index >= this.cardsOnHand.length) return;

            const currentPhase = this.gamePhase;

            if (currentPhase === 'placing_street_1') {
                this.selectedCardToPlaceIndex = index;
                this.selectedCardToDiscardIndex = null;
                this.message = "Select slot to place card";
            } else if (currentPhase === 'placing_street_2_5') {
                if (this.selectedCardToDiscardIndex === null) {
                    this.selectedCardToDiscardIndex = index;
                    this.selectedCardToPlaceIndex = null;
                    this.message = "Select card to place";
                } else {
                    if (index !== this.selectedCardToDiscardIndex) {
                        this.selectedCardToPlaceIndex = index;
                         this.message = "Select slot to place card";
                    } else {
                        this.selectedCardToDiscardIndex = null;
                        this.selectedCardToPlaceIndex = null;
                         this.message = "Select 1 card to discard, place 2";
                    }
                }
            }
        },

        placeSelectedCard(rowIndex: number, slotIndex: number) {
            const player = this.getCurrentPlayer;
            // Проверяем, что это ход игрока (не ИИ)
            if (!player || !this.isMyTurn || this.selectedCardToPlaceIndex === null) return;

            const cardToPlace = this.cardsOnHand[this.selectedCardToPlaceIndex];
            if (!cardToPlace) return;

            const rowKey = rowIndex === 0 ? 'top' : rowIndex === 1 ? 'middle' : 'bottom';
            const targetRow = player.board[rowKey];

            if (slotIndex < targetRow.length && targetRow[slotIndex] === null) {
                targetRow[slotIndex] = { ...cardToPlace };
                const placedCardIndex = this.selectedCardToPlaceIndex;
                this.cardsOnHand = this.cardsOnHand.filter((_, i) => i !== placedCardIndex);

                if (this.selectedCardToDiscardIndex !== null) {
                    if (placedCardIndex < this.selectedCardToDiscardIndex) {
                        this.selectedCardToDiscardIndex--;
                    }
                    if (this.cardsOnHand.length === 1) {
                         this.selectedCardToDiscardIndex = 0;
                         this.message = `Confirm discard ${this.cardsOnHand[0]?.rank}?`;
                    } else if (this.cardsOnHand.length === 2) {
                         this.message = "Select another card to place";
                    }
                } else if (this.gamePhase === 'placing_street_1') {
                     this.message = this.cardsOnHand.length > 0 ? "Select card to place" : "Confirm placement (Ready)";
                }

                this.selectedCardToPlaceIndex = null;
                this.updateBoardState(player.id); // Обновляем доску после размещения
            } else {
                this.message = "Slot is occupied!";
                this.selectedCardToPlaceIndex = null; // Сбросить выбор, если слот занят
            }
        },

        // Обновление состояния доски (роялти, фол, комбинации)
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
                     console.warn(`Player ${playerId} has a FOUL hand!`);
                     player.royalties = { top: null, middle: null, bottom: null }; // Обнуляем роялти
                 }
            } else {
                player.isFoul = false;
            }
        },

        // Подтверждение действия игрока (Готово / Сбросить)
        confirmAction() {
            if (!this.isMyTurn || !this.canConfirmAction) return;
            const player = this.getCurrentPlayer!;
            console.log(`${player.name} confirmed action on street ${this.currentStreet}.`);
            this.cardsOnHand = []; // Очищаем руку игрока
            this.selectedCardToDiscardIndex = null;
            this.selectedCardToPlaceIndex = null;
            this.moveToNextPlayer();
        },

        // --- AI Logic ---
        _runAiTurn() {
            const aiPlayer = this.getCurrentPlayer;
            if (!aiPlayer || !this.isAiTurn) return;

            console.log(`AI Turn: ${aiPlayer.name} on street ${this.currentStreet}`);
            let hand = [...this.cardsOnHand]; // Копия руки ИИ

            // --- Логика сброса (улица 2-5) ---
            let cardToDiscardIndex = 0; // По умолчанию сбрасываем первую карту
            if (this.currentStreet >= 2 && hand.length === 3) {
                // Очень простая логика: сбрасываем самую младшую карту
                hand.sort((a, b) => usePokerLogic().compareHands({value: RANK_VALUES[a.rank], name:''}, {value: RANK_VALUES[b.rank], name:''})); // Сортируем по возрастанию
                cardToDiscardIndex = 0; // Индекс самой младшей
                const cardToDiscard = hand.splice(cardToDiscardIndex, 1)[0]; // Удаляем карту из руки
                console.log(`AI ${aiPlayer.name} discards ${cardToDiscard.display}`);
            }

            // --- Логика размещения ---
            // Очень примитивно: пытаемся разместить снизу вверх, чтобы уменьшить шанс фола
            const placeOrder: { row: keyof PlayerBoard, index: number }[] = [
                // Bottom row
                { row: 'bottom', index: 0 }, { row: 'bottom', index: 1 }, { row: 'bottom', index: 2 }, { row: 'bottom', index: 3 }, { row: 'bottom', index: 4 },
                // Middle row
                { row: 'middle', index: 0 }, { row: 'middle', index: 1 }, { row: 'middle', index: 2 }, { row: 'middle', index: 3 }, { row: 'middle', index: 4 },
                 // Top row
                { row: 'top', index: 0 }, { row: 'top', index: 1 }, { row: 'top', index: 2 },
            ];

            for (const card of hand) {
                let placed = false;
                for (const target of placeOrder) {
                    if (aiPlayer.board[target.row][target.index] === null) {
                        aiPlayer.board[target.row][target.index] = { ...card }; // Копируем карту
                        console.log(`AI ${aiPlayer.name} placed ${card.display} in ${target.row}[${target.index}]`);
                        placed = true;
                        break; // Переходим к следующей карте
                    }
                }
                if (!placed) {
                    console.error(`AI ${aiPlayer.name} could not place card ${card.display}! Board full?`);
                }
            }

            this.updateBoardState(aiPlayer.id); // Обновляем доску ИИ
            this.cardsOnHand = []; // Очищаем "руку" состояния для ИИ
            this.moveToNextPlayer(); // Передаем ход дальше
        },

        // Переход хода к следующему игроку
        moveToNextPlayer() {
            const currentPlayer = this.getCurrentPlayer;
            if (currentPlayer) {
                currentPlayer.isActive = false; // Деактивируем текущего
            }

            const nextPlayerIndex = getNextIndex(this.currentPlayerIndex, this.players.length);
            this.currentPlayerIndex = nextPlayerIndex;

            // Проверяем, закончили ли все игроки текущую улицу
            const firstPlayerIndexOfStreet = getNextIndex(this.dealerIndex, this.players.length);
            if (this.currentPlayerIndex === firstPlayerIndexOfStreet) {
                // --- Все игроки закончили улицу ---
                this.currentStreet++;
                if (this.currentStreet > 5) {
                    this._advanceGamePhase('showdown'); // Переход к вскрытию
                } else {
                     console.log(`--- Street ${this.currentStreet} starting ---`);
                     this._advanceGamePhase('dealing_street_2_5'); // Начинаем следующую улицу
                }
            } else {
                 // --- Просто передаем ход следующему игроку на той же улице ---
                 const nextPlayer = this.getCurrentPlayer;
                 if (nextPlayer) {
                     this._advanceGamePhase(this.currentStreet === 1 ? 'dealing_street_1' : 'dealing_street_2_5'); // Фаза раздачи для следующего
                 } else {
                     console.error("Could not find next player");
                 }
            }
        },

        // --- Showdown ---
        calculateShowdown() {
            console.log("Calculating Showdown...");
            const { compareHands } = usePokerLogic();
            const results: ShowdownPairResult[] = [];
            const numPlayers = this.players.length;

            // Финальное обновление состояния досок
            this.players.forEach(p => this.updateBoardState(p.id));

            // Сбрасываем предыдущие изменения счета
            this.players.forEach(p => p.lastRoundScoreChange = 0);

            // Попарное сравнение
            for (let i = 0; i < numPlayers; i++) {
                for (let j = i + 1; j < numPlayers; j++) {
                    const playerA = this.players[i];
                    const playerB = this.players[j];

                    let linePointsA = 0;
                    let linePointsB = 0;
                    let lineWinsA = 0;
                    let lineWinsB = 0;

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

                        if (lineWinsA === 3) linePointsA += 3; // Scoop bonus
                        if (lineWinsB === 3) linePointsB += 3;

                    } else if (playerA.isFoul && !playerB.isFoul) {
                        linePointsB = 6; lineWinsB = 3;
                        linesResult.top = -1; linesResult.middle = -1; linesResult.bottom = -1;
                    } else if (!playerA.isFoul && playerB.isFoul) {
                        linePointsA = 6; lineWinsA = 3;
                        linesResult.top = 1; linesResult.middle = 1; linesResult.bottom = 1;
                    } // else: оба фол, linePoints = 0

                    const royaltyA = this.getCombinedRoyaltiesPoints(playerA.id);
                    const royaltyB = this.getCombinedRoyaltiesPoints(playerB.id);

                    // Общие очки за раунд = очки за линии + роялти
                    const totalPointsA = linePointsA + royaltyA;
                    const totalPointsB = linePointsB + royaltyB;

                    // Разница очков между игроками
                    const netPointsA = totalPointsA - totalPointsB;
                    const netPointsB = totalPointsB - totalPointsA;

                    // Ограничение по стеку (нельзя выиграть/проиграть больше, чем есть у оппонента НА НАЧАЛО РУКИ - это сложно отследить без доп. состояния, пока упростим)
                    // Упрощение: пока не ограничиваем по стеку в этой реализации
                    const finalPointsA = netPointsA;
                    const finalPointsB = netPointsB;

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
                     console.log(`Showdown ${playerA.name} vs ${playerB.name}: A=${finalPointsA}, B=${finalPointsB} (Lines A:${linePointsA}, B:${linePointsB}; Royalty A:${royaltyA}, B:${royaltyB})`);
                }
            }

            // Применяем изменение счета
            this.players.forEach(p => {
                p.score += p.lastRoundScoreChange;
                // Проверка Fantasyland Earned (QQ+ на топе, не фол)
                 const topHand = p.combinations.top;
                 if (!p.isFoul && topHand && topHand.name.includes('Pair') && RANK_VALUES[topHand.name.slice(-2,-1) as Rank] >= RANK_VALUES['Q']) {
                     console.log(`${p.name} earned Fantasyland! (QQ+)`);
                     p.fantasylandState = 'earned';
                 } else if (!p.isFoul && topHand && topHand.name.includes('Set')) {
                      console.log(`${p.name} earned Fantasyland! (Set)`);
                      p.fantasylandState = 'earned';
                 }
            });

            this.showdownResults = results;
            this.message = "Round Over";
            this._advanceGamePhase('round_over');

            // Запускаем следующую руку через паузу
            setTimeout(() => {
                 this.startNewHand();
            }, 5000); // Пауза 5 секунд
        },

        // --- Управление фазами ---
        _advanceGamePhase(newPhase: GamePhase) {
            console.log(`Phase change: ${this.gamePhase} -> ${newPhase}`);
            this.gamePhase = newPhase;
            const player = this.getCurrentPlayer;

            switch (newPhase) {
                case 'dealing_street_1':
                case 'dealing_street_2_5':
                    if (player) {
                        player.isActive = true; // Активируем игрока ПЕРЕД раздачей
                        this.message = `Dealing to ${player.name}...`;
                        // Небольшая задержка перед раздачей для визуального эффекта
                        setTimeout(() => this._dealCurrentPlayer(), 300);
                    } else {
                         console.error("Cannot deal, no current player");
                    }
                    break;
                case 'ai_thinking':
                     if (player) {
                         this.message = `${player.name} is thinking...`;
                         // Имитация "раздумий" ИИ
                         setTimeout(() => this._runAiTurn(), 750 + Math.random() * 500); // Пауза 0.75-1.25 сек
                     }
                    break;
                case 'showdown':
                    this.message = "Calculating results...";
                    this.players.forEach(p => p.isActive = false); // Деактивируем всех
                    // Небольшая задержка перед расчетом
                    setTimeout(() => this.calculateShowdown(), 1000);
                    break;
                case 'round_over':
                     this.message = "Round Over! Scores updated.";
                     this.players.forEach(p => p.isActive = false);
                     // Следующая рука запустится по таймеру в calculateShowdown
                     break;
                case 'placing_street_1':
                case 'placing_street_2_5':
                     // Сообщение устанавливается в _dealCurrentPlayer или selectCard/placeSelectedCard
                     break; // Ничего дополнительно не делаем
                 case 'waiting':
                     this.message = "Waiting for game to start...";
                     break;
            }
        }
    }
});
