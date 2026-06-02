import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { store } from './app/store'
import { fetchMe } from './features/auth/authSlice'
import App from './App'
import './styles/index.css'

// Rehydrate auth state on page load (cookie is sent automatically)
store.dispatch(fetchMe())

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </StrictMode>,
)