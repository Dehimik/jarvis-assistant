import { ReactNode } from 'react'

export default function Card({ children, className = '' }: { children: ReactNode, className?: string }) {
  return (
    <div className={`rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4 ${className}`}>{children}</div>
  )
}