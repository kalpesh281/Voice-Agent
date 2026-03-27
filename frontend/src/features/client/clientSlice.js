import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api from '../../services/api'

export const fetchClient = createAsyncThunk(
  'client/fetchClient',
  async (clientId) => {
    const res = await api.get(`/clients/${clientId}`)
    return res.data.client
  }
)

const initialState = {
  config: null,
  loading: false,
  error: null,
}

const clientSlice = createSlice({
  name: 'client',
  initialState,
  reducers: {
    setClientFromWs(state, action) {
      state.config = action.payload
      state.loading = false
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchClient.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchClient.fulfilled, (state, action) => {
        state.config = action.payload
        state.loading = false
      })
      .addCase(fetchClient.rejected, (state, action) => {
        state.error = action.error.message
        state.loading = false
      })
  },
})

export const { setClientFromWs } = clientSlice.actions
export default clientSlice.reducer
