import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  status: 'idle', // idle | connecting | listening | thinking | agent_speaking
  isConnected: false,
  isMicOn: false,
  transcript: [], // [{role: 'user'|'agent', text, timestamp}]
  toolCalls: [],  // [{tool, args, timestamp}]
  waveformData: new Array(40).fill(0),
  error: null,
}

const voiceSlice = createSlice({
  name: 'voice',
  initialState,
  reducers: {
    setStatus(state, action) {
      state.status = action.payload
    },
    setConnected(state, action) {
      state.isConnected = action.payload
      if (!action.payload) state.status = 'idle'
    },
    setMicOn(state, action) {
      state.isMicOn = action.payload
    },
    addUserMessage(state, action) {
      state.transcript.push({
        role: 'user',
        text: action.payload,
        timestamp: Date.now(),
      })
    },
    addAgentMessage(state, action) {
      state.transcript.push({
        role: 'agent',
        text: action.payload,
        timestamp: Date.now(),
      })
    },
    addToolCall(state, action) {
      state.toolCalls.push({
        ...action.payload,
        timestamp: Date.now(),
      })
    },
    updateWaveform(state, action) {
      state.waveformData = action.payload
    },
    setError(state, action) {
      state.error = action.payload
    },
    resetConversation(state) {
      state.transcript = []
      state.toolCalls = []
      state.status = 'idle'
      state.error = null
    },
  },
})

export const {
  setStatus,
  setConnected,
  setMicOn,
  addUserMessage,
  addAgentMessage,
  addToolCall,
  updateWaveform,
  setError,
  resetConversation,
} = voiceSlice.actions

export default voiceSlice.reducer
