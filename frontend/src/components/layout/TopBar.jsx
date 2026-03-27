import { motion } from 'framer-motion'
import { useSelector } from 'react-redux'
import { Radio, Wifi, WifiOff } from 'lucide-react'

export default function TopBar() {
  const client = useSelector((s) => s.client.config)
  const isConnected = useSelector((s) => s.voice.isConnected)
  const status = useSelector((s) => s.voice.status)

  const statusText = {
    idle: 'Ready to connect',
    connecting: 'Connecting...',
    listening: 'Live — Listening',
    thinking: 'Live — Processing',
    agent_speaking: 'Live — Agent speaking',
  }

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="h-14 px-6 flex items-center justify-between border-b border-gray-200 bg-white"
    >
      {/* Left — Branding */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center border border-emerald-200">
          <Radio className="w-4 h-4 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-gray-900">
            {client?.business_name || 'Voice Booking Agent'}
          </h1>
          <p className="text-[10px] text-gray-400 tracking-wider uppercase">
            {client?.category?.replace('_', ' ') || 'Hotel'}
          </p>
        </div>
      </div>

      {/* Right — Connection status */}
      <div className="flex items-center gap-3">
        <motion.div
          animate={{ opacity: isConnected ? 1 : 0.6 }}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-medium border
            ${isConnected
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-gray-50 text-gray-400 border-gray-200'
            }`}
        >
          {isConnected ? (
            <Wifi className="w-3.5 h-3.5" />
          ) : (
            <WifiOff className="w-3.5 h-3.5" />
          )}
          {statusText[status] || 'Ready'}
        </motion.div>
      </div>
    </motion.header>
  )
}
