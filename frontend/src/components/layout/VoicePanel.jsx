import { motion } from 'framer-motion'
import AgentOrb from '../voice/AgentOrb'
import Waveform from '../voice/Waveform'
import MicButton from '../voice/MicButton'
import StatusIndicator from '../voice/StatusIndicator'
import Transcript from '../voice/Transcript'

export default function VoicePanel({ onConnect, onDisconnect, onMicToggle }) {
  return (
    <motion.aside
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
      className="w-[420px] min-w-[380px] h-full flex flex-col border-r border-gray-200 bg-white"
    >
      {/* Top: Orb + Waveform + Status */}
      <div className="pt-6 pb-2 flex flex-col items-center shrink-0 border-b border-gray-100">
        <AgentOrb />
        <Waveform />
        <div className="mt-1 mb-4">
          <StatusIndicator />
        </div>
      </div>

      {/* Middle: Transcript */}
      <div className="flex-1 overflow-y-auto px-5 py-4 min-h-0">
        <Transcript />
      </div>

      {/* Bottom: Controls */}
      <div className="shrink-0 py-6 pb-8 flex flex-col items-center border-t border-gray-100 bg-gray-50/50">
        <MicButton
          onConnect={onConnect}
          onDisconnect={onDisconnect}
          onMicToggle={onMicToggle}
        />
      </div>
    </motion.aside>
  )
}
