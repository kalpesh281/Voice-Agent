import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSelector } from 'react-redux'
import TranscriptBubble from './TranscriptBubble'

export default function Transcript() {
  const transcript = useSelector((s) => s.voice.transcript)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript.length])

  return (
    <div className="flex-1 overflow-y-auto space-y-3">
      <AnimatePresence initial={false}>
        {transcript.map((msg, i) => (
          <TranscriptBubble key={i} role={msg.role} text={msg.text} timestamp={msg.timestamp} />
        ))}
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
