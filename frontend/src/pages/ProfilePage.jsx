import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useSelector, useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import {
  Radio, Building2, Mic, Database, Package, AlertTriangle,
  Save, Loader2, CheckCircle2, ArrowLeft,
} from 'lucide-react'
import { logout, deleteAccount } from '../features/auth/authSlice'
import api from '../services/api'

const TABS = [
  { id: 'business', label: 'Business', icon: Building2 },
  { id: 'voice', label: 'Voice Agent', icon: Mic },
  { id: 'database', label: 'Database', icon: Database },
  { id: 'resources', label: 'Resources', icon: Package },
  { id: 'danger', label: 'Danger Zone', icon: AlertTriangle },
]

function FormField({ label, value, onChange, type = 'text', placeholder, disabled, textarea }) {
  const Component = textarea ? 'textarea' : 'input'
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1.5">{label}</label>
      <Component
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        rows={textarea ? 3 : undefined}
        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all disabled:opacity-50 resize-none"
      />
    </div>
  )
}

function SelectField({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1.5">{label}</label>
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}

export default function ProfilePage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const user = useSelector((s) => s.auth.user)

  const [activeTab, setActiveTab] = useState('business')
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [resources, setResources] = useState([])
  const [testDbResult, setTestDbResult] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState('')

  const clientId = user?.client_id

  // Load client config
  useEffect(() => {
    if (!clientId) return
    api.get(`/clients/${clientId}`).then(({ data }) => {
      setConfig(data.client)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [clientId])

  // Load resources when tab is active
  useEffect(() => {
    if (activeTab === 'resources' && clientId) {
      api.get(`/clients/${clientId}/resources`).then(({ data }) => {
        setResources(data.resources || [])
      }).catch(() => {})
    }
  }, [activeTab, clientId])

  const updateField = useCallback((path, value) => {
    setConfig((prev) => {
      const copy = JSON.parse(JSON.stringify(prev))
      const keys = path.split('.')
      let obj = copy
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]]
      obj[keys[keys.length - 1]] = value
      return copy
    })
    setSaveSuccess(false)
  }, [])

  const handleSave = async () => {
    if (!config || !clientId) return
    setSaving(true)
    try {
      await api.put(`/clients/${clientId}`, {
        owner_name: config.owner?.name || '',
        owner_email: config.owner?.email || '',
        owner_phone: config.owner?.phone || '',
        owner_company: config.owner?.company || '',
        business_name: config.business?.name || '',
        business_location: config.business?.location || '',
        business_category: config.business?.category || 'hotel',
        currency: config.business?.currency || 'INR',
        token_percentage: config.business?.token_percentage || 20,
        custom_rules: config.business?.custom_rules || [],
        db_type: config.database?.db_type || 'mongodb',
        db_connection_uri: config.database?.connection_uri || '',
        db_name: config.database?.database_name || '',
        resources_collection: config.db_mapping?.resources_collection || '',
        resource_id_field: config.db_mapping?.resource_id_field || 'id',
        resource_name_field: config.db_mapping?.resource_name_field || 'name',
        resource_price_field: config.db_mapping?.resource_price_field || 'price_per_night',
        resource_availability_field: config.db_mapping?.resource_availability_field || 'available',
        searchable_fields: config.db_mapping?.searchable_fields || [],
        display_fields: config.db_mapping?.display_fields || [],
        speech_fields: config.db_mapping?.speech_fields || [],
        agent_name: config.voice?.agent_name || 'Aria',
        agent_personality: config.voice?.agent_personality || '',
        greeting_template: config.voice?.greeting_template || '',
        tts_voice: config.voice?.tts_voice || 'aura-asteria-en',
        system_prompt_template: config.system_prompt_template || '',
      })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      console.error('Save failed:', err)
    }
    setSaving(false)
  }

  const handleTestDb = async () => {
    setTestDbResult(null)
    try {
      const { data } = await api.post(`/clients/${clientId}/test-db`)
      setTestDbResult(data)
    } catch (err) {
      setTestDbResult({ success: false, message: err.response?.data?.detail || 'Failed' })
    }
  }

  const handleDeleteAccount = async () => {
    await dispatch(deleteAccount())
    navigate('/', { replace: true })
  }

  const handleLogout = async () => {
    await dispatch(logout())
    navigate('/', { replace: true })
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-bg-primary">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
      </div>
    )
  }

  const maskUri = (uri) => {
    if (!uri) return ''
    return uri.replace(/:([^@]+)@/, ':****@')
  }

  return (
    <div className="h-screen flex flex-col bg-bg-primary">
      {/* Header */}
      <header className="h-14 px-6 flex items-center justify-between border-b border-gray-200 bg-white shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center border border-gray-200 hover:bg-gray-100 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 text-gray-600" />
          </button>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center border border-emerald-200">
              <Radio className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-gray-900">Profile & Settings</h1>
              <p className="text-[10px] text-gray-400 tracking-wider uppercase">{config?.business?.name}</p>
            </div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-red-600 transition-colors cursor-pointer"
        >
          Sign out
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <nav className="w-52 border-r border-gray-200 bg-white py-4 px-3 shrink-0">
          <div className="space-y-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all cursor-pointer border ${
                  activeTab === tab.id
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : tab.id === 'danger'
                      ? 'text-red-500 border-transparent hover:bg-red-50'
                      : 'text-gray-600 border-transparent hover:bg-gray-50'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="max-w-2xl"
          >
            {/* Business Tab */}
            {activeTab === 'business' && config && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900">Business Details</h2>
                <div className="glass p-6 space-y-4">
                  <FormField label="Business Name" value={config.business?.name} onChange={(v) => updateField('business.name', v)} />
                  <FormField label="Location" value={config.business?.location} onChange={(v) => updateField('business.location', v)} placeholder="City, Country" />
                  <SelectField
                    label="Category"
                    value={config.business?.category}
                    onChange={(v) => updateField('business.category', v)}
                    options={[
                      { value: 'hotel', label: 'Hotel' },
                      { value: 'restaurant', label: 'Restaurant' },
                      { value: 'table_booking', label: 'Table Booking' },
                      { value: 'cricket_ground', label: 'Cricket Ground' },
                      { value: 'pickleball', label: 'Pickleball' },
                      { value: 'ecommerce', label: 'E-commerce' },
                    ]}
                  />
                  <FormField label="Currency" value={config.business?.currency} onChange={(v) => updateField('business.currency', v)} />
                  <FormField label="Token Percentage (%)" value={config.business?.token_percentage} onChange={(v) => updateField('business.token_percentage', parseFloat(v) || 0)} type="number" />
                </div>

                <h3 className="text-sm font-semibold text-gray-700 mt-6">Owner Details</h3>
                <div className="glass p-6 space-y-4">
                  <FormField label="Name" value={config.owner?.name} onChange={(v) => updateField('owner.name', v)} />
                  <FormField label="Email" value={config.owner?.email} onChange={(v) => updateField('owner.email', v)} type="email" />
                  <FormField label="Phone" value={config.owner?.phone} onChange={(v) => updateField('owner.phone', v)} />
                </div>

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-all cursor-pointer"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saveSuccess ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                  {saving ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save changes'}
                </button>
              </div>
            )}

            {/* Voice Tab */}
            {activeTab === 'voice' && config && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900">Voice Agent Settings</h2>
                <div className="glass p-6 space-y-4">
                  <FormField label="Agent Name" value={config.voice?.agent_name} onChange={(v) => updateField('voice.agent_name', v)} />
                  <FormField label="Agent Personality" value={config.voice?.agent_personality} onChange={(v) => updateField('voice.agent_personality', v)} textarea />
                  <FormField label="Greeting Template" value={config.voice?.greeting_template} onChange={(v) => updateField('voice.greeting_template', v)} textarea placeholder="Hello, welcome to {business_name}, I'm {agent_name}..." />
                  <SelectField
                    label="TTS Voice"
                    value={config.voice?.tts_voice}
                    onChange={(v) => updateField('voice.tts_voice', v)}
                    options={[
                      { value: 'aura-asteria-en', label: 'Asteria (Female, warm)' },
                      { value: 'aura-luna-en', label: 'Luna (Female, soft)' },
                      { value: 'aura-orion-en', label: 'Orion (Male, confident)' },
                      { value: 'aura-arcas-en', label: 'Arcas (Male, deep)' },
                      { value: 'aura-stella-en', label: 'Stella (Female, bright)' },
                    ]}
                  />
                </div>

                {/* Custom Instructions — fed into the agent's system prompt */}
                <h3 className="text-sm font-semibold text-gray-700 mt-6 flex items-center gap-2">
                  Custom Instructions
                  <span className="text-xs font-normal text-gray-400">(fed directly into the agent's memory)</span>
                </h3>
                <div className="glass p-6 space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">System Prompt Override</label>
                    <p className="text-xs text-gray-400 mb-2">
                      Leave empty to use the default prompt for your category. If set, this completely replaces the default.
                      Use variables: {'{agent_name}'}, {'{business_name}'}, {'{location}'}, {'{currency}'}, {'{token_percentage}'}, {'{personality}'}, {'{custom_rules}'}
                    </p>
                    <textarea
                      value={config.system_prompt_template || ''}
                      onChange={(e) => updateField('system_prompt_template', e.target.value)}
                      rows={6}
                      placeholder="Leave empty to use the default category prompt..."
                      className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all resize-none font-mono text-xs leading-relaxed"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Custom Rules</label>
                    <p className="text-xs text-gray-400 mb-2">
                      Business-specific rules injected into the agent prompt. One per line.
                      These are added to the RULES section so the agent always follows them.
                    </p>
                    <textarea
                      value={(config.business?.custom_rules || []).join('\n')}
                      onChange={(e) => {
                        const rules = e.target.value.split('\n').filter(r => r.trim())
                        updateField('business.custom_rules', rules)
                      }}
                      rows={5}
                      placeholder={"Check-in time is 2:00 PM, check-out is 11:00 AM\nNo pets allowed\nBreakfast included for all bookings\nMaximum 3 adults per standard room\nChildren under 5 stay free"}
                      className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all resize-none"
                    />
                  </div>
                </div>

                <div className="glass p-4 bg-emerald-50/30 border-emerald-200/50">
                  <p className="text-xs text-emerald-700 leading-relaxed">
                    <strong>How this works:</strong> Custom rules are injected into the agent's system prompt under the RULES section.
                    The agent treats them as strict instructions — it will follow them on every call.
                    This prevents hallucination by giving the agent ground-truth knowledge about your business.
                  </p>
                </div>

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-all cursor-pointer"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saveSuccess ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                  {saving ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save changes'}
                </button>
              </div>
            )}

            {/* Database Tab */}
            {activeTab === 'database' && config && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900">Database Configuration</h2>
                <div className="glass p-6 space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1.5">Connection URI</label>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={config.database?.connection_uri || ''}
                        onChange={(e) => updateField('database.connection_uri', e.target.value)}
                        placeholder="mongodb+srv://user:pass@cluster.mongodb.net"
                        className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all"
                      />
                    </div>
                    {config.database?.connection_uri && (
                      <p className="text-xs text-gray-400 mt-1">{maskUri(config.database.connection_uri)}</p>
                    )}
                  </div>
                  <FormField label="Database Name" value={config.database?.database_name} onChange={(v) => updateField('database.database_name', v)} />

                  <button
                    onClick={handleTestDb}
                    className="px-4 py-2 rounded-xl text-xs font-medium border border-emerald-200 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition-all cursor-pointer"
                  >
                    Test connection
                  </button>

                  {testDbResult && (
                    <div className={`px-4 py-2.5 rounded-xl text-sm border ${testDbResult.success ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-red-50 border-red-200 text-red-600'}`}>
                      {testDbResult.message}
                      {testDbResult.collections?.length > 0 && (
                        <p className="text-xs mt-1 opacity-70">Collections: {testDbResult.collections.join(', ')}</p>
                      )}
                    </div>
                  )}
                </div>

                <h3 className="text-sm font-semibold text-gray-700 mt-6">Field Mapping</h3>
                <div className="glass p-6 space-y-4">
                  <FormField label="Resources Collection" value={config.db_mapping?.resources_collection} onChange={(v) => updateField('db_mapping.resources_collection', v)} />
                  <div className="grid grid-cols-2 gap-4">
                    <FormField label="ID Field" value={config.db_mapping?.resource_id_field} onChange={(v) => updateField('db_mapping.resource_id_field', v)} />
                    <FormField label="Name Field" value={config.db_mapping?.resource_name_field} onChange={(v) => updateField('db_mapping.resource_name_field', v)} />
                    <FormField label="Price Field" value={config.db_mapping?.resource_price_field} onChange={(v) => updateField('db_mapping.resource_price_field', v)} />
                    <FormField label="Availability Field" value={config.db_mapping?.resource_availability_field} onChange={(v) => updateField('db_mapping.resource_availability_field', v)} />
                  </div>
                </div>

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-all cursor-pointer"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : saveSuccess ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                  {saving ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save changes'}
                </button>
              </div>
            )}

            {/* Resources Tab */}
            {activeTab === 'resources' && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-gray-900">Resources</h2>
                <p className="text-sm text-gray-500">Read-only view of your {config?.db_mapping?.resources_collection || 'resources'} collection.</p>

                {resources.length === 0 ? (
                  <div className="glass p-8 text-center text-gray-400 text-sm">
                    No resources found. Make sure your database is configured and has data.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {resources.map((res, i) => (
                      <div key={i} className="glass p-4">
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(res).map(([key, val]) => (
                            <div key={key}>
                              <span className="text-xs text-gray-400">{key}</span>
                              <p className="text-sm text-gray-800 truncate">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Danger Zone */}
            {activeTab === 'danger' && (
              <div className="space-y-5">
                <h2 className="text-lg font-bold text-red-600">Danger Zone</h2>
                <div className="border-2 border-red-200 rounded-2xl p-6 bg-red-50/30">
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">Delete Account</h3>
                  <p className="text-sm text-gray-500 mb-4">
                    This will permanently delete your account and client configuration.
                    Your bookings in your hotel database will be preserved.
                  </p>
                  <FormField
                    label={`Type "${config?.business?.name}" to confirm`}
                    value={deleteConfirm}
                    onChange={setDeleteConfirm}
                    placeholder={config?.business?.name}
                  />
                  <button
                    onClick={handleDeleteAccount}
                    disabled={deleteConfirm !== config?.business?.name}
                    className="mt-4 px-5 py-2.5 rounded-xl text-sm font-semibold bg-red-600 text-white hover:bg-red-700 disabled:opacity-30 transition-all cursor-pointer"
                  >
                    Delete my account
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
