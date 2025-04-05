import type { Card, Rank, Suit, HandEvaluationResult, RoyaltyResult, CombinationResult, PlayerBoard } from '@/types';

// --- Constants ---
const RANKS: Rank[] = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
const SUITS: Suit[] = ['s', 'h', 'd', 'c'];

const RANK_VALUES: Record<Rank, number> = {
  '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
};

// --- Royalty Tables (American Rules) ---
const ROYALTIES_BOTTOM: Record<string, number> = {
    'Straight': 2, 'Flush': 4, 'Full House': 6, 'Four of a Kind': 10, 'Straight Flush': 15, 'Royal Flush': 25
};
const ROYALTIES_MIDDLE: Record<string, number> = {
    'Set': 2, 'Straight': 4, 'Flush': 8, 'Full House': 12, 'Four of a Kind': 20, 'Straight Flush': 30, 'Royal Flush': 50
};
// Используем объект для хранения очков и имени для верхней линии
const ROYALTIES_TOP_LOOKUP: Record<string, { points: number; name: string }> = {
    '66': { points: 1, name: "Pair 66" }, '77': { points: 2, name: "Pair 77" }, '88': { points: 3, name: "Pair 88" },
    '99': { points: 4, name: "Pair 99" }, 'TT': { points: 5, name: "Pair TT" }, 'JJ': { points: 6, name: "Pair JJ" },
    'QQ': { points: 7, name: "Pair QQ" }, 'KK': { points: 8, name: "Pair KK" }, 'AA': { points: 9, name: "Pair AA" },
    '222': { points: 10, name: "Set 222" }, '333': { points: 11, name: "Set 333" }, '444': { points: 12, name: "Set 444" },
    '555': { points: 13, name: "Set 555" }, '666': { points: 14, name: "Set 666" }, '777': { points: 15, name: "Set 777" },
    '888': { points: 16, name: "Set 888" }, '999': { points: 17, name: "Set 999" }, 'TTT': { points: 18, name: "Set TTT" },
    'JJJ': { points: 19, name: "Set JJJ" }, 'QQQ': { points: 20, name: "Set QQQ" }, 'KKK': { points: 21, name: "Set KKK" },
    'AAA': { points: 22, name: "Set AAA" }
};

// --- Helper Functions ---
const getRankValue = (rank: Rank): number => RANK_VALUES[rank];
const sortCards = (cards: Card[]): Card[] => {
    // Сортировка по убыванию ранга
    return [...cards].sort((a, b) => getRankValue(b.rank) - getRankValue(a.rank));
};

// --- Evaluation Functions ---

// Основа для числового значения руки (для сравнения)
// HandType * 10^10 + Kicker1 * 10^8 + Kicker2 * 10^6 + ...
const calculateHandValue = (handType: number, kickers: Rank[]): number => {
    let value = handType * Math.pow(10, 10);
    kickers.forEach((kicker, index) => {
        value += getRankValue(kicker) * Math.pow(10, 8 - index * 2);
    });
    return value;
};

