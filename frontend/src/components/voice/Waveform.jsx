import { motion } from 'framer-motion'
import { useSelector } from 'react-redux'

export default function Waveform() {
  const waveformData = useSelector((s) => s.voice.waveformData)
  const status = useSelector((s) => s.voice.status)
  const isActive = status === 'listening' || status === 'agent_speaking'

  return (
    <div className="flex items-end justify-center gap-[3px] h-12 px-6 my-2">
      {waveformData.map((value, i) => {
        const height = Math.max(4, value * 44)
        const center = Math.abs(i - 20)
        const color = center < 8 ? '#059669' : '#7C3AED'
        const opacity = isActive ? 0.35 + value * 0.65 : 0.12

        return (
          <motion.div
            key={i}
            animate={{ height }}
            transition={{ type: 'spring', stiffness: 300, damping: 18 }}
            style={{
              width: 3,
              minHeight: 4,
              borderRadius: 2,
              backgroundColor: color,
              opacity,
            }}
          />
        )
      })}
    </div>
  )
}
