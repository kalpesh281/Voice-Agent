import { motion } from 'framer-motion'

export default function GlowButton({ children, onClick, variant = 'primary', disabled = false, className = '' }) {
  const variants = {
    primary: 'bg-accent/20 text-accent border border-accent/30 hover:bg-accent/30 hover:shadow-[0_0_24px_rgba(0,212,170,0.2)]',
    coral: 'bg-coral/20 text-coral border border-coral/30 hover:bg-coral/30 hover:shadow-[0_0_24px_rgba(255,107,107,0.2)]',
    ghost: 'bg-transparent text-text-secondary border border-border-subtle hover:text-text-primary hover:border-accent/20',
  }

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      onClick={onClick}
      disabled={disabled}
      className={`px-5 py-2.5 rounded-xl text-sm font-medium tracking-wide transition-all duration-200
        disabled:opacity-40 disabled:pointer-events-none ${variants[variant]} ${className}`}
    >
      {children}
    </motion.button>
  )
}
