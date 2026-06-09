import { useCallback, useEffect, useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { setStatus, setError, setConnected as setReduxConnected, resetConversation } from '../features/voice/voiceSlice'
import { resetBooking } from '../features/booking/bookingSlice'
import TopBar from '../components/layout/TopBar'
import VoicePanel from '../components/layout/VoicePanel'
import InfoPanel from '../components/layout/InfoPanel'
import LiveKitSession from '../components/voice/LiveKitSession'

export default function DashboardPage() {
  const dispatch = useDispatch()
  const clientId = useSelector((s) => s.auth.user?.client_id)

  // LiveKit handles transport/audio; we just drive connect + mic intent here.
  const [connected, setConnected] = useState(false)
  const [micEnabled, setMicEnabled] = useState(true)

  // Always start a fresh page load disconnected — never auto-join. This also
  // clears any state HMR/Fast-Refresh might have preserved across a dev reload.
  useEffect(() => {
    setConnected(false)
    dispatch(setReduxConnected(false))
    dispatch(setStatus('idle'))
  }, [dispatch])

  // Connect: the button click is the user gesture WebRTC autoplay needs.
  const handleConnect = useCallback(() => {
    dispatch(setStatus('connecting'))
    setMicEnabled(true)
    setConnected(true)
  }, [dispatch])

  // Disconnect: tear down the room and reset state.
  const handleDisconnect = useCallback(() => {
    setConnected(false)
    setMicEnabled(true)
    dispatch(resetConversation())
    dispatch(resetBooking())
  }, [dispatch])

  // Mute / unmute mic (applied to the published track inside the room).
  const handleMicToggle = useCallback(() => {
    setMicEnabled((v) => !v)
  }, [])

  // New conversation: same as disconnect.
  const handleNewConversation = useCallback(() => {
    handleDisconnect()
  }, [handleDisconnect])

  const handleSessionError = useCallback(
    (e) => {
      dispatch(setError(e?.response?.data?.detail || e?.message || 'Voice connection failed'))
      setConnected(false)
    },
    [dispatch]
  )

  return (
    <div className="h-screen flex flex-col bg-bg-primary overflow-hidden">
      <TopBar onNewConversation={handleNewConversation} />
      <div className="flex flex-1 overflow-hidden">
        <VoicePanel
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onMicToggle={handleMicToggle}
        />
        <InfoPanel />
      </div>
      <LiveKitSession
        clientId={clientId}
        connected={connected}
        micEnabled={micEnabled}
        onError={handleSessionError}
      />
    </div>
  )
}
