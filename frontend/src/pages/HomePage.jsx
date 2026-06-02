import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { Radio, Mic, MessageSquare, Rocket, Hotel, UtensilsCrossed, Dumbbell } from 'lucide-react'
import { useEffect } from 'react'

const categories = [
  { icon: Hotel, label: 'Hotels', desc: 'Room booking & concierge' },
  { icon: UtensilsCrossed, label: 'Restaurants', desc: 'Table reservations' },
  { icon: Dumbbell, label: 'Sports & Turf', desc: 'Court & slot booking' },
]

const steps = [
  { num: '01', title: 'Create account', desc: 'Sign up in seconds with your email' },
  { num: '02', title: 'Chat with AI setup', desc: 'Our agent guides you through configuration' },
  { num: '03', title: 'Go live', desc: 'Your AI voice agent is ready for customers' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const { user, loading } = useSelector((s) => s.auth)

  useEffect(() => {
    if (!loading && user) {
      navigate(user.onboarding_complete ? '/dashboard' : '/onboarding', { replace: true })
    }
  }, [user, loading, navigate])

  if (loading) return null

  return (
    <div className="min-h-screen bg-bg-primary overflow-y-auto">
      {/* Navbar */}
      <nav className="h-14 px-6 flex items-center justify-between border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center border border-emerald-200">
            <Radio className="w-4 h-4 text-emerald-600" />
          </div>
          <span className="text-sm font-bold text-gray-900">Voice Booking Agent</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/login')}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors cursor-pointer"
          >
            Sign in
          </button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => navigate('/signup')}
            className="px-4 py-2 rounded-xl text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors cursor-pointer"
          >
            Get started
          </motion.button>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left — Text */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium mb-6">
              <Mic className="w-3.5 h-3.5" />
              AI-Powered Voice Agent
            </div>
            <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 leading-tight mb-5">
              Your business.{' '}
              <span className="text-emerald-600">Your AI voice agent.</span>{' '}
              60-second setup.
            </h1>
            <p className="text-lg text-gray-500 mb-8 max-w-lg">
              Let customers book rooms, tables, and courts through natural phone conversations.
              No buttons, no typing — just talking.
            </p>
            <div className="flex items-center gap-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate('/signup')}
                className="px-6 py-3 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-lg shadow-emerald-200 transition-all cursor-pointer"
              >
                Get started free
              </motion.button>
              <button
                onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-6 py-3 rounded-xl text-sm font-medium text-gray-600 border border-gray-200 hover:border-emerald-200 hover:text-emerald-700 transition-all cursor-pointer"
              >
                See how it works
              </button>
            </div>
          </motion.div>

          {/* Right — Visual */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="relative"
          >
            <div className="glass p-8 relative overflow-hidden">
              {/* Mock orb */}
              <div className="flex justify-center mb-6">
                <div className="relative">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-200">
                    <Mic className="w-10 h-10 text-white" />
                  </div>
                  <motion.div
                    animate={{ scale: [1, 1.4, 1], opacity: [0.3, 0, 0.3] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    className="absolute inset-0 rounded-full border-2 border-emerald-400"
                  />
                </div>
              </div>

              {/* Mock transcript */}
              <div className="space-y-3">
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 }}
                  className="flex gap-2"
                >
                  <div className="bg-emerald-50 border border-emerald-100 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm text-gray-700 max-w-[280px]">
                    Welcome to The Grand Meridian! I'm Aria, how can I help you today?
                  </div>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 1 }}
                  className="flex justify-end"
                >
                  <div className="bg-gray-100 border border-gray-200 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-gray-700 max-w-[240px]">
                    I'd like to book a deluxe room for two nights
                  </div>
                </motion.div>
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 1.5 }}
                  className="flex gap-2"
                >
                  <div className="bg-emerald-50 border border-emerald-100 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm text-gray-700 max-w-[280px]">
                    I found 3 deluxe rooms available. The best one is at ₹4,500/night with a sea view!
                  </div>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="max-w-4xl mx-auto px-6 py-16">
        <motion.h2
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-2xl font-bold text-gray-900 text-center mb-12"
        >
          Up and running in 3 steps
        </motion.h2>
        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15 }}
              className="glass p-6 text-center"
            >
              <div className="text-3xl font-bold text-emerald-600/20 mb-3">{step.num}</div>
              <h3 className="text-sm font-semibold text-gray-900 mb-1.5">{step.title}</h3>
              <p className="text-xs text-gray-500">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Categories */}
      <section className="max-w-4xl mx-auto px-6 py-12 pb-20">
        <h2 className="text-xl font-bold text-gray-900 text-center mb-8">Works for any booking business</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {categories.map((cat, i) => (
            <motion.div
              key={cat.label}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass p-5 flex items-center gap-4"
            >
              <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center shrink-0">
                <cat.icon className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">{cat.label}</h3>
                <p className="text-xs text-gray-500">{cat.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  )
}
