import { useEffect, useRef, useState } from 'react'
import { useDispatch } from 'react-redux'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  useTranscriptions,
  useLocalParticipant,
  useMultibandTrackVolume,
} from '@livekit/components-react'
import { Track } from 'livekit-client'
import api from '../../services/api'
import {
  setStatus,
  setConnected,
  setMicOn,
  replaceTranscript,
  updateWaveform,
} from '../../features/voice/voiceSlice'

const WAVEFORM_BARS = 40

// Maps the LiveKit voice-assistant lifecycle to our existing status strings so
// the orb / status indicator keep working unchanged.
const STATE_MAP = {
  // agent active states
  initializing: 'connecting',
  listening: 'listening',
  thinking: 'thinking',
  speaking: 'agent_speaking',
  // pre-join / transport states — agent isn't talking yet
  connecting: 'connecting',
  'pre-connect-buffering': 'connecting',
  disconnected: 'connecting', // browser is in the room but the agent hasn't joined
  failed: 'idle',
}

/**
 * Lives inside <LiveKitRoom>. Pushes agent state + transcripts into Redux and
 * renders the (invisible) audio sink so the agent's voice plays.
 */
function VoiceBridge({ micEnabled }) {
  const dispatch = useDispatch()
  const { state, audioTrack } = useVoiceAssistant()
  const segments = useTranscriptions()
  const { localParticipant } = useLocalParticipant()

  // Agent lifecycle → status
  useEffect(() => {
    if (state) dispatch(setStatus(STATE_MAP[state] || 'idle'))
  }, [state, dispatch])

  // ── Live waveform ──────────────────────────────────────────────────────
  // Visualize the agent's voice while it speaks, otherwise the user's mic, so
  // the orb / bars react to whoever is talking. Both produce a 0..1 band array.
  const micTrack = localParticipant?.getTrackPublication(Track.Source.Microphone)?.track
  // Don't visualize a muted mic (avoids reading a stale/silent track).
  const usableMic = micEnabled ? micTrack : undefined
  const activeTrack = state === 'speaking' ? audioTrack : usableMic
  const bands = useMultibandTrackVolume(activeTrack, { bands: WAVEFORM_BARS })

  useEffect(() => {
    if (bands && bands.length) dispatch(updateWaveform(bands))
  }, [bands, dispatch])

  // Pause / resume by muting the EXISTING published mic track — never via
  // setMicrophoneEnabled, which unpublishes/republishes and renegotiates the
  // track. That republish (fighting <LiveKitRoom audio>) is what broke the call
  // on unmute. mute()/unmute() keeps the track + agent audio path intact.
  useEffect(() => {
    // Reflect intent in the UI immediately, even before the track exists (the
    // track may publish a beat after connect; an early return here used to
    // leave the indicator stuck on the Redux default "muted").
    dispatch(setMicOn(micEnabled))
    const track = localParticipant?.getTrackPublication(Track.Source.Microphone)?.track
    if (!track) return
    Promise.resolve(micEnabled ? track.unmute() : track.mute()).catch(() => {})
  }, [micEnabled, localParticipant, dispatch])

  // Rebuild the conversation log from the live transcription segments. Deepgram
  // can emit several "final" segments for ONE spoken turn (a >0.4s mid-sentence
  // pause finalizes early), each as its own stream. We merge consecutive
  // segments from the SAME speaker into one bubble — a turn only ends when the
  // other speaker talks — so a sentence shows as a single message, not fragments.
  useEffect(() => {
    const localId = localParticipant?.identity
    const ordered = [...segments].sort(
      (a, b) => (a.streamInfo?.timestamp || 0) - (b.streamInfo?.timestamp || 0)
    )
    const merged = []
    for (const seg of ordered) {
      const text = seg.text?.trim()
      if (!text) continue
      const who = seg.participantInfo?.identity
      const role = who && localId && who === localId ? 'user' : 'agent'
      const last = merged[merged.length - 1]
      if (last && last.who === who) {
        last.text = `${last.text} ${text}`.trim()
      } else {
        merged.push({ who, role, text, timestamp: seg.streamInfo?.timestamp || Date.now() })
      }
    }
    dispatch(replaceTranscript(merged.map(({ role, text, timestamp }) => ({ role, text, timestamp }))))
  }, [segments, localParticipant, dispatch])

  return <RoomAudioRenderer />
}

/**
 * Connects to a LiveKit room for the given client when `connected` is true.
 * Fetches a join token from the backend, then mounts <LiveKitRoom>. The agent
 * worker (app/livekit_agent) is auto-dispatched into the same room.
 */
export default function LiveKitSession({ clientId, connected, micEnabled, onError }) {
  const dispatch = useDispatch()
  const [creds, setCreds] = useState(null)

  useEffect(() => {
    let active = true
    if (connected && clientId && !creds) {
      const identity = `web-${clientId}-${Math.random().toString(36).slice(2, 8)}`
      api
        .get('/livekit/token', { params: { client_id: clientId, identity } })
        .then((r) => active && setCreds(r.data))
        .catch((e) => {
          if (!active) return
          onError?.(e)
          dispatch(setStatus('idle'))
        })
    }
    if (!connected && creds) setCreds(null)
    return () => {
      active = false
    }
  }, [connected, clientId, creds, onError, dispatch])

  if (!connected || !creds) return null

  return (
    <LiveKitRoom
      serverUrl={creds.url}
      token={creds.token}
      connect
      audio
      video={false}
      // Clean mic input → much better STT. Echo cancellation keeps the agent's
      // own TTS out of the mic (which otherwise gets transcribed as gibberish).
      options={{
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      }}
      onConnected={() => dispatch(setConnected(true))}
      onDisconnected={() => dispatch(setConnected(false))}
      onError={(e) => onError?.(e)}
    >
      <VoiceBridge micEnabled={micEnabled} />
    </LiveKitRoom>
  )
}
