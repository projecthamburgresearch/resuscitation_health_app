// === ALGORITHM LOADER ===
import type { Algorithm, Card, Transition, WheelArc } from '../types';

// Default fallback algorithm (Paediatric Out-of-Hospital BLS)
const DEFAULT_ALGORITHM: Algorithm = {
  algorithm_meta: {
    id: 'algo_paed_bls_001',
    title: 'Paediatric Out-of-Hospital BLS',
    source: 'Resuscitation Council UK (2021)',
    global_timer: { enabled: true, label: 'Total Time', type: 'count_up' },
  },
  deck: [
    {
      id: 'CARD_00_START',
      type: 'cover',
      content: {
        title: 'Paediatric Basic Life Support',
        subtitle: 'Out-of-Hospital Algorithm',
        footer_note: 'Those trained only in adult BLS should use adult sequence with paediatric modifications.',
      },
      wheel_config: { position_degrees: 330, phase: 'start_point' },
      checklist: [],
      transitions: { type: 'linear', next_id: 'CARD_01_UNRESPONSIVE' },
    },
    {
      id: 'CARD_01_UNRESPONSIVE',
      type: 'standard',
      content: { title: 'Assessment', body: 'Is the child unresponsive?' },
      wheel_config: { position_degrees: 0, phase: 'assessment' },
      checklist: [
        { id: 'chk_safe', label: 'Area is safe to approach', type: 'checkbox' },
        { id: 'chk_unresp', label: 'Confirm Unresponsiveness', type: 'checkbox' },
      ],
      transitions: { type: 'linear', next_id: 'CARD_02_SHOUT' },
    },
    {
      id: 'CARD_02_SHOUT',
      type: 'standard',
      content: { title: 'Call for Help', body: 'Shout loudly for help.' },
      wheel_config: { position_degrees: 15, phase: 'action' },
      checklist: [
        { id: 'toggle_2nd_rescuer', label: 'Is a 2nd rescuer present?', type: 'boolean_toggle' },
        { id: 'chk_call_999', label: 'Call EMS (999)', type: 'checkbox', visible_if: 'toggle_2nd_rescuer == true' },
        { id: 'chk_get_aed', label: 'Collect and apply AED', type: 'checkbox', visible_if: 'toggle_2nd_rescuer == true' },
      ],
      transitions: { type: 'linear', next_id: 'CARD_03_AIRWAY' },
    },
    {
      id: 'CARD_03_AIRWAY',
      type: 'standard',
      content: { title: 'Airway', body: 'Open Airway', slides: [{ label: 'Technique', text: 'Head tilt, chin lift' }] },
      wheel_config: { position_degrees: 30, phase: 'action' },
      checklist: [],
      transitions: { type: 'linear', next_id: 'CARD_04_BREATHING_DECISION' },
    },
    {
      id: 'CARD_04_BREATHING_DECISION',
      type: 'decision',
      content: { title: 'Breathing Check', body: 'Is the child breathing normally?' },
      wheel_config: { position_degrees: 45, phase: 'decision' },
      checklist: [],
      transitions: {
        type: 'split',
        options: [
          { label: 'YES', preview_card_title: 'Observe & Assess', target_id: 'CARD_END_OBSERVE' },
          { label: 'NO', sub_label: 'or any doubt', preview_card_title: '5 Rescue Breaths', target_id: 'CARD_05_BREATHS' },
        ],
      },
    },
    {
      id: 'CARD_END_OBSERVE',
      type: 'terminal',
      content: { title: 'Observation', body: 'Observe and re-assess as necessary.' },
      wheel_config: { position_degrees: 60, phase: 'complete' },
      checklist: [],
      transitions: null,
      status: 'complete',
    },
    {
      id: 'CARD_05_BREATHS',
      type: 'carousel_action',
      content: {
        title: '5 Rescue Breaths',
        slides: [
          { id: 'slide_infant', header: 'Infant Technique', text: 'Mouth to nose/mouth' },
          { id: 'slide_child', header: 'Child Technique', text: 'Mouth to mouth' },
        ],
      },
      wheel_config: { position_degrees: 90, phase: 'intervention' },
      toolbox: [{ id: 'calc_age', icon: 'calculator', label: 'Age Calculator', action: 'open_modal_age_calc' }],
      checklist: [
        { id: 'toggle_single_rescuer', label: 'Are you a single rescuer?', type: 'boolean_toggle' },
        { id: 'chk_speakerphone', label: 'Call EMS on speakerphone', type: 'checkbox', visible_if: 'toggle_single_rescuer == true' },
        { id: 'chk_delay_call', label: 'Do CPR 1 min before leaving to call', type: 'checkbox', visible_if: 'toggle_single_rescuer == true AND chk_speakerphone == false' },
      ],
      transitions: { type: 'linear', next_id: 'CARD_06_CHECK_LIFE_PRE_CPR' },
    },
    {
      id: 'CARD_06_CHECK_LIFE_PRE_CPR',
      type: 'decision',
      content: { title: 'Signs of Life?', body: 'Were signs of life observed during rescue breaths?' },
      wheel_config: { position_degrees: 120, phase: 'check' },
      checklist: [],
      transitions: {
        type: 'split',
        options: [
          { label: 'YES', target_id: 'CARD_END_RECOVERY' },
          { label: 'NO', target_id: 'CARD_07_COMPRESSIONS' },
        ],
      },
    },
    {
      id: 'CARD_07_COMPRESSIONS',
      type: 'loop_start',
      content: { title: '30 Chest Compressions', body: 'Perform continuous chest compressions.' },
      wheel_config: { position_degrees: 180, phase: 'cpr_loop', animation: 'pulse' },
      local_timer: { enabled: true, type: 'metronome', bpm: 110, guidance: 'Push hard and fast' },
      checklist: [],
      transitions: { type: 'linear', next_id: 'CARD_08_LOOP_BREATHS' },
    },
    {
      id: 'CARD_08_LOOP_BREATHS',
      type: 'action',
      content: { title: '2 Rescue Breaths', body: 'Deliver 2 effective breaths.' },
      wheel_config: { position_degrees: 200, phase: 'cpr_loop' },
      checklist: [],
      transitions: { type: 'linear', next_id: 'CARD_09_LOOP_CHECK' },
    },
    {
      id: 'CARD_09_LOOP_CHECK',
      type: 'decision',
      content: { title: 'Re-assess', body: 'Are there clear signs of life?' },
      wheel_config: { position_degrees: 220, phase: 'cpr_loop' },
      checklist: [],
      transitions: {
        type: 'split',
        options: [
          { label: 'NO', preview_card_title: 'Resume Compressions', target_id: 'CARD_07_COMPRESSIONS' },
          { label: 'YES', preview_card_title: 'Recovery Position', target_id: 'CARD_END_RECOVERY' },
        ],
      },
    },
    {
      id: 'CARD_END_RECOVERY',
      type: 'terminal',
      content: { title: 'Stabilised', body: 'Keep child in safe position, continue to assess and await EMS.' },
      wheel_config: { position_degrees: 60, phase: 'complete' },
      checklist: [],
      transitions: null,
      status: 'complete',
    },
  ],
};

