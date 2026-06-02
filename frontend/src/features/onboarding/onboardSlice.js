import { createSlice } from '@reduxjs/toolkit'

const onboardSlice = createSlice({
  name: 'onboard',
  initialState: {
    messages: [],        // { role: 'user'|'agent', text, timestamp }
    sessionId: null,
    status: 'idle',      // idle | connecting | chatting | complete | error
    collectedConfig: {}, // live preview of extracted fields
    error: null,
    clientId: null,      // set on completion
  },
  reducers: {
    setSessionId(state, action) {
      state.sessionId = action.payload
    },
    setStatus(state, action) {
      state.status = action.payload
    },
    addMessage(state, action) {
      state.messages.push({
        ...action.payload,
        timestamp: Date.now(),
      })
    },
    updateCollectedConfig(state, action) {
      const { field, value } = action.payload
      if (field && value) {
        state.collectedConfig[field] = value
      }
    },
    setComplete(state, action) {
      state.status = 'complete'
      state.clientId = action.payload
    },
    setError(state, action) {
      state.status = 'error'
      state.error = action.payload
    },
    resetOnboarding(state) {
      state.messages = []
      state.sessionId = null
      state.status = 'idle'
      state.collectedConfig = {}
      state.error = null
      state.clientId = null
    },
  },
})

export const {
  setSessionId, setStatus, addMessage,
  updateCollectedConfig, setComplete, setError, resetOnboarding,
} = onboardSlice.actions

export default onboardSlice.reducer
