import { motion } from 'framer-motion'
import { useSelector } from 'react-redux'
import { IndianRupee } from 'lucide-react'
import GlassCard from '../ui/GlassCard'

export default function PriceBreakdown() {
  const availability = useSelector((s) => s.booking.availability)

  if (!availability || !availability.available) return null

  return (
    <GlassCard className="space-y-3">
      <h3 className="text-xs tracking-[0.2em] uppercase text-text-muted font-medium">
        Price Breakdown
      </h3>

      <div className="space-y-2">
        <Row
          label={`${availability.units} ${availability.unit_label} x ${availability.price_per_unit?.toLocaleString('en-IN')}`}
          value={availability.total_price}
        />

        <div className="border-t border-border-subtle my-2" />

        <Row label="Total" value={availability.total_price} bold />
        <Row
          label={`Advance (${availability.token_percentage}%)`}
          value={availability.token_amount}
          color="text-coral"
        />
      </div>
    </GlassCard>
  )
}

function Row({ label, value, bold = false, color = 'text-accent' }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center justify-between"
    >
      <span className={`text-sm ${bold ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
        {label}
      </span>
      <span className={`flex items-center gap-0.5 ${bold ? 'text-base font-bold' : 'text-sm font-medium'} ${color}`}>
        <IndianRupee className="w-3 h-3" />
        {value?.toLocaleString('en-IN')}
      </span>
    </motion.div>
  )
}
