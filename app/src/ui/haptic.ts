// === HAPTIC FEEDBACK ===
export function triggerHaptic(ms: number): void {
  if (navigator.vibrate) navigator.vibrate(ms);
}
