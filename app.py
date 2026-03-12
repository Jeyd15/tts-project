import io, os, re, platform, subprocess, tempfile, threading
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
IS_MAC = platform.system() == "Darwin"
_lock  = threading.Lock()

VOICES = {
    ("english", "adult-male"):   {"voice": "Daniel",   "rate": 145, "prosody": "[[pbas -10]]"},
    ("english", "adult-female"): {"voice": "Samantha",  "rate": 170, "prosody": "[[pbas +2]]"},
    ("english", "young-boy"):    {"voice": "Junior",    "rate": 210, "prosody": "[[pbas +6]]"},
    ("english", "young-girl"):   {"voice": "Karen",     "rate": 215, "prosody": "[[pbas +10]]"},
    ("spanish", "adult-male"):   {"voice": "Reed",      "rate": 135, "prosody": "[[pbas -12]]"},
    ("spanish", "adult-female"): {"voice": "Mónica",    "rate": 162, "prosody": "[[pbas +2]]"},
    ("spanish", "young-boy"):    {"voice": "Junior",    "rate": 205, "prosody": "[[pbas +8]]"},
    ("spanish", "young-girl"):   {"voice": "Paulina",   "rate": 208, "prosody": "[[pbas +12]]"},
    ("tagalog", "adult-male"):   {"voice": "Rishi",     "rate": 130, "prosody": "[[pbas -8]]"},
    ("tagalog", "adult-female"): {"voice": "Tessa",     "rate": 148, "prosody": "[[pbas +3]]"},
    ("tagalog", "young-boy"):    {"voice": "Junior",    "rate": 172, "prosody": "[[pbas +6]]"},
    ("tagalog", "young-girl"):   {"voice": "Karen",     "rate": 178, "prosody": "[[pbas +10]]"},
}

ABBR = {
    "english": [(r"\bMr\.", "Mister"), (r"\bMrs\.", "Missus"), (r"\bDr\.", "Doctor"),
                (r"\betc\.", "et cetera"), (r"\be\.g\.", "for example"), (r"\bvs\.", "versus")],
    "spanish": [(r"\bDr\.", "Doctor"), (r"\bSr\.", "Señor"), (r"\bSra\.", "Señora")],
    "tagalog": [],
}

def preprocess(text, lang):
    for pattern, replacement in ABBR.get(lang, []):
        text = re.sub(pattern, replacement, text)
    return text.strip()

def speak_mac(text, cfg, speed, volume):
    rate = int(cfg["rate"] * speed)
    full = f"{cfg['prosody']} {text}".strip()
    aiff_fd, aiff = tempfile.mkstemp(suffix=".aiff")
    wav_fd,  wav  = tempfile.mkstemp(suffix=".wav")
    os.close(aiff_fd); os.close(wav_fd)
    try:
        subprocess.run(["say", "-v", cfg["voice"], "-r", str(rate), "-o", aiff, full], check=True, capture_output=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", aiff, wav], check=True, capture_output=True)
        with open(wav, "rb") as f:
            return f.read()
    finally:
        for p in (aiff, wav):
            try: os.unlink(p)
            except: pass

def speak_pyttsx3(text, cfg, speed, volume):
    import pyttsx3
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with _lock:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []
            vid    = next((v.id for v in voices if "male" in (v.name or "").lower()), voices[0].id if voices else None)
            if vid: engine.setProperty("voice", vid)
            engine.setProperty("rate", int(cfg["rate"] * speed))
            engine.setProperty("volume", volume)
            engine.save_to_file(text, tmp)
            engine.runAndWait()
            engine.stop()
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        try: os.unlink(tmp)
        except: pass

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/speak", methods=["POST"])
def api_speak():
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    if len(text) > 5000:
        return jsonify({"error": "text too long"}), 400

    lang    = (body.get("language") or "english").lower()
    profile = body.get("profile", "adult-male")
    speed   = max(0.5, min(2.0, float(body.get("speed",  1.0))))
    volume  = max(0.0, min(1.0, float(body.get("volume", 1.0))))
    cfg     = VOICES.get((lang, profile)) or VOICES.get(("english", profile))
    text    = preprocess(text, lang)

    try:
        audio = speak_mac(text, cfg, speed, volume) if IS_MAC else speak_pyttsx3(text, cfg, speed, volume)
        if not audio:
            return jsonify({"error": "No audio generated"}), 500
        return send_file(io.BytesIO(audio), mimetype="audio/wav", download_name="speech.wav")
    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr.decode(errors="replace")}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  TTS Converter → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
