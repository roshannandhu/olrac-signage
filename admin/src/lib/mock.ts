import type { Media, Screen, Website } from '../types'

// Demo content seeded on first load — mirrors the demo library in admin.html.
export const seedMedia: Media[] = [
  { id: 'm1', name: 'Demo HD vertical video (flowers)', type: 'Video', orient: 'portrait', dur: '0:20', ico: '🌸', bg: '#FDF2F8' },
  { id: 'm2', name: 'Demo HD video (beach)', type: 'Video', orient: 'landscape', dur: '0:08', ico: '🏖️', bg: '#EFF6FF' },
  { id: 'm3', name: 'Demo HD video (waterfall)', type: 'Video', orient: 'landscape', dur: '0:15', ico: '💧', bg: '#F0FDF4' },
  { id: 'm4', name: 'Demo landscape image (grass)', type: 'Image', orient: 'landscape', dur: null, ico: '🌿', bg: '#F0FDF4' },
  { id: 'm5', name: 'Demo HD video (snowscape)', type: 'Video', orient: 'landscape', dur: '0:20', ico: '❄️', bg: '#EFF6FF' },
  { id: 'm6', name: 'Demo portrait image (trees)', type: 'Image', orient: 'portrait', dur: null, ico: '🌳', bg: '#F7FEE7' },
]

export const seedScreens: Screen[] = [
  { id: 's1', name: 'Lobby Display', status: 'online', lastSeen: 'Few seconds ago', orientLabel: 'Landscape', deg: 0, description: 'For testing purposes' },
  { id: 's2', name: 'Reception Screen', status: 'online', lastSeen: '2 min ago', orientLabel: 'Portrait', deg: 90 },
  { id: 's3', name: 'Cafeteria Board', status: 'offline', lastSeen: '3 hours ago', orientLabel: 'Landscape', deg: 0 },
]

export const seedWebsites: Website[] = [
  { id: 'w1', name: 'olrac', addedAt: '2 hours ago' },
]
