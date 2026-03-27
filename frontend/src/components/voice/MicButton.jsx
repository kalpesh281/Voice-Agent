import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Phone, PhoneOff, Loader2 } from 'lucide-react'
import { useSelector } from 'react-redux'

export default function MicButton({ onConnect, onDisconnect, onMicToggle }) {
  const isMicOn = useSelector((s) => s.voice.isMicOn)
  const isConnected = useSelector((s) => s.voice.isConnected)
  const status = useSelector((s) => s.voice.status)
  const isConnecting = status === 'connecting'

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Main action buttons row */}
      <div className="flex items-center gap-4">
        {/* Mute/Unmute — only visible when connected */}
        {isConnected && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            onClick={onMicToggle}
            className={`w-12 h-12 rounded-full flex items-center justify-center cursor-pointer transition-all duration-200
              ${isMicOn
                ? 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'
                : 'bg-red-50 text-red-500 border border-red-200 hover:bg-red-100'
              }`}
            title={isMicOn ? 'Mute mic' : 'Unmute mic'}
          >
            {isMicOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
          </motion.button>
        )}

        {/* Connect / Disconnect — main button */}
        <div className="relative">
          {/* Pulse rings when connected */}
          <AnimatePresence>
            {isConnected && isMicOn && (
              <>
                <motion.div
                  initial={{ scale: 1, opacity: 0.3 }}
                  animate={{ scale: 2, opacity: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: 'easeOut' }}
                  className="absolute inset-0 rounded-full border-2 border-emerald-400"
                />
                <motion.div
                  initial={{ scale: 1, opacity: 0.2 }}
                  animate={{ scale: 1.6, opacity: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: 'easeOut', delay: 0.3 }}
                  className="absolute inset-0 rounded-full border border-emerald-300"
                />
              </>
            )}
          </AnimatePresence>

          <motion.button
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.92 }}
            transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            onClick={isConnected ? onDisconnect : onConnect}
            disabled={isConnecting}
            className={`relative z-10 w-16 h-16 rounded-full flex items-center justify-center cursor-pointer transition-all duration-200
              ${isConnecting
                ? 'bg-gray-100 text-gray-400 border-2 border-gray-200'
                : isConnected
                  ? 'bg-red-500 text-white shadow-lg shadow-red-200 hover:bg-red-600'
                  : 'bg-emerald-600 text-white shadow-lg shadow-emerald-200 hover:bg-emerald-700'
              }
            `}
          >
            {isConnecting ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : isConnected ? (
              <PhoneOff className="w-6 h-6" />
            ) : (
              <Phone className="w-6 h-6" />
            )}
          </motion.button>
        </div>
      </div>

      {/* Label */}
      <span className="text-xs font-medium text-gray-400 tracking-wide">
        {isConnecting
          ? 'Connecting...'
          : isConnected
            ? isMicOn ? 'Call active — Tap red to end' : 'Mic muted — Tap mic to unmute'
            : 'Tap to start call'
        }
      </span>
    </div>
  )
}
