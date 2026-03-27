import { motion } from 'framer-motion'
import { useSelector } from 'react-redux'
import { MapPin, Bed, Eye, Users, IndianRupee, Sparkles } from 'lucide-react'
import GlassCard from '../ui/GlassCard'
import Badge from '../ui/Badge'

export default function RoomDetails() {
  const room = useSelector((s) => s.booking.selectedRoom)

  if (!room) return null

  return (
    <GlassCard className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <motion.h2
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-lg font-bold text-text-primary"
          >
            {room.name}
          </motion.h2>
          <p className="text-xs text-text-secondary mt-1 flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            Floor {room.floor} · {room.size_sqft} sq ft
          </p>
        </div>
        <Badge color="accent">{room.type}</Badge>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: Bed, label: 'Bed', value: room.bed_type, color: 'text-violet' },
          { icon: Eye, label: 'View', value: room.view, color: 'text-accent' },
          { icon: Users, label: 'Guests', value: `Up to ${room.max_guests}`, color: 'text-coral' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="bg-bg-elevated/60 rounded-xl p-3 text-center">
            <Icon className={`w-4 h-4 mx-auto mb-1 ${color}`} />
            <p className="text-[10px] uppercase tracking-wider text-text-muted">{label}</p>
            <p className="text-sm font-medium text-text-primary capitalize">{value}</p>
          </div>
        ))}
      </div>

      {/* Amenities */}
      {room.amenities?.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-text-muted mb-2 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-accent" />
            Amenities
          </p>
          <div className="flex flex-wrap gap-1.5">
            {room.amenities.map((a, i) => (
              <motion.span
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                className="text-[11px] px-2.5 py-1 rounded-lg bg-bg-elevated/50 text-text-secondary
                  border border-border-subtle"
              >
                {a}
              </motion.span>
            ))}
          </div>
        </div>
      )}

      {/* Price */}
      <div className="flex items-baseline gap-1.5 pt-2 border-t border-border-subtle">
        <IndianRupee className="w-4 h-4 text-accent" />
        <span className="text-2xl font-bold text-accent">
          {room.price_per_night?.toLocaleString('en-IN')}
        </span>
        <span className="text-sm text-text-muted">/night</span>
      </div>

      {/* Description */}
      {room.description && (
        <p className="text-xs text-text-secondary leading-relaxed italic">
          "{room.description}"
        </p>
      )}
    </GlassCard>
  )
}
