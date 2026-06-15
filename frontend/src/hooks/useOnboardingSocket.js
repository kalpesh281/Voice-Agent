import { useCallback, useEffect, useRef } from 'react'
import { useDispatch } from 'react-redux'
import {
  setStatus, addMessage, updateCollectedConfig,
  setComplete, setError, setReviewMode, setConfirmError,
} from '../features/onboarding/onboardSlice'

export default function useOnboardingSocket(sessionId) {
  const dispatch = useDispatch()
  const wsRef = useRef(null)
  const intentionalClose = useRef(false)

  const connect = useCallback(() => {
    if (!sessionId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    intentionalClose.current = false

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const ws = new WebSocket(`${protocol}://${host}/ws/onboard/${sessionId}`)

    ws.onopen = () => {
      console.log('[Onboard WS] Connected')
      dispatch(setStatus('chatting'))
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        console.log('[Onboard WS] Received:', msg.type)

        switch (msg.type) {
          case 'agent_message':
            dispatch(addMessage({ role: 'agent', text: msg.text }))
            if (msg.field && msg.value) {
              dispatch(updateCollectedConfig({ field: msg.field, value: msg.value }))
            }
            break

          case 'config_update':
            if (msg.field && msg.value) {
              dispatch(updateCollectedConfig({ field: msg.field, value: msg.value }))
            }
            break

          case 'review_card':
            dispatch(addMessage({ role: 'review_card', text: '' }))
            dispatch(setReviewMode())
            break

          case 'complete':
            intentionalClose.current = true
            dispatch(setComplete(msg.client_id))
            break

          case 'confirm_error':
            dispatch(setConfirmError(msg.message))
            break

          case 'error':
            dispatch(setError(msg.message))
            break
        }
      } catch (e) {
        console.error('Onboarding WS parse error:', e)
      }
    }

    ws.onclose = () => {
      console.log('[Onboard WS] Closed, intentional:', intentionalClose.current)
      if (!intentionalClose.current) {
        dispatch(setStatus('error'))
      }
    }

    ws.onerror = (e) => {
      console.error('[Onboard WS] Error:', e)
    }

    wsRef.current = ws
  }, [sessionId, dispatch])

  const sendMessage = useCallback((text) => {
    // Always add to UI immediately — decoupled from WS state
    dispatch(addMessage({ role: 'user', text }))
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', text }))
    } else {
      dispatch(setError('Connection lost. Please refresh the page.'))
    }
  }, [dispatch])

  const sendConfirm = useCallback((config) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'confirm', config }))
      return true
    }
    return false
  }, [])

  const disconnect = useCallback(() => {
    intentionalClose.current = true
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  return { connect, disconnect, sendMessage, sendConfirm }
}
