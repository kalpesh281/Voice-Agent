/**
 * Convert Float32 audio samples to Int16 PCM bytes.
 * Deepgram expects linear16 (signed 16-bit little-endian).
 */
export function float32ToInt16(float32Array) {
  const int16 = new Int16Array(float32Array.length)
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]))
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return int16.buffer
}

/**
 * Resample a Float32 buffer from `inputRate` down to `targetRate` (default 16k)
 * using linear interpolation. Browsers often ignore AudioContext({sampleRate})
 * and run at 44.1/48kHz; sending that to Deepgram while claiming 16kHz makes
 * speech sound sped-up and transcribe very poorly. This guarantees true 16kHz.
 */
export function resampleTo16k(float32Array, inputRate, targetRate = 16000) {
  if (!inputRate || inputRate === targetRate) return float32Array
  const ratio = inputRate / targetRate
  const newLength = Math.round(float32Array.length / ratio)
  const result = new Float32Array(newLength)
  const lastIdx = float32Array.length - 1
  for (let i = 0; i < newLength; i++) {
    const pos = i * ratio
    const i0 = Math.floor(pos)
    const i1 = Math.min(i0 + 1, lastIdx)
    const frac = pos - i0
    result[i] = float32Array[i0] * (1 - frac) + float32Array[i1] * frac
  }
  return result
}

/**
 * Convert Int16 PCM bytes to Float32 for Web Audio API playback.
 */
export function int16ToFloat32(int16Buffer) {
  const int16 = new Int16Array(int16Buffer)
  const float32 = new Float32Array(int16.length)
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 0x8000
  }
  return float32
}
