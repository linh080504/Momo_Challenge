import { readBase64 } from "./images";

const RATE = 16000;
const MAX_SECONDS = 45;

export async function audioInput(file: File): Promise<string> {
  if (file.size > 12 * 1024 * 1024) throw new Error("Tệp âm thanh vượt quá 12 MB.");
  const context = new AudioContext();
  let decoded: AudioBuffer;
  try {
    decoded = await context.decodeAudioData(await file.arrayBuffer());
  } catch {
    throw new Error("Trình duyệt chưa đọc được bản ghi. Hãy thử tệp WAV, MP3 hoặc M4A.");
  } finally {
    await context.close();
  }
  if (decoded.duration <= 0 || decoded.duration > MAX_SECONDS) throw new Error("Bản ghi phải dài tối đa 45 giây.");
  const sampleCount = Math.ceil(decoded.duration * RATE);
  const output = new OfflineAudioContext(1, sampleCount, RATE);
  const source = output.createBufferSource();
  source.buffer = decoded;
  source.connect(output.destination);
  source.start();
  const mono = (await output.startRendering()).getChannelData(0);
  const wav = new DataView(new ArrayBuffer(44 + mono.length * 2));
  function label(offset: number, value: string) {
    for (let i = 0; i < value.length; i++) wav.setUint8(offset + i, value.charCodeAt(i));
  }
  label(0, "RIFF"); wav.setUint32(4, wav.byteLength - 8, true); label(8, "WAVE");
  label(12, "fmt "); wav.setUint32(16, 16, true);
  wav.setUint16(20, 1, true); wav.setUint16(22, 1, true);
  wav.setUint32(24, RATE, true); wav.setUint32(28, RATE * 2, true);
  wav.setUint16(32, 2, true); wav.setUint16(34, 16, true);
  label(36, "data"); wav.setUint32(40, mono.length * 2, true);
  mono.forEach((sample, index) => wav.setInt16(44 + index * 2, Math.max(-1, Math.min(1, sample)) * 32767, true));
  return readBase64(new Blob([wav.buffer], { type: "audio/wav" }));
}
