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
