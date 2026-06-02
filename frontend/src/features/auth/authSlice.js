import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import api from '../../services/api'

export const signup = createAsyncThunk('auth/signup', async ({ email, password, full_name }, { rejectWithValue }) => {
  try {
    const { data } = await api.post('/auth/signup', { email, password, full_name })
    return data.user
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Signup failed')
  }
})

export const login = createAsyncThunk('auth/login', async ({ email, password }, { rejectWithValue }) => {
  try {
    const { data } = await api.post('/auth/login', { email, password })
    return data.user
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Login failed')
  }
})

export const logout = createAsyncThunk('auth/logout', async () => {
  await api.post('/auth/logout')
})

export const fetchMe = createAsyncThunk('auth/fetchMe', async (_, { rejectWithValue }) => {
  try {
    const { data } = await api.get('/auth/me')
    return data.user
  } catch {
    return rejectWithValue(null)
  }
})

export const deleteAccount = createAsyncThunk('auth/deleteAccount', async (_, { rejectWithValue }) => {
  try {
    await api.delete('/auth/me')
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Delete failed')
  }
})

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    loading: true, // true initially so we don't flash the home page
    error: null,
  },
  reducers: {
    setUser(state, action) {
      state.user = action.payload
      state.error = null
    },
    clearUser(state) {
      state.user = null
      state.error = null
    },
    clearError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    // Signup
    builder.addCase(signup.pending, (state) => { state.loading = true; state.error = null })
    builder.addCase(signup.fulfilled, (state, action) => { state.loading = false; state.user = action.payload })
    builder.addCase(signup.rejected, (state, action) => { state.loading = false; state.error = action.payload })

    // Login
    builder.addCase(login.pending, (state) => { state.loading = true; state.error = null })
    builder.addCase(login.fulfilled, (state, action) => { state.loading = false; state.user = action.payload })
    builder.addCase(login.rejected, (state, action) => { state.loading = false; state.error = action.payload })

    // Logout
    builder.addCase(logout.fulfilled, (state) => { state.user = null; state.loading = false })

    // Fetch me (rehydrate on page load)
    builder.addCase(fetchMe.pending, (state) => { state.loading = true })
    builder.addCase(fetchMe.fulfilled, (state, action) => { state.loading = false; state.user = action.payload })
    builder.addCase(fetchMe.rejected, (state) => { state.loading = false; state.user = null })

    // Delete account
    builder.addCase(deleteAccount.fulfilled, (state) => { state.user = null; state.loading = false })
  },
})

export const { setUser, clearUser, clearError } = authSlice.actions
export default authSlice.reducer
