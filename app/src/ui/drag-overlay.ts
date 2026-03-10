// === DRAG OVERLAY CLONE ===
// Uses a visual clone for drag interactions so original cards stay in layout.

export interface DragOverlayOptions {
  className?: string;
  scale?: number;
  zIndex?: number;
}

export interface DragOverlaySession {
  setTransform: (transform: string) => void;
  moveBy: (dx: number, dy: number) => void;
  cleanup: () => void;
}

function resolveHost(): HTMLElement {
  return document.getElementById('app') || document.body;
}

export function createDragOverlay(
  sourceElement: HTMLElement,
  options: DragOverlayOptions = {},
): DragOverlaySession {
  const host = resolveHost();
  const hostRect = host.getBoundingClientRect();
  const sourceRect = sourceElement.getBoundingClientRect();
  const scale = typeof options.scale === 'number' ? options.scale : 1;
  const zIndex = typeof options.zIndex === 'number' ? options.zIndex : 1600;

  const ghost = sourceElement.cloneNode(true) as HTMLElement;
  ghost.style.position = host === document.body ? 'fixed' : 'absolute';
  ghost.style.left = `${sourceRect.left - hostRect.left}px`;
  ghost.style.top = `${sourceRect.top - hostRect.top}px`;
  ghost.style.width = `${sourceRect.width}px`;
  ghost.style.height = `${sourceRect.height}px`;
  ghost.style.margin = '0';
  ghost.style.pointerEvents = 'none';
  ghost.style.zIndex = String(zIndex);
  ghost.style.willChange = 'transform';
  ghost.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';

  if (options.className) {
    ghost.classList.add(options.className);
  }

  sourceElement.style.visibility = 'hidden';
  host.classList.add('drag-overlay-active');
  host.appendChild(ghost);

  const setTransform = (transform: string): void => {
    ghost.style.transform = transform;
  };

  const moveBy = (dx: number, dy: number): void => {
    ghost.style.transform = `translate(${dx}px, ${dy}px) scale(${scale})`;
  };

  moveBy(0, 0);

  const cleanup = (): void => {
    sourceElement.style.visibility = '';
    if (ghost.parentElement) {
      ghost.remove();
    }
    host.classList.remove('drag-overlay-active');
  };

  return {
    setTransform,
    moveBy,
    cleanup,
  };
}
