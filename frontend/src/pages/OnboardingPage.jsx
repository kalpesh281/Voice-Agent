import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSelector, useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { Send, Radio, Loader2, CheckCircle2, Sparkles, Play, Square, Rocket, Edit3, XCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { setSessionId, resetOnboarding, setConfirmError } from '../features/onboarding/onboardSlice'
import { fetchMe } from '../features/auth/authSlice'
import useOnboardingSocket from '../hooks/useOnboardingSocket'
import { VOICE_OPTIONS, DEFAULT_VOICE } from '../constants/voices'

function cleanGreeting(raw) {
  return (raw || '')
    .replace(/^[\s>]+/, '')   // leading > blockquotes
    .replace(/\*+/g, '')      // * and ** markers
    .replace(/^['"]|['"]$/g, '') // surrounding quotes
    .trim()
}

function GreetingAudioPreview({ text, voice }) {
  text = cleanGreeting(text)
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(false)
  const audioRef = useRef(null)

  const toggle = async () => {
    if (playing) {
      audioRef.current?.pause()
      audioRef.current = null
      setPlaying(false)
      return
    }
    setLoading(true)
    try {
      const params = new URLSearchParams({ text, voice: voice || DEFAULT_VOICE })
      const res = await fetch(`/api/v1/tts-preview?${params}`)
      if (!res.ok) throw new Error('TTS failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { setPlaying(false); URL.revokeObjectURL(url) }
      audio.play()
      setPlaying(true)
    } catch {
      setPlaying(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-100">
      <p className="text-[10px] text-emerald-600 font-medium uppercase tracking-wider mb-2">Voice Preview</p>
      <p className="text-xs text-gray-500 italic mb-3 leading-relaxed">"{text}"</p>
      <button
        onClick={toggle}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-700 disabled:opacity-50 transition-all"
      >
        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : playing ? <Square className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
        {loading ? 'Generating…' : playing ? 'Stop' : 'Play Greeting'}
      </button>
    </div>
  )
}

const REVIEW_FIELDS = [
  { section: 'Business', fields: [
    { label: 'Business Name', key: 'business_name' },
    { label: 'Category', key: 'business_category' },
    { label: 'Location', key: 'business_location' },
  ]},
  { section: 'Voice Agent', fields: [
    { label: 'Agent Name', key: 'agent_name' },
    { label: 'TTS Voice', key: 'tts_voice' },
    { label: 'Greeting', key: 'greeting_template' },
  ]},
  { section: 'Database', fields: [
    { label: 'Database Name', key: 'database_name' },
    { label: 'Collection', key: 'resources_collection' },
    { label: 'Price Field', key: 'resource_price_field' },
  ]},
]

function ReviewCard({ config, onChange }) {
  const set = (key, val) => onChange(prev => ({ ...(prev || config), [key]: val }))

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="w-full max-w-[92%] rounded-2xl border border-emerald-200 bg-white shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="px-4 py-3 bg-emerald-50 border-b border-emerald-100 flex items-center gap-2">
        <Edit3 className="w-4 h-4 text-emerald-600" />
        <span className="text-sm font-semibold text-emerald-800">Review & Edit Your Config</span>
        <span className="ml-auto text-[10px] text-emerald-500 uppercase tracking-wider">All fields editable</span>
      </div>

      {/* Sections */}
      <div className="divide-y divide-gray-100">
        {REVIEW_FIELDS.map(({ section, fields }) => (
          <div key={section} className="px-4 py-3">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">{section}</p>
            <div className="space-y-2">
              {fields.map(({ label, key }) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
                  {key === 'tts_voice' ? (
                    <select
                      value={config[key] || DEFAULT_VOICE}
                      onChange={e => set(key, e.target.value)}
                      className="flex-1 text-xs text-gray-900 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-400/30 focus:border-emerald-400 transition-all"
                    >
                      {/* Keep an unknown/legacy voice selectable so the agent's
                          suggestion is never silently dropped. */}
                      {!VOICE_OPTIONS.some(o => o.value === config[key]) && config[key] && (
                        <option value={config[key]}>{config[key]}</option>
                      )}
                      {VOICE_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={config[key] || ''}
                      onChange={e => set(key, e.target.value)}
                      placeholder="—"
                      className="flex-1 text-xs text-gray-900 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-400/30 focus:border-emerald-400 transition-all placeholder:text-gray-300"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

export default function OnboardingPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { messages, sessionId, status, collectedConfig, isReviewMode, confirmError, error } = useSelector(s => s.onboard)
  const user = useSelector((s) => s.auth.user)

  const [input, setInput] = useState('')
  const [waiting, setWaiting] = useState(false)
  const [reviewEdits, setReviewEdits] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Generate session ID on mount
  useEffect(() => {
    if (!sessionId) {
      dispatch(setSessionId(crypto.randomUUID?.() || Date.now().toString()))
    }
  }, [sessionId, dispatch])

  const { connect, disconnect, sendMessage, sendConfirm } = useOnboardingSocket(sessionId)

  // Initialise review edits when review mode activates
  useEffect(() => {
    if (isReviewMode && !reviewEdits) {
      setReviewEdits({ ...collectedConfig })
    }
  }, [isReviewMode, collectedConfig, reviewEdits])

  const handleConfirm = async () => {
    if (confirming) return
    // Clear any previous error first so a repeat of the *same* error still
    // re-triggers the reset effect (which keys off confirmError changing).
    dispatch(setConfirmError(null))
    setConfirming(true)
    const sent = sendConfirm(reviewEdits || collectedConfig)
    if (!sent) {
      // WebSocket isn't open — the click would otherwise hang on "Launching…" forever.
      dispatch(setConfirmError('Connection lost. Please refresh the page and try again.'))
    }
  }

  // Auto-connect once when session ID is ready
  useEffect(() => {
    if (sessionId) {
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
    if (status === 'complete') {
      const timer = setTimeout(async () => {
        await dispatch(fetchMe())
        navigate('/dashboard', { replace: true })
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [status, dispatch, navigate])

  // Redirect to dashboard if already onboarded
  useEffect(() => {
    if (user?.onboarding_complete) {
      navigate('/dashboard', { replace: true })
    }
  }, [user, navigate])

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

  // Reset waiting on any agent reply, review card, or error
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (last?.role === 'agent' || last?.role === 'review_card') {
      setWaiting(false)
      if (last.role === 'agent') inputRef.current?.focus()
    }
  }, [messages])

  // Explicitly clear waiting state when review mode is activated
  useEffect(() => {
    if (isReviewMode) {
      setWaiting(false)
    }
  }, [isReviewMode])

  useEffect(() => {
    if (status === 'error' || status === 'complete') {
      setWaiting(false)
      setConfirming(false)  // socket dropped/completed mid-launch — don't leave the button spinning
    }
  }, [status])

  // Reset confirming when a confirm_error comes back
  useEffect(() => {
    if (confirmError) setConfirming(false)
  }, [confirmError])

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
              {messages.map((msg, i) => {
                if (msg.role === 'review_card') {
                  return (
                    <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="flex w-full justify-start">
                      <ReviewCard
                        config={reviewEdits || collectedConfig}
                        onChange={setReviewEdits}
                      />
                    </motion.div>
                  )
                }
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed break-words overflow-hidden ${
                        msg.role === 'user'
                          ? 'bg-gray-100 border border-gray-200 rounded-2xl rounded-tr-sm text-gray-800 whitespace-pre-wrap'
                          : 'bg-emerald-50 border border-emerald-100 rounded-2xl rounded-tl-sm text-gray-700'
                      }`}
                    >
                      {msg.role === 'user' ? msg.text : (
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                            strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                            ul: ({ children }) => <ul className="list-disc pl-4 my-1 space-y-0.5">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal pl-4 my-1 space-y-0.5">{children}</ol>,
                            li: ({ children }) => <li className="text-sm">{children}</li>,
                            code: ({ children }) => <code className="bg-emerald-100 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                          }}
                        >
                          {msg.text}
                        </ReactMarkdown>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>

            {/* Typing indicator when waiting for agent */}
            {!isReviewMode && waiting && (
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

            {/* Connection error */}
            {status === 'error' && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex justify-center py-8"
              >
                <div className="text-center max-w-sm px-6 py-5 rounded-2xl border border-red-200 bg-red-50/30">
                  <XCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
                  <h3 className="text-sm font-bold text-gray-900 mb-1">Connection Error</h3>
                  <p className="text-xs text-gray-500 mb-4">{confirmError || error || 'Failed to connect to the onboarding server.'}</p>
                  <button
                    onClick={() => {
                      dispatch(resetOnboarding())
                      window.location.reload()
                    }}
                    className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
                  >
                    Retry Setup
                  </button>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom bar — textarea or launch button */}
          <div className="shrink-0 px-6 py-4 border-t border-gray-100 bg-gray-50/50">
            <AnimatePresence mode="wait">
              {isReviewMode ? (
                <motion.button
                  key="launch"
                  initial={{ opacity: 0, y: 10, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.96 }}
                  transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                  whileHover={{ scale: 1.015 }}
                  whileTap={{ scale: 0.985 }}
                  onClick={handleConfirm}
                  disabled={confirming || status === 'complete'}
                  className={`w-full h-12 rounded-xl font-semibold text-sm flex flex-col items-center justify-center gap-0.5 transition-colors shadow-sm cursor-pointer disabled:opacity-60 ${confirmError ? 'bg-red-500 hover:bg-red-600 shadow-red-200' : 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-200'} text-white`}
                >
                  {confirming ? (
                    <span className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Launching your agent…</span>
                  ) : confirmError ? (
                    <>
                      <span className="flex items-center gap-2"><Rocket className="w-4 h-4" /> Try Again</span>
                      <span className="text-[10px] opacity-80">{confirmError}</span>
                    </>
                  ) : (
                    <span className="flex items-center gap-2"><Rocket className="w-4 h-4" /> Go Live — Launch My Agent</span>
                  )}
                </motion.button>
              ) : (
                <motion.div
                  key="input"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25 }}
                  className="flex items-end gap-3"
                >
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value)
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
                      if (inputRef.current) inputRef.current.style.height = 'auto'
                    }}
                    disabled={!input.trim() || status === 'complete' || waiting}
                    className="w-10 h-10 shrink-0 rounded-xl bg-emerald-600 text-white flex items-center justify-center hover:bg-emerald-700 disabled:opacity-40 transition-all cursor-pointer"
                  >
                    <Send className="w-4 h-4" />
                  </motion.button>
                </motion.div>
              )}
            </AnimatePresence>
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
              <GreetingAudioPreview
                text={collectedConfig.greeting_template}
                voice={collectedConfig.tts_voice}
              />
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
