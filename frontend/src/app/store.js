import { configureStore } from '@reduxjs/toolkit'
import authReducer from '../features/auth/authSlice'
import onboardReducer from '../features/onboarding/onboardSlice'
import voiceReducer from '../features/voice/voiceSlice'
import bookingReducer from '../features/booking/bookingSlice'
import clientReducer from '../features/client/clientSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    onboard: onboardReducer,
    voice: voiceReducer,
    booking: bookingReducer,
    client: clientReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['voice/addAudioChunk'],
        ignoredPaths: ['voice.audioChunks'],
      },
    }),
})
