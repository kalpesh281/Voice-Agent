import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // send session cookie with every request
})

// On 401, redirect to home (session expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config.url?.includes('/auth/me')) {
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export default api
