import { motion } from 'framer-motion'
import { useSelector } from 'react-redux'

const stateConfig = {
  idle:           { glowColor: '#D1D5DB', ringColor: '#9CA3AF', speed: 4 },
  listening:      { glowColor: '#059669', ringColor: '#059669', speed: 2.5 },
  thinking:       { glowColor: '#7C3AED', ringColor: '#7C3AED', speed: 1.2 },
  agent_speaking: { glowColor: '#059669', ringColor: '#059669', speed: 1.8 },
  connecting:     { glowColor: '#9CA3AF', ringColor: '#9CA3AF', speed: 2 },
}

export default function AgentOrb() {
  const status = useSelector((s) => s.voice.status)
  const c = stateConfig[status] || stateConfig.idle
  const isActive = status !== 'idle'

  return (
    <div className="relative flex items-center justify-center w-36 h-36 mx-auto">
      {/* Glow pulse */}
      {isActive && (
        <motion.div
          animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0.1, 0.3] }}
          transition={{ duration: c.speed, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute w-28 h-28 rounded-full"
          style={{ backgroundColor: c.glowColor, filter: 'blur(24px)' }}
        />
      )}

      {/* Outer ring */}
      <motion.div
        animate={{
          scale: [1, 1.04, 1],
          rotate: status === 'thinking' ? 360 : 0,
        }}
        transition={{
          scale: { duration: c.speed, repeat: Infinity, ease: 'easeInOut' },
          rotate: status === 'thinking' ? { duration: 3, repeat: Infinity, ease: 'linear' } : {},
        }}
        className="absolute w-28 h-28 rounded-full"
        style={{
          border: `2px solid ${c.ringColor}40`,
          boxShadow: isActive ? `0 0 20px ${c.glowColor}25` : 'none',
        }}
      />

      {/* Inner circle */}
      <motion.div
        animate={{ scale: [1, 1.06, 1] }}
        transition={{ duration: c.speed * 0.7, repeat: Infinity, ease: 'easeInOut' }}
        className="relative w-16 h-16 rounded-full flex items-center justify-center"
        style={{
          background: `linear-gradient(135deg, ${c.ringColor}20, ${c.ringColor}08)`,
          border: `2px solid ${c.ringColor}50`,
          boxShadow: isActive ? `0 0 24px ${c.glowColor}20` : '0 2px 8px rgba(0,0,0,0.06)',
        }}
      >
        <motion.div
          animate={{ opacity: isActive ? [0.6, 1, 0.6] : 0.4 }}
          transition={{ duration: 2, repeat: Infinity }}
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: c.ringColor }}
        />
      </motion.div>

      {/* Orbiting dot */}
      {isActive && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: c.speed * 2.5, repeat: Infinity, ease: 'linear' }}
          className="absolute w-30 h-30"
          style={{ width: 120, height: 120 }}
        >
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: c.ringColor, boxShadow: `0 0 6px ${c.ringColor}` }}
          />
        </motion.div>
      )}
    </div>
  )
}
