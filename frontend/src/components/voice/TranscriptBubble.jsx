import { motion } from 'framer-motion'

export default function TranscriptBubble({ role, text, timestamp }) {
  const isUser = role === 'user'
  const time = new Date(timestamp).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 16 : -16, y: 6 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ type: 'spring', stiffness: 280, damping: 22 }}
      className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
    >
      <div className="flex items-center gap-2 mb-1 px-1">
        <span className={`text-[10px] font-bold tracking-wider uppercase ${isUser ? 'text-violet' : 'text-accent'}`}>
          {isUser ? 'You' : 'Aria'}
        </span>
        <span className="text-[10px] text-gray-300">{time}</span>
      </div>

      <div
        className={`max-w-[88%] px-4 py-2.5 text-[13px] leading-relaxed
          ${isUser
            ? 'bg-violet/8 text-gray-800 rounded-2xl rounded-tr-md border border-violet/15'
            : 'bg-emerald-50 text-gray-800 rounded-2xl rounded-tl-md border border-emerald-100'
          }
        `}
      >
        {text}
      </div>
    </motion.div>
  )
}
