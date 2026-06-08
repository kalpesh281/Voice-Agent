import { useCallback, useEffect, useRef } from 'react'
import { useDispatch } from 'react-redux'
import { setStatus, setConnected, addUserMessage, addAgentMessage, addToolCall, setError } from '../features/voice/voiceSlice'
import { setSearchResults, setSelectedRoom, setAvailability, setConfirmedBooking } from '../features/booking/bookingSlice'
import { setClientFromWs } from '../features/client/clientSlice'

export default function useWebSocket(clientId, onAudioReceived, onInterrupt) {
  const dispatch = useDispatch()
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const intentionalClose = useRef(false)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    intentionalClose.current = false

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const ws = new WebSocket(`${protocol}://${host}/ws/voice/${clientId}`)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      dispatch(setConnected(true))
      dispatch(setStatus('listening'))
    }

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        // Binary = TTS audio chunk from server
        console.log(`[WS] Audio chunk received: ${event.data.byteLength} bytes`)
        onAudioReceived?.(event.data)
        return
      }

      // JSON control message
      try {
        const msg = JSON.parse(event.data)
        switch (msg.type) {
          case 'session_start':
            dispatch(setClientFromWs({
              business_name: msg.business_name,
              agent_name: msg.agent_name,
              category: msg.category,
              client_id: msg.client_id,
            }))
            break
          case 'state':
            dispatch(setStatus(msg.state))
            break
          case 'interrupt':
            // Barge-in: agent was cut off — stop playback immediately
            onInterrupt?.()
            break
          case 'user_transcript':
            dispatch(addUserMessage(msg.text))
            break
          case 'agent_message':
            dispatch(addAgentMessage(msg.text))
            break
          case 'tool_call':
            dispatch(addToolCall({ tool: msg.tool, args: msg.args }))
            break
          case 'search_results':
            dispatch(setSearchResults(msg.results || []))
            break
          case 'resource_details':
            dispatch(setSelectedRoom(msg.resource))
            break
          case 'availability':
            dispatch(setAvailability(msg))
            break
          case 'booking_confirmed':
            dispatch(setConfirmedBooking(msg))
            break
          case 'error':
            dispatch(setError(msg.message))
            break
        }
      } catch (e) {
        console.error('WS message parse error:', e)
      }
    }

    ws.onclose = () => {
      dispatch(setConnected(false))
      // Only auto-reconnect if it wasn't an intentional disconnect
      if (!intentionalClose.current) {
        reconnectTimer.current = setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => {
      dispatch(setError('Connection lost'))
    }

    wsRef.current = ws
  }, [clientId, dispatch, onAudioReceived, onInterrupt])

  const disconnect = useCallback(() => {
    intentionalClose.current = true
    clearTimeout(reconnectTimer.current)
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    dispatch(setConnected(false))
  }, [dispatch])

  const sendAudio = useCallback((audioBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(audioBuffer)
    }
  }, [])

  const sendJson = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [])

  return { connect, disconnect, sendAudio, sendJson, wsRef }
}
