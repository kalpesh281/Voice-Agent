import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSelector, useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { Send, Radio, Loader2, CheckCircle2, Sparkles } from 'lucide-react'
import { setSessionId, resetOnboarding } from '../features/onboarding/onboardSlice'
import { fetchMe } from '../features/auth/authSlice'
import useOnboardingSocket from '../hooks/useOnboardingSocket'

export default function OnboardingPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { messages, sessionId, status, collectedConfig, clientId } = useSelector((s) => s.onboard)
  const user = useSelector((s) => s.auth.user)

  const [input, setInput] = useState('')
  const [waiting, setWaiting] = useState(false) // true while waiting for bot reply
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Generate session ID on mount
  useEffect(() => {
    if (!sessionId) {
      dispatch(setSessionId(crypto.randomUUID?.() || Date.now().toString()))
    }
  }, [sessionId, dispatch])

  const { connect, disconnect, sendMessage } = useOnboardingSocket(sessionId)

  // Auto-connect once when session ID is ready
  const hasConnected = useRef(false)
  useEffect(() => {
    if (sessionId && !hasConnected.current) {
      hasConnected.current = true
      connect()
    }
    return () => disconnect()
  }, [sessionId, connect, disconnect])

  // Auto-scroll to bottom on new messages
  const scrollContainerRef = useRef(null)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight
      }
    }, 50)
    return () => clearTimeout(timer)
  }, [messages.length])

  // On complete, refresh auth and redirect
  useEffect(() => {
    if (status === 'complete' && clientId) {
      const timer = setTimeout(async () => {
        await dispatch(fetchMe())
        navigate('/dashboard', { replace: true })
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [status, clientId, dispatch, navigate])

  const handleSend = () => {
    const text = input.trim()
    if (!text || waiting) return
    sendMessage(text)
    setInput('')
    setWaiting(true)
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
  }

  // Reset waiting when agent replies
  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1]?.role === 'agent') {
      setWaiting(false)
      inputRef.current?.focus()
    }
  }, [messages.length])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Config preview fields
  const previewFields = [
    { label: 'Business', key: 'business_name' },
    { label: 'Category', key: 'business_category' },
    { label: 'Location', key: 'business_location' },
    { label: 'Agent Name', key: 'agent_name' },
    { label: 'Voice', key: 'tts_voice' },
    { label: 'Database', key: 'database_name' },
    { label: 'Collection', key: 'resources_collection' },
  ]

  return (
    <div className="h-screen flex flex-col bg-bg-primary overflow-hidden">
      {/* Top bar */}
      <header className="h-14 px-6 flex items-center justify-between border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center border border-emerald-200">
            <Radio className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-900">Setup Your Agent</h1>
            <p className="text-[10px] text-gray-400 tracking-wider uppercase">Onboarding</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
          AI-guided setup
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat panel — 60% */}
        <div className="flex-[60] flex flex-col border-r border-gray-200 bg-white min-h-0">
          {/* Messages */}
          <div ref={scrollContainerRef} className="flex-1 overflow-y-auto overflow-x-hidden px-6 py-5 space-y-4 scrollbar-hide" style={{ minHeight: 0 }}>
            <AnimatePresence initial={false}>
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words overflow-hidden ${
                      msg.role === 'user'
                        ? 'bg-gray-100 border border-gray-200 rounded-2xl rounded-tr-sm text-gray-800'
                        : 'bg-emerald-50 border border-emerald-100 rounded-2xl rounded-tl-sm text-gray-700'
                    }`}
                  >
                    {msg.text}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Typing indicator when waiting for agent */}
            {waiting && (
              <div className="flex justify-start">
                <div className="bg-emerald-50 border border-emerald-100 rounded-2xl px-4 py-3 flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}

            {/* Completion celebration */}
            {status === 'complete' && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex justify-center py-8"
              >
                <div className="text-center">
                  <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                  <h3 className="text-lg font-bold text-gray-900 mb-1">You're all set!</h3>
                  <p className="text-sm text-gray-500">Redirecting to your dashboard...</p>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="shrink-0 px-6 py-4 border-t border-gray-100 bg-gray-50/50">
            <div className="flex items-end gap-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value)
                  // Auto-resize: reset height then set to scrollHeight
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
                }}
                onKeyDown={handleKeyDown}
                disabled={status === 'complete' || waiting}
                placeholder={status === 'complete' ? 'Setup complete!' : 'Type your reply...'}
                rows={1}
                className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all disabled:opacity-50 resize-none overflow-y-auto"
                style={{ maxHeight: '120px' }}
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  handleSend()
                  // Reset textarea height after send
                  if (inputRef.current) inputRef.current.style.height = 'auto'
                }}
                disabled={!input.trim() || status === 'complete' || waiting}
                className="w-10 h-10 shrink-0 rounded-xl bg-emerald-600 text-white flex items-center justify-center hover:bg-emerald-700 disabled:opacity-40 transition-all cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </motion.button>
            </div>
          </div>
        </div>

        {/* Config preview — 40% */}
        <div className="flex-[40] overflow-y-auto overflow-x-hidden px-6 py-5 bg-bg-primary scrollbar-hide">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass p-6"
          >
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-emerald-50 flex items-center justify-center border border-emerald-200">
                <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              </div>
              Your Agent Config
            </h3>

            <div className="space-y-3">
              {previewFields.map((f) => (
                <div key={f.key} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <span className="text-xs font-medium text-gray-500">{f.label}</span>
                  <span className={`text-sm font-medium ${collectedConfig[f.key] ? 'text-gray-900' : 'text-gray-300'}`}>
                    {collectedConfig[f.key] || '—'}
                  </span>
                </div>
              ))}
            </div>

            {/* Greeting preview */}
            {collectedConfig.greeting_template && (
              <div className="mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-100">
                <p className="text-[10px] text-emerald-600 font-medium uppercase tracking-wider mb-1">Greeting Preview</p>
                <p className="text-sm text-gray-700 italic">"{collectedConfig.greeting_template}"</p>
              </div>
            )}
          </motion.div>

          {/* User info card */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass p-5 mt-4"
          >
            <p className="text-xs text-gray-400 mb-2">Logged in as</p>
            <p className="text-sm font-medium text-gray-900">{user?.full_name || user?.email}</p>
            <p className="text-xs text-gray-500">{user?.email}</p>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
