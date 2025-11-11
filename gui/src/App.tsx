import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from '@/pages/Dashboard'
import Settings from '@/pages/Settings'
import Logs from '@/pages/Logs'
import Intents from '@/pages/Intents'
import About from "@/pages/About.tsx";
import Statistics from "@/pages/Statistics.tsx";

export default function App() {
  return (
    <div className="min-h-screen grid grid-cols-[240px_1fr]">
      <aside className="p-4 border-r border-zinc-800">
        <h1 className="text-xl font-bold mb-6">Jarvis</h1>
        <nav className="flex flex-col gap-2">
          <NavLink to="/" end className={({isActive})=>`px-3 py-2 rounded ${isActive? 'bg-zinc-800' : 'hover:bg-zinc-800/50'}`}>Dashboard</NavLink>
          <NavLink to="/settings" className={({isActive})=>`px-3 py-2 rounded ${isActive? 'bg-zinc-800' : 'hover:bg-zinc-800/50'}`}>Settings</NavLink>
          <NavLink to="/statistics" className={({isActive})=>`px-3 py-2 rounded ${isActive? 'bg-zinc-800' : 'hover:bg-zinc-800/50'}`}>Statistics</NavLink>
          <NavLink to="/logs" className={({isActive})=>`px-3 py-2 rounded ${isActive? 'bg-zinc-800' : 'hover:bg-zinc-800/50'}`}>Logs</NavLink>
          <NavLink to="/intents" className={({isActive})=>`px-3 py-2 rounded ${isActive? 'bg-zinc-800' : 'hover:bg-zinc-800/50'}`}>Intents</NavLink>
          <NavLink to="/about" className={({isActive})=>`px-3 py-2 rounded ${isActive? 'bg-zinc-800' : 'hover:bg-zinc-800/50'}`}>About</NavLink>
        </nav>
      </aside>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/statistics" element={<Statistics />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/intents" element={<Intents />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
    </div>
  )
}