import { useCallback, useEffect } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { setStatus, setMicOn, resetConversation } from '../features/voice/voiceSlice'
import { resetBooking } from '../features/booking/bookingSlice'
import TopBar from '../components/layout/TopBar'
import VoicePanel from '../components/layout/VoicePanel'
import InfoPanel from '../components/layout/InfoPanel'
import useWebSocket from '../hooks/useWebSocket'
import useAudioCapture from '../hooks/useAudioCapture'
import useAudioPlayback from '../hooks/useAudioPlayback'

export default function DashboardPage() {
  const dispatch = useDispatch()
  const isMicOn = useSelector((s) => s.voice.isMicOn)
  const isConnected = useSelector((s) => s.voice.isConnected)
  const clientId = useSelector((s) => s.auth.user?.client_id)

  const { initContext, enqueueAudio, clearQueue, cleanup: cleanupPlayback } = useAudioPlayback()
  const { connect, disconnect, sendAudio } = useWebSocket(clientId, enqueueAudio)
  const { startCapture, stopCapture } = useAudioCapture(sendAudio)

  // Connect: init audio context (user gesture), connect WS, start mic
  const handleConnect = useCallback(() => {
    initContext()
    dispatch(setStatus('connecting'))
    connect()
    startCapture()
  }, [initContext, connect, startCapture, dispatch])

  // Disconnect: stop everything, reset state
  const handleDisconnect = useCallback(() => {
    stopCapture()
    clearQueue()
    disconnect()
    dispatch(resetConversation())
    dispatch(resetBooking())
  }, [stopCapture, clearQueue, disconnect, dispatch])

  // Mute / Unmute mic
  const handleMicToggle = useCallback(() => {
    if (isMicOn) {
      stopCapture()
      dispatch(setMicOn(false))
    } else {
      startCapture()
    }
  }, [isMicOn, startCapture, stopCapture, dispatch])

  // New conversation: disconnect, reset everything
  const handleNewConversation = useCallback(() => {
    stopCapture()
    clearQueue()
    disconnect()
    dispatch(resetConversation())
    dispatch(resetBooking())
  }, [stopCapture, clearQueue, disconnect, dispatch])

  useEffect(() => {
    return () => {
      stopCapture()
      disconnect()
      cleanupPlayback()
    }
  }, [stopCapture, disconnect, cleanupPlayback])

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
    </div>
  )
}
