import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSelector } from 'react-redux'
import TranscriptBubble from './TranscriptBubble'

/** Agent-side "…thinking" placeholder: three bouncing dots in a real bubble. */
function TypingBubble() {
  const agentName = useSelector((s) => s.client.config?.agent_name) || 'Agent'
  return (
    <motion.div
      initial={{ opacity: 0, x: -16, y: 6 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ type: 'spring', stiffness: 280, damping: 22 }}
      className="flex flex-col items-start"
    >
      <div className="flex items-center gap-2 mb-1 px-1">
        <span className="text-[10px] font-bold tracking-wider uppercase text-accent">
          {agentName}
        </span>
      </div>
      <div className="px-4 py-3 bg-emerald-50 rounded-2xl rounded-tl-md border border-emerald-100">
        <span className="inline-flex items-center">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
              className="inline-block w-1.5 h-1.5 rounded-full mx-[2px] bg-accent"
            />
          ))}
        </span>
      </div>
    </motion.div>
  )
}

export default function Transcript() {
  const transcript = useSelector((s) => s.voice.transcript)
  const status = useSelector((s) => s.voice.status)
  const bottomRef = useRef(null)

  // Show a typing indicator only while the agent is actually working out its
  // reply (thinking / calling tools). Once it starts speaking, its words stream
  // into a real bubble, so the placeholder is no longer needed.
  const isThinking = status === 'thinking'

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript.length, isThinking])

  return (
    <div className="flex-1 overflow-y-auto space-y-3">
      <AnimatePresence initial={false}>
        {transcript.map((msg, i) => (
          <TranscriptBubble key={i} role={msg.role} text={msg.text} timestamp={msg.timestamp} />
        ))}
        {isThinking && <TypingBubble key="typing" />}
      </AnimatePresence>

      {transcript.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex items-center justify-center h-24 text-gray-300 text-sm"
        >
          Conversation will appear here
        </motion.div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
