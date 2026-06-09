// A "playlist" of slides. In the production app this comes from GET /screens/me
// (resolved playlist) and media is cached locally for offline playback — see plan.md (T3).

export interface Slide {
  emoji: string
  title: string
  sub: string
  cls: string // slide theme class s0..s4
}

export const SLIDES: Slide[] = [
  { emoji: '🌸', title: 'Welcome to Olrac Signage', sub: 'Digital Display Platform', cls: 's0' },
  { emoji: '🏖️', title: 'Beach Vibes', sub: 'Demo HD Video · Landscape', cls: 's1' },
  { emoji: '💧', title: "Nature's Beauty", sub: 'Waterfall Series', cls: 's2' },
  { emoji: '🌿', title: 'Fresh & Green', sub: 'Landscape Collection', cls: 's3' },
  { emoji: '❄️', title: 'Winter Escape', sub: 'Snowscape Series', cls: 's4' },
]

export const SLIDE_DURATION = 5000 // ms per slide

// The screen identity the admin assigned at pairing time.
export const SCREEN_NAME = 'Lobby Display'
export const SCREEN_ORIENTATION_DEG = 0 // 0 | 90 | 180 | 270
