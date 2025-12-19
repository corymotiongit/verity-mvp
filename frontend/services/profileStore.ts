export type VerityProfile = {
  displayName: string;
  email: string;
  organizationName: string;
};

const STORAGE_KEY = 'verity_profile_v1';

const DEFAULT_PROFILE: VerityProfile = {
  displayName: 'John Doe',
  email: 'john.doe@acme.com',
  organizationName: 'Acme Corp',
};

export function getProfile(): VerityProfile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PROFILE;

    const parsed = JSON.parse(raw) as Partial<VerityProfile>;
    return {
      displayName: parsed.displayName ?? DEFAULT_PROFILE.displayName,
      email: parsed.email ?? DEFAULT_PROFILE.email,
      organizationName: parsed.organizationName ?? DEFAULT_PROFILE.organizationName,
    };
  } catch {
    return DEFAULT_PROFILE;
  }
}

export function setProfile(next: VerityProfile): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent('verity:profile', { detail: next }));
}

export function updateProfile(patch: Partial<VerityProfile>): VerityProfile {
  const current = getProfile();
  const next: VerityProfile = { ...current, ...patch };
  setProfile(next);
  return next;
}

export function computeInitials(displayName: string): string {
  const parts = displayName
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (parts.length === 0) return 'U';
  const first = parts[0][0] ?? '';
  const last = parts.length > 1 ? (parts[parts.length - 1][0] ?? '') : '';
  const initials = (first + last).toUpperCase();
  return initials || 'U';
}
