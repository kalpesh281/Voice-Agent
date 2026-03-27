import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { store } from './app/store'
import App from './App'
import './styles/index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </StrictMode>,
)
// https://console.deepgram.com/project/92d6df8f-4990-446e-b91b-dda4dcc7d35c/keys i want the deepgrams console ui type so take the
// reference and try to make it this