import { useEffect, useState } from 'react';
import { getThemeSetting, subscribeThemeChanges, ThemeSetting } from './themeStore';

export function useThemeSetting(): ThemeSetting {
  const [setting, setSetting] = useState<ThemeSetting>(() => getThemeSetting());

  useEffect(() => {
    // Reuse the theme change event; it is fired for any setting/mode change.
    return subscribeThemeChanges(() => setSetting(getThemeSetting()));
  }, []);

  return setting;
}
