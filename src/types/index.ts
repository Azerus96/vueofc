// Типы для карт
export type Suit = 's' | 'h' | 'd' | 'c'; // Spades, Hearts, Diamonds, Clubs
export type Rank = '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | 'T' | 'J' | 'Q' | 'K' | 'A';

export interface Card {
  id: string; // Уникальный ID для key в v-for и отслеживания
  rank: Rank;
  suit: Suit;
  display: string; // Для удобства, например 'As'
}

// Типы для доски игрока
export interface PlayerBoard {
  top: (Card | null)[];    // 3 слота
  middle: (Card | null)[]; // 5 слотов
  bottom: (Card | null)[]; // 5 слотов
}

// Типы для оценки комбинаций
export interface CombinationResult {
    name: string; // e.g., "Flush", "Pair QQ"
    value: number; // Числовое значение для сравнения (включая кикеры)
    cards?: Card[]; // Карты, формирующие комбинацию (опционально)
}

export interface RoyaltyResult {
    points: number;
    name: string; // e.g., "+4 Flush", "+9 AA"
}

export interface HandEvaluationResult extends CombinationResult {
    royalty?: RoyaltyResult | null; // Может быть null если нет роялти
}

// Типы для состояния игрока
export interface PlayerState {
  id: string;
  name: string;
  avatar?: string; // URL аватара (опционально)
  score: number; // Текущие очки/фишки
  board: PlayerBoard;
  isDealer: boolean;
  isActive: boolean; // Чей сейчас ход
  timeRemaining?: number; // Оставшееся время хода
  timeBank?: number; // Резервное время
  fantasylandState: 'none' | 'active' | 'pending' | 'earned'; // Статус Fantasyland
  lastRoundScoreChange: number; // Изменение счета за прошлый раунд (для анимации)
  royalties: { // Роялти за текущую руку (обновляется динамически)
      top: RoyaltyResult | null;
      middle: RoyaltyResult | null;
      bottom: RoyaltyResult | null;
  };
  isFoul: boolean; // Рука мертвая?
  // Дополнительно для отображения комбинаций
  combinations: {
      top: CombinationResult | null;
      middle: CombinationResult | null;
      bottom: CombinationResult | null;
  }
}

// Типы для фаз игры
export type GamePhase =
  | 'waiting'           // Ожидание игроков
  | 'starting'          // Начало раунда
  | 'dealing_street_1'  // Раздача 1й улицы
  | 'placing_street_1'  // Расстановка 1й улицы
  | 'dealing_street_2_5'// Раздача 2-5 улиц
  | 'placing_street_2_5'// Расстановка 2-5 улиц (включает выбор сброса)
  | 'ai_thinking'       // "Ход" ИИ (для имитации паузы)
  | 'showdown'          // Вскрытие и подсчет
  | 'round_over'        // Конец раунда, показ результатов
  | 'fantasyland_dealing' // Раздача для Fantasyland (НЕ РЕАЛИЗОВАНО)
  | 'fantasyland_placing'; // Расстановка Fantasyland (НЕ РЕАЛИЗОВАНО)

// Типы для результатов вскрытия
export interface ShowdownPairResult {
    playerA_id: string;
    playerB_id: string;
    pointsA: number; // Очки A против B (включая роялти)
    pointsB: number; // Очки B против A (включая роялти)
    lines: { // Результат по линиям (1 = A win, -1 = B win, 0 = tie)
        top: number;
        middle: number;
        bottom: number;
    };
    scoopA: boolean;
    scoopB: boolean;
    royaltyA: number;
    royaltyB: number;
}

// Типы для общего состояния игры
export interface GameState {
  players: PlayerState[];
  deck: Card[];
  currentStreet: number; // 1 to 5
  gamePhase: GamePhase;
  currentPlayerIndex: number;
  dealerIndex: number;
  cardsOnHand: Card[]; // Карты, розданные текущему игроку
  selectedCardToDiscardIndex: number | null; // Индекс карты для сброса в cardsOnHand
  selectedCardToPlaceIndex: number | null;   // Индекс карты для размещения в cardsOnHand
  showdownResults: ShowdownPairResult[] | null; // Результаты последнего вскрытия
  message: string | null; // Сообщение для игрока (например, "Place 5 cards")
}
