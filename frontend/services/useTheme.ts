import { useEffect, useState } from 'react';
import { getTheme, subscribeThemeChanges, ThemeMode } from './themeStore';

export function useTheme(): ThemeMode {
  const [mode, setMode] = useState<ThemeMode>(() => getTheme());

  useEffect(() => {
    return subscribeThemeChanges(setMode);
  }, []);

  return mode;
}
