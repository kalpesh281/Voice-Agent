export default function Badge({ children, color = 'accent' }) {
  const colors = {
    accent: 'bg-accent/15 text-accent border-accent/20',
    violet: 'bg-violet/15 text-violet border-violet/20',
    coral: 'bg-coral/15 text-coral border-coral/20',
    muted: 'bg-bg-elevated text-text-secondary border-border-subtle',
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium
      tracking-wider uppercase border ${colors[color]}`}>
      {children}
    </span>
  )
}
