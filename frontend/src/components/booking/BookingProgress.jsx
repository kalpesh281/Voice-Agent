import { motion } from 'framer-motion'
import { useSelector } from 'react-redux'
import { Search, MousePointerClick, ClipboardList, CheckCircle2 } from 'lucide-react'

const steps = [
  { key: 'searching', label: 'Search', icon: Search },
  { key: 'selected', label: 'Select', icon: MousePointerClick },
  { key: 'confirming', label: 'Details', icon: ClipboardList },
  { key: 'confirmed', label: 'Booked', icon: CheckCircle2 },
]

const stepOrder = ['idle', 'searching', 'selected', 'confirming', 'confirmed']

export default function BookingProgress() {
  const step = useSelector((s) => s.booking.step)
  const currentIndex = stepOrder.indexOf(step)

  if (step === 'idle') return null

  return (
    <div className="flex items-center justify-between px-2 py-3">
      {steps.map(({ key, label, icon: Icon }, i) => {
        const stepIdx = stepOrder.indexOf(key)
        const isActive = stepIdx === currentIndex
        const isDone = stepIdx < currentIndex

        return (
          <div key={key} className="flex items-center">
            {/* Step circle */}
            <div className="flex flex-col items-center">
              <motion.div
                animate={{
                  scale: isActive ? 1.15 : 1,
                  backgroundColor: isDone ? '#00D4AA' : isActive ? 'rgba(0,212,170,0.2)' : 'transparent',
                  borderColor: isDone || isActive ? '#00D4AA' : '#3D4566',
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                className="w-9 h-9 rounded-full border-2 flex items-center justify-center"
              >
                <Icon
                  className="w-4 h-4"
                  style={{
                    color: isDone ? '#0B0E17' : isActive ? '#00D4AA' : '#3D4566',
                  }}
                />
              </motion.div>
              <span
                className="text-[9px] mt-1.5 tracking-wider uppercase font-medium"
                style={{ color: isDone || isActive ? '#00D4AA' : '#3D4566' }}
              >
                {label}
              </span>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div className="w-8 h-[2px] mx-1 rounded-full overflow-hidden bg-text-muted/20">
                <motion.div
                  animate={{ width: isDone ? '100%' : '0%' }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                  className="h-full bg-accent rounded-full"
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
