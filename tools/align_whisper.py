"""Line boundaries from faster-whisper word timestamps + char-level alignment to the script.
Used by tts_gemini.py when faster-whisper is installed (GitHub Actions). Returns None on failure."""
import difflib
import re
import unicodedata


def _norm(s):
    s = unicodedata.normalize("NFC", s.lower())
    s = re.sub(r"[़्ँंः]", "", s)  # nukta, halant, chandrabindu, anusvara, visarga
    return re.sub(r"[^\w]", "", s)


def line_starts(wav_path, lines, model_size="small"):
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return None
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    import subprocess, numpy as np  # decode with ffmpeg: PyAV in new faster-whisper/py3.14 breaks on metadata_errors
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav_path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    segs, _ = model.transcribe(audio, language="hi", word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False, initial_prompt=" ".join(lines)[:400])
    words = [(w.word, w.start, w.end) for s in segs for w in (s.words or [])]
    if len(words) < len(lines):
        return None
    # whisper chars with times
    wchars, wtimes = [], []
    for txt, st, en in words:
        t = _norm(txt)
        for k, ch in enumerate(t):
            wchars.append(ch)
            wtimes.append(st + (en - st) * k / max(1, len(t)))
    # script chars with line index of each line start
    schars, line_pos = [], []
    for l in lines:
        line_pos.append(len(schars))
        schars += list(_norm(l))
    sm = difflib.SequenceMatcher(None, schars, wchars, autojunk=False)
    smap = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            smap[a + k] = b + k
    starts = []
    for i, p in enumerate(line_pos):
        end = line_pos[i + 1] if i + 1 < len(line_pos) else len(schars)
        hit = next((smap[q] for q in range(p, min(end, p + 12)) if q in smap), None)
        starts.append(wtimes[hit] if hit is not None else None)
    known = sum(1 for s in starts if s is not None)
    if known < 0.6 * len(lines):
        return None
    return starts
