import { configureStore } from '@reduxjs/toolkit'
import voiceReducer from '../features/voice/voiceSlice'
import bookingReducer from '../features/booking/bookingSlice'
import clientReducer from '../features/client/clientSlice'

export const store = configureStore({
  reducer: {
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
