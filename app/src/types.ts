// === CORE TYPE DEFINITIONS ===

export interface ChecklistItem {
  id: string;
  label: string;
  type: 'checkbox' | 'boolean_toggle';
  visible_if?: string;
}

export interface Slide {
  id?: string;
  header?: string;
  label?: string;
  text: string;
}

export interface CardContent {
  title: string;
  body?: string;
  subtitle?: string;
  footer_note?: string;
  slides?: Slide[];
}

export interface ToolboxItem {
  id: string;
  icon: string;
  label: string;
  action: string;
}

export interface TransitionOption {
  label: string;
  sub_label?: string | null;
  preview_card_title?: string | null;
  target_id: string;
}

export interface LinearTransition {
  type: 'linear';
  next_id: string;
}

export interface SplitTransition {
  type: 'split';
  options: TransitionOption[];
}

export interface SelfLoopTransition {
  type: 'self_loop';
  next_id: string;
}

export type Transition = LinearTransition | SplitTransition | SelfLoopTransition;

export interface WheelConfig {
  position_degrees?: number;
  phase?: string;
  animation?: string;
}

export interface Card {
  id: string;
  type: string;
  content: CardContent;
  checklist: ChecklistItem[];
  wheel_config: WheelConfig;
  transitions: Transition | null;
  status?: string;
  toolbox?: ToolboxItem[];
  local_timer?: {
    enabled: boolean;
    type: string;
    bpm?: number;
    guidance?: string;
  };
}

export interface WheelArc {
  start_degrees: number;
  end_degrees: number;
  direction: 'anticlockwise' | 'clockwise';
  phase_spread_degrees: number;
}

export interface AlgorithmMeta {
  id?: string;
  title?: string;
  source?: string;
  color_theme?: string;
  wheel_arc?: WheelArc;
  global_timer?: {
    enabled: boolean;
    label?: string;
    type?: string;
    auto_start_on_card?: string;
  };
  [key: string]: unknown;
}

export interface Algorithm {
  algorithm_meta: AlgorithmMeta;
  deck: Card[];
}

export type WheelMode = 'COVER' | 'LINEAR' | 'DECISION' | 'LOOP' | 'TERMINAL';

export interface Anchor {
  id: string;
  angle: number;
}

export interface WheelState {
  mode: WheelMode;
  angle: number;
  visualAngle: number;
  dragOrigin: number | null;
  navConsumed: boolean;
}

export interface AppState {
  currentId: string;
  history: string[];
  decisionIndex: number;
  decisionRecords: Record<string, number>;
  decisionTrail: DecisionTrailEntry[];
  decisionTapped: boolean;
  carouselIndex: number;
  timerSeconds: number;
  timerRunning: boolean;
  timerInterval: ReturnType<typeof setInterval> | null;
  checklistState: Record<string, boolean>;
  anchors: Anchor[];
  anchorIndex: number;
  wheel: WheelState;
}

export interface DecisionTrailEntry {
  card_id: string;
  option_index: number;
  option_label: string;
  target_id: string | null;
  interaction: string;
  source: string;
  timestamp: string;
}

export interface AdvanceOptions {
  source?: string;
  splitConfirmed?: boolean;
}

// Automation snapshot types
export interface CardSnapshot {
  id: string;
  type: string;
  status: string | null;
  title: string;
  phase: string | null;
  canonicalAngle: number;
  transitions: TransitionSummary | null;
}

export interface TransitionSummary {
  type: string | null;
  next_id: string | null;
  options: TransitionOptionSummary[];
}

export interface TransitionOptionSummary {
  index: number;
  label: string;
  sub_label: string | null;
  target_id: string | null;
  preview_card_title: string | null;
}

export interface AutomationSnapshot {
  currentId: string;
  algorithmSource: string;
  history: string[];
  historySize: number;
  decisionIndex: number;
  decisionRecords: Record<string, number>;
  decisionTrail: DecisionTrailEntry[];
  carouselIndex: number;
  timerSeconds: number;
  anchors: Anchor[];
  anchorIndex: number;
  decisionTapped: boolean;
  wheel: {
    mode: WheelMode;
    angle: number;
  };
  card: CardSnapshot | null;
}

// Deck map type
export type DeckMap = Record<string, Card>;
