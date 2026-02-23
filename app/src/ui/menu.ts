// === 3-DOT MENU ===
import { discoverAvailableAlgorithmFiles, loadAlgorithmByFileName } from '../algorithms/loader';
import { applyAlgorithm, getDom } from '../main';

let menuOpen = false;
let menuEl: HTMLElement | null = null;

function createMenuElement(): HTMLElement {
  const el = document.createElement('div');
  el.id = 'menu-panel';
  el.className = 'menu-panel';
  el.innerHTML = `
    <div class="menu-header">
      <span class="menu-title">Menu</span>
      <button class="menu-close-btn" data-action="close-menu">&times;</button>
    </div>
    <div class="menu-items">
      <button class="menu-item" data-action="select-protocol">
        <span class="menu-item-icon">&#9776;</span>
        Select Protocol
      </button>
      <button class="menu-item" data-action="search-protocol">
        <span class="menu-item-icon">&#128269;</span>
        Search
      </button>
      <button class="menu-item" data-action="open-settings">
        <span class="menu-item-icon">&#9881;</span>
        Settings
      </button>
      <button class="menu-item" data-action="about">
        <span class="menu-item-icon">&#8505;</span>
        About
      </button>
    </div>
    <div id="protocol-list" class="protocol-list" style="display:none;"></div>
    <div id="settings-panel" class="settings-panel-inner" style="display:none;"></div>
  `;
  return el;
}

export function initMenu(): void {
  menuEl = createMenuElement();
  document.getElementById('app')!.appendChild(menuEl);

  // Wire menu button
  const menuBtn = document.querySelector('.header-icon:last-child');
  if (menuBtn) {
    menuBtn.addEventListener('click', toggleMenu);
  }

  // Wire menu actions via delegation
  menuEl.addEventListener('click', (e) => {
    const target = (e.target as HTMLElement).closest('[data-action]') as HTMLElement;
    if (!target) return;

    const action = target.dataset.action;
    if (action === 'close-menu') closeMenu();
    else if (action === 'select-protocol') showProtocolList();
    else if (action === 'search-protocol') showSearch();
    else if (action === 'open-settings') showSettings();
    else if (action === 'about') showAbout();
  });
}

function toggleMenu(): void {
  if (menuOpen) closeMenu();
  else openMenu();
}

function openMenu(): void {
  if (!menuEl) return;
  menuEl.classList.add('open');
  menuOpen = true;
}

function closeMenu(): void {
  if (!menuEl) return;
  menuEl.classList.remove('open');
  menuOpen = false;
  // Reset inner panels
  const protocolList = menuEl.querySelector('#protocol-list') as HTMLElement;
  const settingsPanel = menuEl.querySelector('#settings-panel') as HTMLElement;
  if (protocolList) protocolList.style.display = 'none';
  if (settingsPanel) settingsPanel.style.display = 'none';
}

async function showProtocolList(): Promise<void> {
  if (!menuEl) return;
  const listEl = menuEl.querySelector('#protocol-list') as HTMLElement;
  if (!listEl) return;

  listEl.style.display = 'block';
  listEl.innerHTML = '<div class="loading">Loading protocols...</div>';

  try {
    const res = await fetch('algorithms/index.json', { cache: 'no-store' });
    const data = await res.json();
    const algorithms = data.algorithms || [];

    listEl.innerHTML = algorithms.map((algo: { file: string; title: string; context: string; version: string }) => `
      <button class="protocol-item" data-file="${algo.file}">
        <div class="protocol-title">${algo.title}</div>
        <div class="protocol-meta">${algo.context} &middot; v${algo.version}</div>
      </button>
    `).join('');

    listEl.addEventListener('click', async (e) => {
      const btn = (e.target as HTMLElement).closest('.protocol-item') as HTMLElement;
      if (!btn) return;
      const file = btn.dataset.file;
      if (!file) return;
      try {
        const loaded = await loadAlgorithmByFileName(file);
        applyAlgorithm(loaded, file);
        closeMenu();
      } catch (err) {
        console.error('Failed to load protocol:', err);
      }
    });
  } catch {
    listEl.innerHTML = '<div class="loading">Failed to load protocols</div>';
  }
}

function showSearch(): void {
  // Simple search - filter protocol list
  showProtocolList();
}

function showSettings(): void {
  if (!menuEl) return;
  const settingsEl = menuEl.querySelector('#settings-panel') as HTMLElement;
  if (!settingsEl) return;

  settingsEl.style.display = 'block';
  const currentSize = localStorage.getItem('resus-font-size') || 'medium';
  const currentTheme = localStorage.getItem('resus-theme') || 'light';

  settingsEl.innerHTML = `
    <div class="settings-group">
      <div class="settings-label">Font Size</div>
      <div class="settings-options">
        <button class="settings-btn ${currentSize === 'small' ? 'active' : ''}" data-setting="font-size" data-value="small">Small</button>
        <button class="settings-btn ${currentSize === 'medium' ? 'active' : ''}" data-setting="font-size" data-value="medium">Medium</button>
        <button class="settings-btn ${currentSize === 'large' ? 'active' : ''}" data-setting="font-size" data-value="large">Large</button>
      </div>
    </div>
    <div class="settings-group">
      <div class="settings-label">Theme</div>
      <div class="settings-options">
        <button class="settings-btn ${currentTheme === 'light' ? 'active' : ''}" data-setting="theme" data-value="light">Light</button>
        <button class="settings-btn ${currentTheme === 'dark' ? 'active' : ''}" data-setting="theme" data-value="dark">Dark</button>
        <button class="settings-btn ${currentTheme === 'high-contrast' ? 'active' : ''}" data-setting="theme" data-value="high-contrast">High Contrast</button>
      </div>
    </div>
  `;

  settingsEl.addEventListener('click', (e) => {
    const btn = (e.target as HTMLElement).closest('.settings-btn') as HTMLElement;
    if (!btn) return;

    const setting = btn.dataset.setting;
    const value = btn.dataset.value;
    if (!setting || !value) return;

    if (setting === 'font-size') {
      localStorage.setItem('resus-font-size', value);
      applyFontSize(value);
    } else if (setting === 'theme') {
      localStorage.setItem('resus-theme', value);
      applyTheme(value);
    }

    // Update active state
    const siblings = btn.parentElement?.querySelectorAll('.settings-btn');
    siblings?.forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
  });
}

function showAbout(): void {
  if (!menuEl) return;
  const settingsEl = menuEl.querySelector('#settings-panel') as HTMLElement;
  if (!settingsEl) return;

  settingsEl.style.display = 'block';
  settingsEl.innerHTML = `
    <div class="about-content">
      <h3>Resuscitation Handbook</h3>
      <p>Version 0.2.0</p>
      <p>Digitised hospital wall-chart resuscitation algorithms</p>
      <p class="about-source">Based on Resuscitation Council UK (2021) guidelines</p>
    </div>
  `;
}

// Settings application
const FONT_SCALE: Record<string, string> = {
  small: '0.85',
  medium: '1',
  large: '1.15',
};

function applyFontSize(size: string): void {
  const scale = FONT_SCALE[size] || '1';
  document.documentElement.style.setProperty('--font-scale', scale);
}

function applyTheme(theme: string): void {
  const root = document.documentElement;
  root.removeAttribute('data-theme');
  if (theme !== 'light') {
    root.setAttribute('data-theme', theme);
  }
}

// Apply saved settings on load
export function applySavedSettings(): void {
  const size = localStorage.getItem('resus-font-size') || 'medium';
  const theme = localStorage.getItem('resus-theme') || 'light';
  applyFontSize(size);
  applyTheme(theme);
}
