import { motion, AnimatePresence } from 'framer-motion'
import { useSelector } from 'react-redux'
import RoomCard from './RoomCard'

export default function RoomList() {
  const searchResults = useSelector((s) => s.booking.searchResults)

  if (searchResults.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-3"
    >
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-xs tracking-[0.2em] uppercase text-text-muted font-medium">
          Available Rooms
        </h2>
        <span className="text-xs text-text-muted">
          {searchResults.length} found
        </span>
      </div>

      <AnimatePresence>
        <div className="grid gap-3">
          {searchResults.map((room, i) => (
            <RoomCard key={room.id || i} room={room} index={i} />
          ))}
        </div>
      </AnimatePresence>
    </motion.div>
  )
}
