import type { Card, Rank, Suit, HandEvaluationResult, RoyaltyResult, CombinationResult, PlayerBoard } from '@/types';

// --- Constants ---
const RANKS: Rank[] = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
const SUITS: Suit[] = ['s', 'h', 'd', 'c'];
const SUIT_SYMBOLS: Record<Suit, string> = { s: '♠', h: '♥', d: '♦', c: '♣' }; // Unicode символы

const RANK_VALUES: Record<Rank, number> = {
  '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
};

// --- Royalty Tables (American Rules) ---
// Русские названия для роялти
const ROYALTIES_BOTTOM: Record<string, number> = {
    'Стрит': 2, 'Флеш': 4, 'Фулл-хаус': 6, 'Каре': 10, 'Стрит-флеш': 15, 'Флеш-рояль': 25
};
const ROYALTIES_MIDDLE: Record<string, number> = {
    'Сет': 2, 'Стрит': 4, 'Флеш': 8, 'Фулл-хаус': 12, 'Каре': 20, 'Стрит-флеш': 30, 'Флеш-рояль': 50
};
const ROYALTIES_TOP_LOOKUP: Record<string, { points: number; name: string }> = {
    '66': { points: 1, name: "Пара 66" }, '77': { points: 2, name: "Пара 77" }, '88': { points: 3, name: "Пара 88" },
    '99': { points: 4, name: "Пара 99" }, 'TT': { points: 5, name: "Пара TT" }, 'JJ': { points: 6, name: "Пара JJ" },
    'QQ': { points: 7, name: "Пара QQ" }, 'KK': { points: 8, name: "Пара KK" }, 'AA': { points: 9, name: "Пара AA" },
    '222': { points: 10, name: "Сет 222" }, '333': { points: 11, name: "Сет 333" }, '444': { points: 12, name: "Сет 444" },
    '555': { points: 13, name: "Сет 555" }, '666': { points: 14, name: "Сет 666" }, '777': { points: 15, name: "Сет 777" },
    '888': { points: 16, name: "Сет 888" }, '999': { points: 17, name: "Сет 999" }, 'TTT': { points: 18, name: "Сет TTT" },
    'JJJ': { points: 19, name: "Сет JJJ" }, 'QQQ': { points: 20, name: "Сет QQQ" }, 'KKK': { points: 21, name: "Сет KKK" },
    'AAA': { points: 22, name: "Сет AAA" }
};

// --- Helper Functions ---
const getRankValue = (rank: Rank): number => RANK_VALUES[rank];
const sortCards = (cards: Card[]): Card[] => {
    return [...cards].sort((a, b) => getRankValue(b.rank) - getRankValue(a.rank));
};

// --- Evaluation Functions ---
const calculateHandValue = (handType: number, kickers: Rank[]): number => {
    let value = handType * Math.pow(10, 10);
    kickers.forEach((kicker, index) => {
        value += getRankValue(kicker) * Math.pow(10, 8 - index * 2);
    });
    return value;
};

