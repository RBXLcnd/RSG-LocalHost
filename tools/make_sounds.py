"""Regenerates app/assets/sounds/ready.wav (a soft two-note chime). Run from the project root."""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

RATE = 22050
OUT = Path("app/assets/sounds/ready.wav")


def note(freq: float, seconds: float, volume: float) -> list[float]:
    frames = int(RATE * seconds)
    samples = []
    for i in range(frames):
        t = i / RATE
        attack = min(1.0, i / (RATE * 0.008))            # 8 ms fade-in, no click
        decay = math.exp(-t * 11.0)                       # bell-like tail
        tone = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(2 * math.pi * freq * 2 * t)
        samples.append(volume * attack * decay * tone)
    return samples


def main() -> None:
    audio = note(659.25, 0.22, 0.30)                      # E5
    gap = [0.0] * int(RATE * 0.03)
    second = note(880.00, 0.38, 0.30)                     # A5
    mix = audio + gap + second
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in mix))


if __name__ == "__main__":
    main()
