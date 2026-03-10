// === GLOBAL DRAG LOCK ===
// Guarantees only one drag interaction (zone/decision/etc.) is active at a time.

type DragCancelFn = () => void;

let activeOwner: string | null = null;
let activeCancel: DragCancelFn | null = null;

export function beginDrag(owner: string, cancel: DragCancelFn): void {
  if (activeCancel && activeOwner !== owner) {
    const previousCancel = activeCancel;
    activeOwner = null;
    activeCancel = null;
    previousCancel();
  }
  activeOwner = owner;
  activeCancel = cancel;
}

export function clearDrag(owner: string): void {
  if (activeOwner !== owner) return;
  activeOwner = null;
  activeCancel = null;
}

export function cancelAnyDrag(exceptOwner?: string): void {
  if (!activeCancel) return;
  if (exceptOwner && activeOwner === exceptOwner) return;
  const cancel = activeCancel;
  activeOwner = null;
  activeCancel = null;
  cancel();
}
