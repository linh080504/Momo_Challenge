import base64
import io
import subprocess
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from ...media import media_slot
from ..contract import AnalyzerError

MAX_WAV_BYTES = 2_000_000


def read_speech(encoded, settings):
    if len(encoded) > 4 * ((MAX_WAV_BYTES + 2) // 3):
        raise AnalyzerError(413, "Bản ghi âm vượt quá 2 MB.")
    try:
        data = base64.b64decode(encoded, validate=True)
        if len(data) > MAX_WAV_BYTES:
            raise AnalyzerError(413, "Bản ghi âm vượt quá 2 MB.")
        with wave.open(io.BytesIO(data), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
                raise AnalyzerError(415, "Hãy dùng WAV PCM mono 16 bit, 16 kHz.")
            frames = audio.getnframes()
            if not 0 < frames <= 45 * 16000 or len(audio.readframes(frames)) != frames * 2:
                raise AnalyzerError(422, "Bản ghi phải đọc được và dài tối đa 45 giây.")
    except (ValueError, wave.Error, EOFError) as exc:
        raise AnalyzerError(422, "Bản ghi WAV không hợp lệ.") from exc
    if not settings.whisper_command or not settings.whisper_model_path:
        raise AnalyzerError(503, "Chuyển giọng nói thành văn bản cần bộ nhận dạng Whisper cục bộ.")
    try:
        with media_slot(), TemporaryDirectory(prefix="paypause-speech-") as directory:
            source = Path(directory) / "input.wav"
            source.write_bytes(data)
            command = [settings.whisper_command, "-m", settings.whisper_model_path, "-l", "vi",
                       "-nt", "-otxt", "-of", str(source.with_suffix("")), "-f", str(source)]
            subprocess.run(command, capture_output=True, check=True, timeout=22)
            transcript = source.with_suffix(".txt").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
        raise AnalyzerError(503, "Bộ nhận dạng giọng nói đang gián đoạn.") from exc
    if not transcript:
        raise AnalyzerError(422, "Chưa nhận dạng được lời nói trong bản ghi.")
    return transcript[:12000]