const PHASE_ANCHOR_RATIO: Record<string, number> = {
  start_point: 0.0,
  assessment: 0.12,
  action: 0.28,
  decision: 0.45,
  intervention: 0.62,
  check: 0.76,
  loop: 0.88,
  cpr_loop: 0.88,
  complete: 1.0,
};

const DEFAULT_WHEEL_ARC: WheelArc = {
  start_degrees: 330,
  end_degrees: 30,
  direction: 'anticlockwise',
  phase_spread_degrees: 4,
};

export const DEFAULT_ALGORITHM_FILES = [
  'algo_paed_bls_out.json',
  'algo_paed_bls_in.json',
  'algo_newborn_ls.json',
  'algo_anaphylaxis.json',
  'algo_paed_fbao.json',
];

export function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

export function normalizeDegrees(deg: number): number {
  const n = Number(deg);
  if (!Number.isFinite(n)) return 0;
  const mod = n % 360;
  return mod < 0 ? mod + 360 : mod;
}

export function normalizeWheelArc(rawMeta: AlgorithmMetaLike | null): WheelArc {
  const raw = rawMeta && rawMeta.wheel_arc ? rawMeta.wheel_arc : {} as Record<string, unknown>;
  const direction: 'anticlockwise' | 'clockwise' =
    String((raw as Record<string, unknown>).direction || DEFAULT_WHEEL_ARC.direction).toLowerCase() === 'anticlockwise'
      ? 'anticlockwise'
      : 'clockwise';
  const startRaw = (raw as Record<string, unknown>).start_degrees;
  const start = Number.isFinite(Number(startRaw))
    ? normalizeDegrees(Number(startRaw))
    : DEFAULT_WHEEL_ARC.start_degrees;
  const endRaw = (raw as Record<string, unknown>).end_degrees;
  const end = Number.isFinite(Number(endRaw))
    ? normalizeDegrees(Number(endRaw))
    : DEFAULT_WHEEL_ARC.end_degrees;
  const spreadRaw = (raw as Record<string, unknown>).phase_spread_degrees;
  const spread = Number.isFinite(Number(spreadRaw))
    ? Math.max(0, Number(spreadRaw))
    : DEFAULT_WHEEL_ARC.phase_spread_degrees;
  return { start_degrees: start, end_degrees: end, direction, phase_spread_degrees: spread };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AlgorithmMetaLike = Record<string, any>;

function angleOnArc(arc: WheelArc, ratio: number): number {
  const t = Math.max(0, Math.min(1, Number(ratio)));
  const cwDistance = (arc.end_degrees - arc.start_degrees + 360) % 360;
  const ccwDistance = (arc.start_degrees - arc.end_degrees + 360) % 360;
  if (arc.direction === 'anticlockwise') {
    return normalizeDegrees(arc.start_degrees - ccwDistance * t);
  }
  return normalizeDegrees(arc.start_degrees + cwDistance * t);
}

function inferPhase(card: Card): string {
  const explicit = card && card.wheel_config && card.wheel_config.phase
    ? String(card.wheel_config.phase).trim()
    : '';
  if (explicit) {
    if (explicit === 'cpr_loop') return 'loop';
    return explicit;
  }
  if (!card || !card.type) return 'action';
  if (card.type === 'cover') return 'start_point';
  if (card.type === 'decision') return 'decision';
  if (card.type === 'terminal') return 'complete';
  if (card.type === 'loop_start') return 'loop';
  return 'action';
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeTransitions(card: any, index: number, cards: any[]): Transition | null {
  const raw = card && card.transitions ? card.transitions : null;
  const isTerminalLike = card
    && (card.type === 'terminal'
      || card.status === 'complete'
      || card.status === 'handoff');

  if (!raw) {
    if (isTerminalLike) return null;
    const nextCard = cards[index + 1];
    return nextCard ? { type: 'linear', next_id: nextCard.id } : null;
  }

  if (raw.type === 'split' && Array.isArray(raw.options)) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const options = raw.options
      .filter((opt: any) => opt && opt.target_id)
      .map((opt: any, idx: number) => ({
        label: (opt.label as string) || `Option ${idx + 1}`,
        sub_label: (opt.sub_label as string) || null,
        preview_card_title: (opt.preview_card_title as string) || null,
        target_id: String(opt.target_id),
      }));
    if (options.length > 0) return { type: 'split', options };
  }

  if (raw.type === 'self_loop') {
    return {
      type: 'self_loop',
      next_id: raw.next_id ? String(raw.next_id) : String(card.id),
    };
  }

  const linearNext = raw.next_id
    ? String(raw.next_id)
    : (!isTerminalLike && cards[index + 1] ? String(cards[index + 1].id) : null);
  if (linearNext) {
    return { type: 'linear', next_id: linearNext };
  }

  return null;
}

function derivePositionDegrees(cards: Card[], arc: WheelArc): void {
  const byPhase: Record<string, string[]> = {};
  cards.forEach((card) => {
    const phase = card.wheel_config.phase!;
    if (!byPhase[phase]) byPhase[phase] = [];
    byPhase[phase].push(card.id);
  });

  const phaseIndex: Record<string, { idx: number; count: number }> = {};
  for (const [, ids] of Object.entries(byPhase)) {
    ids.forEach((id, idx) => {
      phaseIndex[id] = { idx, count: ids.length };
    });
  }

  cards.forEach((card) => {
    const rawPos = card.wheel_config && typeof card.wheel_config.position_degrees === 'number'
      ? card.wheel_config.position_degrees
      : null;
    if (rawPos != null) {
      card.wheel_config.position_degrees = normalizeDegrees(rawPos);
      return;
    }

    const phase = card.wheel_config.phase!;
    const ratio = Object.prototype.hasOwnProperty.call(PHASE_ANCHOR_RATIO, phase)
      ? PHASE_ANCHOR_RATIO[phase]
      : PHASE_ANCHOR_RATIO.action;
    const anchor = angleOnArc(arc, ratio);
    const placement = phaseIndex[card.id] || { idx: 0, count: 1 };
    const spread = arc.phase_spread_degrees;
    const localOffset = placement.count <= 1
      ? 0
      : ((placement.idx / (placement.count - 1)) - 0.5) * spread;
    const signedOffset = arc.direction === 'anticlockwise' ? -localOffset : localOffset;
    card.wheel_config.position_degrees = normalizeDegrees(anchor + signedOffset);
  });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeAlgorithm(rawAlgorithm: any): Algorithm {
  const raw = rawAlgorithm && typeof rawAlgorithm === 'object' ? rawAlgorithm : deepClone(DEFAULT_ALGORITHM);
  const meta = raw.algorithm_meta && typeof raw.algorithm_meta === 'object'
    ? deepClone(raw.algorithm_meta)
    : {};
  const arc = normalizeWheelArc(meta);
  const rawDeck = Array.isArray(raw.deck) ? raw.deck : [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cards: Card[] = rawDeck
    .filter((card: Record<string, unknown>) => card && typeof card === 'object' && card.id)
    .map((card: Record<string, unknown>) => ({
      ...deepClone(card),
      id: String(card.id),
      content: card.content && typeof card.content === 'object' ? deepClone(card.content) : { title: String(card.id), body: '' },
      checklist: Array.isArray(card.checklist) ? deepClone(card.checklist) : [],
      wheel_config: card.wheel_config && typeof card.wheel_config === 'object' ? deepClone(card.wheel_config) : {},
    } as Card));

  cards.forEach((card, idx) => {
    card.wheel_config.phase = inferPhase(card);
    card.transitions = normalizeTransitions(card, idx, cards);
  });
  derivePositionDegrees(cards, arc);

  meta.wheel_arc = arc;
  return {
    algorithm_meta: meta,
    deck: cards,
  };
}

export function sanitizeAlgorithmFile(value: string | null | undefined): string | null {
  const text = String(value || '').trim();
  if (!text) return null;
  if (!/^[a-zA-Z0-9._-]+\.json$/.test(text)) return null;
  return text;
}

export async function discoverAvailableAlgorithmFiles(): Promise<string[]> {
  try {
    const res = await fetch('algorithms/index.json', { cache: 'no-store' });
    if (!res.ok) return [...DEFAULT_ALGORITHM_FILES];
    const payload = await res.json();
    if (!payload || !Array.isArray(payload.algorithms)) return [...DEFAULT_ALGORITHM_FILES];
    const files = payload.algorithms
      .map((row: Record<string, unknown>) => sanitizeAlgorithmFile(row && (row.file as string)))
      .filter(Boolean) as string[];
    if (files.length === 0) return [...DEFAULT_ALGORITHM_FILES];
    return Array.from(new Set(files));
  } catch {
    return [...DEFAULT_ALGORITHM_FILES];
  }
}

export async function loadAlgorithmByFileName(fileName: string): Promise<unknown> {
  const safe = sanitizeAlgorithmFile(fileName);
  if (!safe) throw new Error(`Invalid algorithm file: ${fileName}`);
  const res = await fetch(`algorithms/${safe}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to load algorithms/${safe} (HTTP ${res.status})`);
  return res.json();
}

export function getDefaultAlgorithm(): Algorithm {
  return deepClone(DEFAULT_ALGORITHM);
}

export { angleOnArc };
