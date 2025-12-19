import { useEffect, useState } from 'react';
import type { VerityProfile } from './profileStore';
import { getProfile } from './profileStore';

export function useProfile(): VerityProfile {
  const [profile, setProfileState] = useState<VerityProfile>(() => getProfile());

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== 'verity_profile_v1') return;
      setProfileState(getProfile());
    };

    const onCustom = (e: Event) => {
      const custom = e as CustomEvent<VerityProfile>;
      if (!custom.detail) {
        setProfileState(getProfile());
        return;
      }
      setProfileState(custom.detail);
    };

    window.addEventListener('storage', onStorage);
    window.addEventListener('verity:profile', onCustom);

    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener('verity:profile', onCustom);
    };
  }, []);

  return profile;
}
