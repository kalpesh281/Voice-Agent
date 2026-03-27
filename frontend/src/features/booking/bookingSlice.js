import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  searchResults: [],     // rooms from search
  selectedRoom: null,    // room details being viewed
  availability: null,    // pricing + availability check result
  confirmedBooking: null, // final booking confirmation
  step: 'idle',          // idle | searching | selected | confirming | confirmed
}

const bookingSlice = createSlice({
  name: 'booking',
  initialState,
  reducers: {
    setSearchResults(state, action) {
      state.searchResults = action.payload
      state.step = 'searching'
    },
    setSelectedRoom(state, action) {
      state.selectedRoom = action.payload
      state.step = 'selected'
    },
    setAvailability(state, action) {
      state.availability = action.payload
      state.step = 'confirming'
    },
    setConfirmedBooking(state, action) {
      state.confirmedBooking = action.payload
      state.step = 'confirmed'
    },
    resetBooking(state) {
      Object.assign(state, initialState)
    },
  },
})

export const {
  setSearchResults,
  setSelectedRoom,
  setAvailability,
  setConfirmedBooking,
  resetBooking,
} = bookingSlice.actions

export default bookingSlice.reducer
