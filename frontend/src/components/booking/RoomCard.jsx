import { motion } from 'framer-motion'
import { Bed, Eye, Users, IndianRupee } from 'lucide-react'
import Badge from '../ui/Badge'

export default function RoomCard({ room, index = 0 }) {
  const available = room.available !== false

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, type: 'spring', stiffness: 200, damping: 20 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={`glass p-4 cursor-pointer group ${!available ? 'opacity-50' : ''}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors">
            {room.name}
          </h3>
          <p className="text-[11px] text-text-muted mt-0.5 uppercase tracking-wider">
            Floor {room.floor} · {room.size_sqft} sq ft
          </p>
        </div>
        <Badge color={available ? 'accent' : 'muted'}>
          {available ? 'Available' : 'Booked'}
        </Badge>
      </div>

      {/* Details row */}
      <div className="flex items-center gap-4 text-[12px] text-text-secondary mb-3">
        <span className="flex items-center gap-1">
          <Bed className="w-3.5 h-3.5 text-violet" />
          {room.bed_type}
        </span>
        <span className="flex items-center gap-1">
          <Eye className="w-3.5 h-3.5 text-accent" />
          {room.view}
        </span>
        <span className="flex items-center gap-1">
          <Users className="w-3.5 h-3.5 text-text-muted" />
          {room.max_guests}
        </span>
      </div>

      {/* Price */}
      <div className="flex items-baseline gap-1">
        <IndianRupee className="w-3.5 h-3.5 text-accent" />
        <span className="text-lg font-bold text-accent">
          {room.price_per_night?.toLocaleString('en-IN')}
        </span>
        <span className="text-[11px] text-text-muted">/night</span>
      </div>
    </motion.div>
  )
}
