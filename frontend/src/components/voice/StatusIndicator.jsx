import { motion, AnimatePresence } from 'framer-motion'
import { useSelector } from 'react-redux'

const config = {
  idle:           { label: 'Ready',       color: '#9CA3AF' },
  connecting:     { label: 'Connecting',  color: '#9CA3AF' },
  listening:      { label: 'Listening',   color: '#059669' },
  thinking:       { label: 'Processing',  color: '#7C3AED' },
  agent_speaking: { label: 'Speaking',    color: '#059669' },
  paused:         { label: 'Paused',      color: '#9CA3AF' },
}

export default function StatusIndicator() {
  const status = useSelector((s) => s.voice.status)
  const { label, color } = config[status] || config.idle
  const isActive = status !== 'idle' && status !== 'paused'

  return (
    <div className="flex items-center gap-2">
      {/* Dot */}
      <div className="relative">
        <motion.div
          animate={{
            scale: isActive ? [1, 1.5, 1] : 1,
            opacity: isActive ? [0.7, 1, 0.7] : 0.5,
          }}
          transition={{ duration: status === 'thinking' ? 0.6 : 1.2, repeat: isActive ? Infinity : 0 }}
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: color }}
        />
        {isActive && (
          <motion.div
            animate={{ scale: [1, 2.5], opacity: [0.3, 0] }}
            transition={{ duration: 1.2, repeat: Infinity }}
            className="absolute inset-0 rounded-full"
            style={{ backgroundColor: color }}
          />
        )}
      </div>

      {/* Label */}
      <AnimatePresence mode="wait">
        <motion.span
          key={status}
          initial={{ opacity: 0, y: 3 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -3 }}
          transition={{ duration: 0.15 }}
          className="text-xs font-semibold tracking-widest uppercase"
          style={{ color }}
        >
          {label}
          {status === 'thinking' && (
            <span className="inline-flex ml-1">
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  animate={{ y: [0, -4, 0] }}
                  transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.12 }}
                  className="inline-block w-1 h-1 rounded-full mx-[1px]"
                  style={{ backgroundColor: color }}
                />
              ))}
            </span>
          )}
        </motion.span>
      </AnimatePresence>
    </div>
  )
}
