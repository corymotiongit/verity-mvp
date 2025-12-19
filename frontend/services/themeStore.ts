export type ThemeMode = 'light' | 'dark';
export type ThemeSetting = ThemeMode | 'system';

const STORAGE_KEY = 'verity_theme_v1';
const EVENT_NAME = 'verity-theme-change';

function isBrowser(): boolean {
  return typeof window !== 'undefined' && typeof document !== 'undefined';
}

export function getTheme(): ThemeMode {
  if (!isBrowser()) return 'dark';

  const stored = getThemeSetting();

  if (stored === 'light' || stored === 'dark') return stored;

  // System preference
  try {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  } catch {
    return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  }
}

export function getThemeSetting(): ThemeSetting {
  if (!isBrowser()) return 'dark';

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;

  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

export function applyTheme(mode: ThemeMode): void {
  if (!isBrowser()) return;

  if (mode === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

export function setTheme(mode: ThemeMode): void {
  if (!isBrowser()) return;

  applyTheme(mode);
  window.localStorage.setItem(STORAGE_KEY, mode);
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { mode, setting: mode } }));
}

export function setThemeSetting(setting: ThemeSetting): void {
  if (!isBrowser()) return;

  window.localStorage.setItem(STORAGE_KEY, setting);
  applyTheme(getTheme());
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { mode: getTheme(), setting } }));
}

export function toggleTheme(): ThemeMode {
  const next: ThemeMode = getTheme() === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next;
}

export function subscribeThemeChanges(callback: (mode: ThemeMode) => void): () => void {
  if (!isBrowser()) return () => {};

  const handler = (event: Event) => {
    const detailMode = (event as CustomEvent)?.detail?.mode;
    if (detailMode === 'light' || detailMode === 'dark') {
      callback(detailMode);
    } else {
      callback(getTheme());
    }
  };

  const storageHandler = (event: StorageEvent) => {
    if (event.key !== STORAGE_KEY) return;
    callback(getTheme());
  };

  window.addEventListener(EVENT_NAME, handler);
  window.addEventListener('storage', storageHandler);

  // React to OS theme changes only when user selected 'system'
  const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  const mediaHandler = () => {
    if (getThemeSetting() !== 'system') return;
    applyTheme(getTheme());
    callback(getTheme());
  };

  try {
    media?.addEventListener?.('change', mediaHandler);
    // Fallback for older browsers
    // @ts-expect-error older Safari
    media?.addListener?.(mediaHandler);
  } catch {}

  return () => {
    window.removeEventListener(EVENT_NAME, handler);
    window.removeEventListener('storage', storageHandler);

    try {
      media?.removeEventListener?.('change', mediaHandler);
      // @ts-expect-error older Safari
      media?.removeListener?.(mediaHandler);
    } catch {}
  };
}