function evaluateFiveCardHand(hand: Card[]): HandEvaluationResult {
    if (hand.length !== 5) return { name: 'Invalid Hand', value: -1 };

    const sortedHand = sortCards(hand);
    const ranks = sortedHand.map(c => c.rank);
    const suits = sortedHand.map(c => c.suit);
    const rankValues = sortedHand.map(c => getRankValue(c.rank));

    const isFlush = new Set(suits).size === 1;
    const rankCounts = ranks.reduce((acc, rank) => {
        acc[rank] = (acc[rank] || 0) + 1;
        return acc;
    }, {} as Record<Rank, number>);

    const counts = Object.values(rankCounts).sort((a, b) => b - a);
    const uniqueSortedRanks = [...new Set(ranks)].sort((a, b) => getRankValue(b) - getRankValue(a)); // Сортируем уникальные ранги по убыванию

    // Проверка на стрит (включая A-5)
    let isStraight = false;
    let straightHighCard: Rank = '5'; // Для A-5
    if (uniqueSortedRanks.length >= 5) {
        // Обычный стрит
        if (getRankValue(uniqueSortedRanks[0]) - getRankValue(uniqueSortedRanks[4]) === 4) {
            isStraight = true;
            straightHighCard = uniqueSortedRanks[0];
        }
        // A-5 стрит ("Wheel")
        else if (uniqueSortedRanks.join('') === 'A5432') {
             isStraight = true;
             straightHighCard = '5'; // Старшая карта в A-5 - это 5
             // Пересортируем кикеры для A-5 для правильного сравнения
             uniqueSortedRanks.splice(0, 1); // Убираем туза
             uniqueSortedRanks.push('A'); // Ставим туза в конец (как 1)
        }
    }

    // --- Определение комбинации ---
    if (isStraight && isFlush) {
        const name = (straightHighCard === 'A' && uniqueSortedRanks[0] === 'K') ? 'Royal Flush' : 'Straight Flush'; // Уточнение Royal Flush
        const value = calculateHandValue(9, [straightHighCard]); // Для стрит-флеша кикер - старшая карта
        const royaltyPoints = name === 'Royal Flush' ? ROYALTIES_MIDDLE['Royal Flush'] : ROYALTIES_MIDDLE['Straight Flush'];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 4) {
        const fourRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 4) as Rank;
        const kicker = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 1) as Rank;
        const name = 'Four of a Kind';
        const value = calculateHandValue(8, [fourRank, kicker]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 3 && counts[1] === 2) {
        const threeRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 3) as Rank;
        const pairRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 2) as Rank;
        const name = 'Full House';
        const value = calculateHandValue(7, [threeRank, pairRank]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (isFlush) {
        const name = 'Flush';
        const value = calculateHandValue(6, uniqueSortedRanks.slice(0, 5)); // Кикеры - 5 старших карт
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (isStraight) {
        const name = 'Straight';
        const value = calculateHandValue(5, [straightHighCard]); // Кикер - старшая карта
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 3) {
        const threeRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 3) as Rank;
        const kickers = uniqueSortedRanks.filter(r => r !== threeRank).slice(0, 2);
        const name = 'Set'; // В OFC часто называют Set вместо Three of a Kind
        const value = calculateHandValue(4, [threeRank, ...kickers]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 2 && counts[1] === 2) {
        const pairs = uniqueSortedRanks.filter(r => rankCounts[r] === 2).sort((a, b) => getRankValue(b) - getRankValue(a));
        const kicker = uniqueSortedRanks.find(r => rankCounts[r] === 1) as Rank;
        const name = 'Two Pair';
        const value = calculateHandValue(3, [pairs[0], pairs[1], kicker]);
        return { name, value, royalty: null }; // Нет роялти за две пары в middle/bottom
    }
    if (counts[0] === 2) {
        const pairRank = uniqueSortedRanks.find(r => rankCounts[r] === 2) as Rank;
        const kickers = uniqueSortedRanks.filter(r => r !== pairRank).slice(0, 3);
        const name = 'Pair';
        const value = calculateHandValue(2, [pairRank, ...kickers]);
        return { name, value, royalty: null }; // Нет роялти за пару в middle/bottom
    }

    // High Card
    const name = `High Card ${uniqueSortedRanks[0]}`;
    const value = calculateHandValue(1, uniqueSortedRanks.slice(0, 5));
    return { name, value, royalty: null };
}

function evaluateThreeCardHand(hand: Card[]): HandEvaluationResult {
    if (hand.length !== 3) return { name: 'Invalid Hand', value: -1 };

    const sortedHand = sortCards(hand);
    const ranks = sortedHand.map(c => c.rank);
    const rankCounts = ranks.reduce((acc, rank) => {
        acc[rank] = (acc[rank] || 0) + 1;
        return acc;
    }, {} as Record<Rank, number>);
    const counts = Object.values(rankCounts).sort((a, b) => b - a);
    const uniqueSortedRanks = [...new Set(ranks)].sort((a, b) => getRankValue(b) - getRankValue(a));

    if (counts[0] === 3) {
        const rank = ranks[0];
        const key = `${rank}${rank}${rank}`;
        const royaltyInfo = ROYALTIES_TOP_LOOKUP[key];
        const name = `Set ${rank}${rank}${rank}`;
        const value = calculateHandValue(4, [rank]); // Тип 4 (выше пары), кикер - ранг сета
        return { name, value, royalty: royaltyInfo ? { points: royaltyInfo.points, name: `+${royaltyInfo.points} ${royaltyInfo.name}` } : null };
    }
    if (counts[0] === 2) {
        const pairRank = uniqueSortedRanks.find(r => rankCounts[r] === 2) as Rank;
        const kicker = uniqueSortedRanks.find(r => rankCounts[r] === 1) as Rank;
        const key = `${pairRank}${pairRank}`;
        const royaltyInfo = ROYALTIES_TOP_LOOKUP[key];
        const name = `Pair ${pairRank}${pairRank}`;
        const value = calculateHandValue(2, [pairRank, kicker]); // Тип 2, кикеры - ранг пары, ранг кикера
        // Роялти только за 66+
        const royalty = (royaltyInfo && getRankValue(pairRank) >= 6) ? { points: royaltyInfo.points, name: `+${royaltyInfo.points} ${royaltyInfo.name}` } : null;
        return { name, value, royalty };
    }

    // High Card
    const name = `High Card ${ranks[0]}`;
    const value = calculateHandValue(1, ranks); // Тип 1, кикеры - все три карты
    return { name, value, royalty: null };
}

// Функция сравнения рук (использует числовое значение)
function compareHands(handA: CombinationResult | null, handB: CombinationResult | null): number {
    if (!handA && !handB) return 0;
    if (!handA) return -1; // A проигрывает, если null
    if (!handB) return 1;  // A выигрывает, если B null
    // Сравниваем числовые значения
    return handA.value - handB.value; // > 0 if A wins, < 0 if B wins, 0 for tie
}

// Проверка валидности всей доски (не фол)
function isBoardValid(board: { top: CombinationResult | null, middle: CombinationResult | null, bottom: CombinationResult | null }): boolean {
    // Считаем валидной, если не все линии заполнены или если иерархия соблюдена
    if (!board.top || !board.middle || !board.bottom) {
        // Если не все линии заполнены, фола еще нет
        return true;
    }
    // Сравниваем только если все линии оценены
    return compareHands(board.top, board.middle) <= 0 && compareHands(board.middle, board.bottom) <= 0;
}

// Получение роялти (уже встроено в HandEvaluationResult)
function getRoyalty(line: 'top' | 'middle' | 'bottom', evaluation: HandEvaluationResult | null): RoyaltyResult | null {
     // Роялти извлекается напрямую из результата оценки, где оно уже было посчитано
     // Дополнительная проверка не нужна, т.к. evaluateXxxHand уже учитывает таблицы роялти
    return evaluation?.royalty ?? null;
}


// --- Deck Functions ---
function createDeck(): Card[] {
    const deck: Card[] = [];
    let idCounter = 0;
    for (const suit of SUITS) {
        for (const rank of RANKS) {
            idCounter++;
            const display = `${rank}${suit}`; // Используем короткое отображение
            deck.push({ id: `card-${idCounter}`, rank, suit, display });
        }
    }
    return deck;
}

function shuffleDeck(deck: Card[]): Card[] {
    const shuffled = [...deck];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

function dealCards(deck: Card[], count: number): { dealtCards: Card[], remainingDeck: Card[] } {
    if (deck.length < count) {
        console.warn("Not enough cards in deck!");
        // Можно вернуть пустой массив или оставшиеся карты
        const dealtCards = deck.slice(0);
        const remainingDeck: Card[] = [];
        return { dealtCards, remainingDeck };
    }
    const dealtCards = deck.slice(0, count);
    const remainingDeck = deck.slice(count);
    return { dealtCards, remainingDeck };
}


// --- Export Composable ---
export function usePokerLogic() {
    return {
        evaluateFiveCardHand,
        evaluateThreeCardHand,
        compareHands,
        isBoardValid,
        getRoyalty, // Оставляем для возможного использования, хотя сейчас не нужно
        createDeck,
        shuffleDeck,
        dealCards,
    };
}
