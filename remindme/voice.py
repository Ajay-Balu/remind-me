"""Text-to-speech using the voices built into Windows (System.Speech / SAPI).

No extra Python packages: each utterance runs a hidden PowerShell process,
so the app never blocks. Text and voice name are passed via environment
variables, never pasted into the script.
"""
import logging
import os
import re
import subprocess
import sys
import threading

log = logging.getLogger("remindme")
IS_WIN = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000

_PRE = ("Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; ")
_SPEAK = _PRE + ("if ($env:RM_VOICE) { try { $s.SelectVoice($env:RM_VOICE) } catch {} }; "
                 "$s.Rate = [int]$env:RM_RATE; $s.Volume = [int]$env:RM_VOLUME; "
                 "$s.Speak($env:RM_TEXT)")
_LIST = _PRE + ("$s.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { "
                "$_.VoiceInfo.Name + '|' + $_.VoiceInfo.Culture.Name + '|' + "
                "$_.VoiceInfo.Gender }")


def _ps(script, env_extra=None, capture=False):
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", script],
        env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW if IS_WIN else 0)


class Voice:
    def __init__(self):
        self.voices = None          # list of dicts once loaded ([] if none / failed)
        self._proc = None
        self._lock = threading.Lock()
        if IS_WIN:
            threading.Thread(target=self._load, daemon=True).start()
        else:
            self.voices = []

    def _load(self):
        try:
            p = _ps(_LIST, capture=True)
            out, _ = p.communicate(timeout=30)
            voices = []
            for line in out.decode("utf-8", "ignore").splitlines():
                parts = line.strip().split("|")
                if parts and parts[0]:
                    voices.append({"name": parts[0],
                                   "culture": parts[1] if len(parts) > 1 else "",
                                   "gender": parts[2] if len(parts) > 2 else ""})
            self.voices = voices
            log.info("voices: %s", [v["name"] for v in voices])
        except Exception:
            log.exception("could not list voices")
            self.voices = []

    @staticmethod
    def label(v):
        extra = ", ".join(x for x in (v.get("gender"), v.get("culture")) if x)
        return f"{v['name']} ({extra})" if extra else v["name"]

    @staticmethod
    def clean(text):
        text = re.sub(r"\*[^*]*\*", "", text)          # *actions*
        return re.sub(r"\s+", " ", text).strip()

    def speak(self, text, name="", rate=0, volume=90):
        text = self.clean(text or "")
        if not IS_WIN or not text:
            return
        self.stop()
        try:
            with self._lock:
                self._proc = _ps(_SPEAK, {"RM_TEXT": text[:500], "RM_VOICE": name or "",
                                          "RM_RATE": str(max(-10, min(10, int(rate)))),
                                          "RM_VOLUME": str(max(0, min(100, int(volume))))})
        except Exception:
            log.exception("speak failed")

    def stop(self):
        with self._lock:
            p, self._proc = self._proc, None
        if p is not None and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    @staticmethod
    def estimate_seconds(text, rate=0):
        words = max(1, len(text.split()))
        return words / (2.6 * (1.1 ** rate)) + 0.8
