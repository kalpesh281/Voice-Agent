import { motion } from 'framer-motion'

export default function GlassCard({ children, className = '', hover = true, ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={hover ? {
        borderColor: 'rgba(0, 212, 170, 0.3)',
        boxShadow: '0 8px 40px rgba(0, 212, 170, 0.08)',
        transition: { duration: 0.25 },
      } : undefined}
      className={`glass p-5 ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  )
}
