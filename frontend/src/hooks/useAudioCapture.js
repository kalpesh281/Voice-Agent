import { useCallback, useRef } from 'react'
import { useDispatch } from 'react-redux'
import { setMicOn, updateWaveform } from '../features/voice/voiceSlice'
import { float32ToInt16 } from '../utils/audioUtils'

const SAMPLE_RATE = 16000
const BUFFER_SIZE = 4096

export default function useAudioCapture(onAudioChunk) {
  const dispatch = useDispatch()
  const audioContextRef = useRef(null)
  const streamRef = useRef(null)
  const processorRef = useRef(null)
  const analyserRef = useRef(null)
  const animFrameRef = useRef(null)

  const startCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      streamRef.current = stream

      const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)

      // Analyser for waveform visualization
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 128
      analyser.smoothingTimeConstant = 0.7
      analyserRef.current = analyser
      source.connect(analyser)

      // ScriptProcessor for capturing PCM data
      const processor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1)
      processorRef.current = processor

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0)
        const pcmBuffer = float32ToInt16(inputData)
        onAudioChunk?.(pcmBuffer)
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      dispatch(setMicOn(true))

      // Start waveform animation loop
      const updateVisual = () => {
        if (!analyserRef.current) return
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
        analyserRef.current.getByteFrequencyData(dataArray)

        // Downsample to 40 bars
        const bars = 40
        const step = Math.floor(dataArray.length / bars)
        const waveform = []
        for (let i = 0; i < bars; i++) {
          const val = dataArray[i * step] / 255
          waveform.push(val)
        }
        dispatch(updateWaveform(waveform))

        animFrameRef.current = requestAnimationFrame(updateVisual)
      }
      updateVisual()
    } catch (err) {
      console.error('Mic capture failed:', err)
      dispatch(setMicOn(false))
    }
  }, [dispatch, onAudioChunk])

  const stopCapture = useCallback(() => {
    cancelAnimationFrame(animFrameRef.current)

    processorRef.current?.disconnect()
    analyserRef.current = null
    processorRef.current = null

    audioContextRef.current?.close()
    audioContextRef.current = null

    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null

    dispatch(setMicOn(false))
    dispatch(updateWaveform(new Array(40).fill(0)))
  }, [dispatch])

  return { startCapture, stopCapture }
}
