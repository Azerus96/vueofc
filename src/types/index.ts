// Типы для карт
export type Suit = 's' | 'h' | 'd' | 'c';
export type Rank = '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | 'T' | 'J' | 'Q' | 'K' | 'A';

export interface Card {
  id: string;
  rank: Rank;
  suit: Suit;
  display: string; // e.g., 'A♠'
  originalPosition?: { // Для возврата карты в руку
      row: 'hand';
      index: number; // Позиция в руке (может быть неточной после перемещений)
  } | {
      row: 'top' | 'middle' | 'bottom';
      index: number; // Позиция на доске
  }
}

// Типы для доски игрока
export interface PlayerBoard {
  top: (Card | null)[];
  middle: (Card | null)[];
  bottom: (Card | null)[];
}

// Типы для оценки комбинаций
export interface CombinationResult { name: string; value: number; cards?: Card[]; }
export interface RoyaltyResult { points: number; name: string; }
export interface HandEvaluationResult extends CombinationResult { royalty?: RoyaltyResult | null; }

// Типы для состояния игрока
export interface PlayerState {
  id: string; name: string; avatar?: string; score: number; board: PlayerBoard;
  isDealer: boolean; isActive: boolean; timeRemaining?: number; timeBank?: number;
  fantasylandState: 'none' | 'active' | 'pending' | 'earned';
  lastRoundScoreChange: number;
  royalties: { top: RoyaltyResult | null; middle: RoyaltyResult | null; bottom: RoyaltyResult | null; };
  isFoul: boolean;
  combinations: { top: CombinationResult | null; middle: CombinationResult | null; bottom: CombinationResult | null; }
}

// Типы для фаз игры
export type GamePhase =
  | 'not_started' | 'waiting' | 'starting' | 'dealing_street_1' | 'placing_street_1'
  | 'dealing_street_2_5' | 'placing_street_2_5' | 'ai_thinking' | 'showdown' | 'round_over'
  | 'fantasyland_dealing' | 'fantasyland_placing';

// Типы для результатов вскрытия
export interface ShowdownPairResult {
    playerA_id: string; playerB_id: string; pointsA: number; pointsB: number;
    lines: { top: number; middle: number; bottom: number; };
    scoopA: boolean; scoopB: boolean; royaltyA: number; royaltyB: number;
}

// Типы для общего состояния игры
export interface GameState {
  players: PlayerState[];
  deck: Card[];
  discardPile: Card[]; // Добавлено поле для сброшенных карт
  currentStreet: number;
  gamePhase: GamePhase;
  currentPlayerIndex: number;
  dealerIndex: number;
  cardsOnHand: Card[];
  // selectedCardToDiscardIndex: number | null; // Убрано, используется новая логика
  showdownResults: ShowdownPairResult[] | null;
  message: string | null;
  opponentCount: 1 | 2;
}