function evaluateFiveCardHand(hand: Card[]): HandEvaluationResult {
    if (hand.length !== 5) return { name: 'Неверная рука', value: -1 };

    const sortedHand = sortCards(hand);
    const ranks = sortedHand.map(c => c.rank);
    const suits = sortedHand.map(c => c.suit);

    const isFlush = new Set(suits).size === 1;
    const rankCounts = ranks.reduce((acc, rank) => {
        acc[rank] = (acc[rank] || 0) + 1;
        return acc;
    }, {} as Record<Rank, number>);

    const counts = Object.values(rankCounts).sort((a, b) => b - a);
    const uniqueSortedRanks = [...new Set(ranks)].sort((a, b) => getRankValue(b) - getRankValue(a));

    let isStraight = false;
    let straightHighCard: Rank = '5';
    if (uniqueSortedRanks.length >= 5) {
        if (getRankValue(uniqueSortedRanks[0]) - getRankValue(uniqueSortedRanks[4]) === 4) {
            isStraight = true;
            straightHighCard = uniqueSortedRanks[0];
        } else if (uniqueSortedRanks.map(r => RANK_VALUES[r]).join(',') === '14,5,4,3,2') {
             isStraight = true;
             straightHighCard = '5';
             uniqueSortedRanks.splice(0, 1);
             uniqueSortedRanks.push('A');
        }
    }

    if (isStraight && isFlush) {
        const isRoyal = straightHighCard === 'A' && uniqueSortedRanks[1] === 'K';
        const name = isRoyal ? 'Флеш-рояль' : 'Стрит-флеш';
        const value = calculateHandValue(9, [straightHighCard]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 4) {
        const fourRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 4) as Rank;
        const kicker = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 1) as Rank;
        const name = 'Каре';
        const value = calculateHandValue(8, [fourRank, kicker]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 3 && counts[1] === 2) {
        const threeRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 3) as Rank;
        const pairRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 2) as Rank;
        const name = 'Фулл-хаус';
        const value = calculateHandValue(7, [threeRank, pairRank]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (isFlush) {
        const name = 'Флеш';
        const value = calculateHandValue(6, uniqueSortedRanks.slice(0, 5));
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (isStraight) {
        const name = 'Стрит';
        const value = calculateHandValue(5, [straightHighCard]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 3) {
        const threeRank = Object.keys(rankCounts).find(r => rankCounts[r as Rank] === 3) as Rank;
        const kickers = uniqueSortedRanks.filter(r => r !== threeRank).slice(0, 2);
        const name = 'Сет';
        const value = calculateHandValue(4, [threeRank, ...kickers]);
        const royaltyPoints = ROYALTIES_MIDDLE[name];
        return { name, value, royalty: royaltyPoints ? { points: royaltyPoints, name: `+${royaltyPoints} ${name}` } : null };
    }
    if (counts[0] === 2 && counts[1] === 2) {
        const pairs = uniqueSortedRanks.filter(r => rankCounts[r] === 2).sort((a, b) => getRankValue(b) - getRankValue(a));
        const kicker = uniqueSortedRanks.find(r => rankCounts[r] === 1) as Rank;
        const name = 'Две пары';
        const value = calculateHandValue(3, [pairs[0], pairs[1], kicker]);
        return { name, value, royalty: null };
    }
    if (counts[0] === 2) {
        const pairRank = uniqueSortedRanks.find(r => rankCounts[r] === 2) as Rank;
        const kickers = uniqueSortedRanks.filter(r => r !== pairRank).slice(0, 3);
        const name = 'Пара';
        const value = calculateHandValue(2, [pairRank, ...kickers]);
        return { name, value, royalty: null };
    }

    const name = `Старшая карта ${uniqueSortedRanks[0]}`;
    const value = calculateHandValue(1, uniqueSortedRanks.slice(0, 5));
    return { name, value, royalty: null };
}

function evaluateThreeCardHand(hand: Card[]): HandEvaluationResult {
    if (hand.length !== 3) return { name: 'Неверная рука', value: -1 };

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
        const name = `Сет ${rank}${rank}${rank}`;
        const value = calculateHandValue(4, [rank]);
        return { name, value, royalty: royaltyInfo ? { points: royaltyInfo.points, name: `+${royaltyInfo.points} ${royaltyInfo.name}` } : null };
    }
    if (counts[0] === 2) {
        const pairRank = uniqueSortedRanks.find(r => rankCounts[r] === 2) as Rank;
        const kicker = uniqueSortedRanks.find(r => rankCounts[r] === 1) as Rank;
        const key = `${pairRank}${pairRank}`;
        const royaltyInfo = ROYALTIES_TOP_LOOKUP[key];
        const name = `Пара ${pairRank}${pairRank}`;
        const value = calculateHandValue(2, [pairRank, kicker]);
        const royalty = (royaltyInfo && getRankValue(pairRank) >= 6) ? { points: royaltyInfo.points, name: `+${royaltyInfo.points} ${royaltyInfo.name}` } : null;
        return { name, value, royalty };
    }

    const name = `Старшая карта ${ranks[0]}`;
    const value = calculateHandValue(1, ranks);
    return { name, value, royalty: null };
}

function compareHands(handA: CombinationResult | null, handB: CombinationResult | null): number {
    if (!handA && !handB) return 0;
    if (!handA) return -1;
    if (!handB) return 1;
    return handA.value - handB.value;
}

function isBoardValid(board: { top: CombinationResult | null, middle: CombinationResult | null, bottom: CombinationResult | null }): boolean {
    if (!board.top || !board.middle || !board.bottom) {
        return true;
    }
    return compareHands(board.top, board.middle) <= 0 && compareHands(board.middle, board.bottom) <= 0;
}

function getRoyalty(line: 'top' | 'middle' | 'bottom', evaluation: HandEvaluationResult | null): RoyaltyResult | null {
   return evaluation?.royalty ?? null;
}

// --- Deck Functions ---
function createDeck(): Card[] {
    const deck: Card[] = [];
    let idCounter = 0;
    for (const suit of SUITS) {
        for (const rank of RANKS) {
            idCounter++;
            const display = `${rank}${SUIT_SYMBOLS[suit]}`;
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
        console.warn("Недостаточно карт в колоде!");
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
        getRoyalty,
        createDeck,
        shuffleDeck,
        dealCards,
    };
}
