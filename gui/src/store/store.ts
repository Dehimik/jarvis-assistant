import { create } from 'zustand'
import type { JarvisSettings, JarvisStatus } from '@/api/api'

type State = {
  status: JarvisStatus | null
  settings: JarvisSettings | null
}

type Actions = {
  setStatus: (s: JarvisStatus) => void
  setSettings: (s: JarvisSettings) => void
}

export const useJarvisStore = create<State & Actions>((set) => ({
  status: null,
  settings: null,
  setStatus: (status) => set({ status }),
  setSettings: (settings) => set({ settings })
}))