// === WHEEL PHYSICS ===
import type { WheelArc } from '../types';
import { normalizeDegrees, normalizeWheelArc } from '../algorithms/loader';
import { state, RUNTIME_ALGORITHM } from '../state/store';
import { getDom } from '../main';

export let WHEEL_RADIUS = 150;
export let KNOB_OFFSET = 15;
export const NAV_THRESHOLD_DEG = 10;

export function updateDimensions(): void {
  const style = getComputedStyle(document.documentElement);
  WHEEL_RADIUS = parseInt(style.getPropertyValue('--wheel-radius')) || 150;
  const knobSize = parseInt(style.getPropertyValue('--knob-size')) || 30;
  KNOB_OFFSET = knobSize / 2;

  if (state.wheel && typeof state.wheel.angle === 'number') {
    setKnobPosition(state.wheel.angle);
  }
}

export function degToPosition(deg: number): { x: number; y: number } {
  const mathDeg = deg - 90;
  const rad = mathDeg * (Math.PI / 180);
  return {
    x: WHEEL_RADIUS + WHEEL_RADIUS * Math.cos(rad) - KNOB_OFFSET,
    y: WHEEL_RADIUS + WHEEL_RADIUS * Math.sin(rad) - KNOB_OFFSET,
  };
}

export function setKnobPosition(deg: number): void {
  const dom = getDom();
  if (!dom.knob) return;

  if (typeof state.wheel.visualAngle === 'undefined') {
    state.wheel.visualAngle = deg;
  }

  const targetDeg = normalizeDegrees(deg);
  const lastVisual = state.wheel.visualAngle;
  const normalizedLast = normalizeDegrees(lastVisual);

  let diff = targetDeg - normalizedLast;
  if (diff > 180) diff -= 360;
  if (diff < -180) diff += 360;

  const newVisual = lastVisual + diff;
  state.wheel.visualAngle = newVisual;

  dom.knob.style.transform = `rotate(${newVisual}deg) translateY(-${WHEEL_RADIUS}px) rotate(-${newVisual}deg)`;
}

// Wrap-safe delta between two angles
export function angleDelta(fromDeg: number, toDeg: number): number {
  let delta = fromDeg - toDeg;
  if (delta > 180) delta -= 360;
  if (delta < -180) delta += 360;
  return delta;
}

export function getCurrentWheelArc(): WheelArc {
  const meta = RUNTIME_ALGORITHM && RUNTIME_ALGORITHM.algorithm_meta
    ? RUNTIME_ALGORITHM.algorithm_meta
    : null;
  return normalizeWheelArc(meta as Record<string, unknown> | null);
}

export function isAngleWithinArc(angle: number, arc: WheelArc): boolean {
  const deg = normalizeDegrees(angle);
  if (arc.direction === 'anticlockwise') {
    const ccwDistance = (arc.start_degrees - arc.end_degrees + 360) % 360;
    const ccwFromStart = (arc.start_degrees - deg + 360) % 360;
    return ccwFromStart <= ccwDistance;
  }
  const cwDistance = (arc.end_degrees - arc.start_degrees + 360) % 360;
  const cwFromStart = (deg - arc.start_degrees + 360) % 360;
  return cwFromStart <= cwDistance;
}

export function shortestAngularDistance(a: number, b: number): number {
  const nA = normalizeDegrees(a);
  const nB = normalizeDegrees(b);
  const diff = Math.abs(nA - nB);
  return Math.min(diff, 360 - diff);
}

export function clampAngleToArc(angle: number, arc: WheelArc): number {
  const deg = normalizeDegrees(angle);
  if (isAngleWithinArc(deg, arc)) return deg;
  const startDist = shortestAngularDistance(deg, arc.start_degrees);
  const endDist = shortestAngularDistance(deg, arc.end_degrees);
  return startDist <= endDist ? arc.start_degrees : arc.end_degrees;
}

export function canonicalAngleForCard(card: { wheel_config?: { position_degrees?: number } } | null, fallbackAngle: number): number {
  if (card && card.wheel_config && typeof card.wheel_config.position_degrees === 'number') {
    return card.wheel_config.position_degrees;
  }
  return typeof fallbackAngle === 'number' ? fallbackAngle : 330;
}
