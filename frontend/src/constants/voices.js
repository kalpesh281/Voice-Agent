// Curated Deepgram Aura-2 voice catalog — the single source of truth for the
// voice picker in both Onboarding and Settings. Aura-2 voices use the
// `aura-2-<name>-en` model id; switching is a one-string change for the worker.
// (Full catalog is larger; this is a hand-picked, balanced shortlist.)

export const DEFAULT_VOICE = 'aura-2-thalia-en'

export const VOICE_OPTIONS = [
  // Female
  { value: 'aura-2-thalia-en', label: 'Thalia — Clear & energetic (Female)' },
  { value: 'aura-2-luna-en', label: 'Luna — Friendly & natural (Female)' },
  { value: 'aura-2-athena-en', label: 'Athena — Calm & professional (Female)' },
  { value: 'aura-2-hera-en', label: 'Hera — Smooth & warm (Female)' },
  { value: 'aura-2-cora-en', label: 'Cora — Smooth & caring (Female)' },
  { value: 'aura-2-aurora-en', label: 'Aurora — Cheerful & expressive (Female)' },
  // Male
  { value: 'aura-2-apollo-en', label: 'Apollo — Confident & casual (Male)' },
  { value: 'aura-2-orion-en', label: 'Orion — Calm & approachable (Male)' },
  { value: 'aura-2-arcas-en', label: 'Arcas — Natural & smooth (Male)' },
  { value: 'aura-2-zeus-en', label: 'Zeus — Deep & trustworthy (Male)' },
  { value: 'aura-2-draco-en', label: 'Draco — Warm baritone (Male)' },
]
