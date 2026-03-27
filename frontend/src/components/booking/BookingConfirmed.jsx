import { motion } from 'framer-motion'
import { useSelector } from 'react-redux'
import { CheckCircle2, Copy, IndianRupee } from 'lucide-react'
import GlassCard from '../ui/GlassCard'

export default function BookingConfirmed() {
  const booking = useSelector((s) => s.booking.confirmedBooking)

  if (!booking) return null

  const copyRef = () => {
    navigator.clipboard?.writeText(booking.booking_id)
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20 }}
    >
      <GlassCard className="border-accent/30 relative overflow-hidden">
        {/* Success glow background */}
        <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent pointer-events-none" />

        {/* Header */}
        <div className="relative flex items-center gap-3 mb-5">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 300, delay: 0.2 }}
            className="w-12 h-12 rounded-full bg-accent/15 flex items-center justify-center"
          >
            <CheckCircle2 className="w-6 h-6 text-accent" />
          </motion.div>
          <div>
            <h2 className="text-base font-bold text-accent">Booking Confirmed</h2>
            <p className="text-xs text-text-secondary">Your reservation is all set</p>
          </div>
        </div>

        {/* Booking ID */}
        <div className="relative bg-bg-elevated/60 rounded-xl p-3 mb-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-text-muted">Reference</p>
            <p className="text-base font-mono font-bold text-accent mt-0.5">{booking.booking_id}</p>
          </div>
          <button
            onClick={copyRef}
            className="p-2 rounded-lg hover:bg-accent/10 transition-colors"
          >
            <Copy className="w-4 h-4 text-text-muted" />
          </button>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            { label: 'Room', value: booking.resource_name },
            { label: 'Guest', value: booking.customer_name },
            { label: 'Check-in', value: booking.start_date },
            { label: 'Check-out', value: booking.end_date },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
              <p className="text-text-primary font-medium mt-0.5">{value}</p>
            </div>
          ))}
        </div>

        {/* Price */}
        <div className="mt-4 pt-4 border-t border-border-subtle flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-text-muted">Total</p>
            <div className="flex items-baseline gap-1 mt-0.5">
              <IndianRupee className="w-4 h-4 text-accent" />
              <span className="text-xl font-bold text-accent">
                {booking.total_price?.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wider text-text-muted">Advance</p>
            <div className="flex items-baseline gap-1 mt-0.5 justify-end">
              <IndianRupee className="w-3 h-3 text-coral" />
              <span className="text-base font-bold text-coral">
                {booking.token_amount?.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>
      </GlassCard>
    </motion.div>
  )
}
