import { AnimatePresence, motion } from 'framer-motion'
import { useSelector } from 'react-redux'
import { Hotel, Sparkles } from 'lucide-react'
import RoomList from '../booking/RoomList'
import RoomDetails from '../booking/RoomDetails'
import BookingProgress from '../booking/BookingProgress'
import BookingConfirmed from '../booking/BookingConfirmed'
import PriceBreakdown from '../booking/PriceBreakdown'

export default function InfoPanel() {
  const step = useSelector((s) => s.booking.step)
  const client = useSelector((s) => s.client.config)

  return (
    <motion.main
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="flex-1 h-full overflow-y-auto p-8 bg-gray-50/50"
    >
      {/* Booking progress */}
      <BookingProgress />

      {/* Content */}
      <AnimatePresence mode="wait">
        {step === 'idle' && <WelcomeCard key="welcome" businessName={client?.business_name} />}
        {step === 'searching' && <RoomList key="rooms" />}
        {step === 'selected' && <RoomDetails key="details" />}
        {step === 'confirming' && (
          <motion.div key="pricing" className="space-y-5">
            <RoomDetails />
            <PriceBreakdown />
          </motion.div>
        )}
        {step === 'confirmed' && <BookingConfirmed key="confirmed" />}
      </AnimatePresence>
    </motion.main>
  )
}

function WelcomeCard({ businessName }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
      className="max-w-lg mx-auto mt-16 text-center"
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
        className="w-16 h-16 rounded-2xl mx-auto mb-6 bg-emerald-50 flex items-center justify-center border border-emerald-200"
      >
        <Hotel className="w-7 h-7 text-emerald-600" />
      </motion.div>

      <h2 className="text-2xl font-bold text-gray-900 mb-3">
        {businessName || 'Welcome'}
      </h2>
      <p className="text-sm text-gray-500 leading-relaxed max-w-sm mx-auto">
        Start a conversation with our voice agent. Ask about rooms,
        availability, or make a booking — just speak naturally.
      </p>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-8 flex items-center justify-center gap-2 text-xs text-gray-400"
      >
        <Sparkles className="w-3 h-3 text-emerald-500" />
        Powered by AI Voice Agent
      </motion.div>
    </motion.div>
  )
}
