import { createSlice } from '@reduxjs/toolkit'

const onboardSlice = createSlice({
  name: 'onboard',
  initialState: {
    messages: [],        // { role: 'user'|'agent'|'review_card', text, timestamp }
    sessionId: null,
    status: 'idle',      // idle | connecting | chatting | reviewing | complete | error
    collectedConfig: {}, // live preview of extracted fields
    error: null,
    confirmError: null,  // error shown on the launch button
    clientId: null,
    isReviewMode: false,
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
    setReviewMode(state) {
      state.isReviewMode = true
      state.status = 'reviewing'
    },
    setComplete(state, action) {
      state.status = 'complete'
      state.clientId = action.payload
    },
    setConfirmError(state, action) {
      state.confirmError = action.payload  // resets confirming without killing the whole session
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
      state.isReviewMode = false
    },
  },
})

export const {
  setSessionId, setStatus, addMessage,
  updateCollectedConfig, setComplete, setError, setConfirmError,
  setReviewMode, resetOnboarding,
} = onboardSlice.actions

export default onboardSlice.reducer
