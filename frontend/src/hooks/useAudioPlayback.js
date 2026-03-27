import { useCallback, useRef } from 'react'
import { int16ToFloat32 } from '../utils/audioUtils'

const TTS_SAMPLE_RATE = 24000

/**
 * Collects all TTS audio chunks into a single buffer,
 * then plays the entire response as one continuous AudioBuffer.
 * This eliminates ALL gaps/choppiness.
 *
 * Flow: chunks arrive → accumulate → flush signal → merge → play as one block
 */
export default function useAudioPlayback() {
  const audioContextRef = useRef(null)
  const accumulatorRef = useRef([])
  const playTimeoutRef = useRef(null)
  const isPlayingRef = useRef(false)
  const sourceRef = useRef(null)

  const initContext = useCallback(() => {
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      audioContextRef.current = new AudioContext({ sampleRate: TTS_SAMPLE_RATE })
      console.log('[Audio] Context created')
    }
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume()
    }
    return audioContextRef.current
  }, [])

  const playAccumulated = useCallback(() => {
    const ctx = audioContextRef.current
    const chunks = accumulatorRef.current
    if (!ctx || ctx.state !== 'running' || chunks.length === 0) return

    // Merge all chunks into one Float32 array
    const allSamples = []
    for (const chunk of chunks) {
      const float32 = int16ToFloat32(chunk)
      allSamples.push(float32)
    }
    accumulatorRef.current = []

    const totalLength = allSamples.reduce((sum, arr) => sum + arr.length, 0)
    const merged = new Float32Array(totalLength)
    let offset = 0
    for (const arr of allSamples) {
      merged.set(arr, offset)
      offset += arr.length
    }

    // Create one big AudioBuffer and play it
    const buffer = ctx.createBuffer(1, merged.length, TTS_SAMPLE_RATE)
    buffer.getChannelData(0).set(merged)

    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.onended = () => { isPlayingRef.current = false }

    sourceRef.current = source
    isPlayingRef.current = true
    source.start()

    const duration = merged.length / TTS_SAMPLE_RATE
    console.log(`[Audio] Playing ${duration.toFixed(1)}s (${chunks.length} chunks merged)`)
  }, [])

  const enqueueAudio = useCallback((arrayBuffer) => {
    accumulatorRef.current.push(arrayBuffer)

    // Debounce: wait 300ms after last chunk before playing
    // This lets all chunks for one utterance accumulate first
    clearTimeout(playTimeoutRef.current)
    playTimeoutRef.current = setTimeout(() => {
      playAccumulated()
    }, 300)
  }, [playAccumulated])

  const clearQueue = useCallback(() => {
    accumulatorRef.current = []
    clearTimeout(playTimeoutRef.current)
    isPlayingRef.current = false
    if (sourceRef.current) {
      try { sourceRef.current.stop() } catch {}
      sourceRef.current = null
    }
  }, [])

  const cleanup = useCallback(() => {
    clearQueue()
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
  }, [clearQueue])

  return { initContext, enqueueAudio, clearQueue, cleanup }
}
