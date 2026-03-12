import io, os, re, platform, subprocess, tempfile, threading
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
IS_MAC     = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
_lock      = threading.Lock()

VOICES = {
    ("english", "adult-male"):   {"mac_voice": "Daniel",  "mac_rate": 145, "prosody": "[[pbas -10]]", "pyttsx3_gender": "male",   "rate": 150},
    ("english", "adult-female"): {"mac_voice": "Samantha","mac_rate": 170, "prosody": "[[pbas +2]]",  "pyttsx3_gender": "female", "rate": 170},
    ("english", "young-boy"):    {"mac_voice": "Junior",  "mac_rate": 210, "prosody": "[[pbas +6]]",  "pyttsx3_gender": "male",   "rate": 210},
    ("english", "young-girl"):   {"mac_voice": "Karen",   "mac_rate": 215, "prosody": "[[pbas +10]]", "pyttsx3_gender": "female", "rate": 215},
    ("spanish", "adult-male"):   {"mac_voice": "Reed",    "mac_rate": 135, "prosody": "[[pbas -12]]", "pyttsx3_gender": "male",   "rate": 135},
    ("spanish", "adult-female"): {"mac_voice": "Mónica",  "mac_rate": 162, "prosody": "[[pbas +2]]",  "pyttsx3_gender": "female", "rate": 162},
    ("spanish", "young-boy"):    {"mac_voice": "Junior",  "mac_rate": 205, "prosody": "[[pbas +8]]",  "pyttsx3_gender": "male",   "rate": 205},
    ("spanish", "young-girl"):   {"mac_voice": "Paulina", "mac_rate": 208, "prosody": "[[pbas +12]]", "pyttsx3_gender": "female", "rate": 208},
    ("tagalog", "adult-male"):   {"mac_voice": "Rishi",   "mac_rate": 130, "prosody": "[[pbas -8]]",  "pyttsx3_gender": "male",   "rate": 130},
    ("tagalog", "adult-female"): {"mac_voice": "Tessa",   "mac_rate": 148, "prosody": "[[pbas +3]]",  "pyttsx3_gender": "female", "rate": 148},
    ("tagalog", "young-boy"):    {"mac_voice": "Junior",  "mac_rate": 172, "prosody": "[[pbas +6]]",  "pyttsx3_gender": "male",   "rate": 172},
    ("tagalog", "young-girl"):   {"mac_voice": "Karen",   "mac_rate": 178, "prosody": "[[pbas +10]]", "pyttsx3_gender": "female", "rate": 178},
}

ABBR = {
    "english": [(r"\bMr\.", "Mister"), (r"\bMrs\.", "Missus"), (r"\bDr\.", "Doctor"),
                (r"\betc\.", "et cetera"), (r"\bvs\.", "versus")],
    "spanish": [(r"\bDr\.", "Doctor"), (r"\bSr\.", "Señor"), (r"\bSra\.", "Señora")],
    "tagalog": [],
}

def preprocess(text, lang):
    for p, r in ABBR.get(lang, []):
        text = re.sub(p, r, text)
    return text.strip()


def speak_mac(text, cfg, speed):
    rate = int(cfg["mac_rate"] * speed)
    full = f"{cfg['prosody']} {text}".strip()
    aiff_fd, aiff = tempfile.mkstemp(suffix=".aiff")
    wav_fd,  wav  = tempfile.mkstemp(suffix=".wav")
    os.close(aiff_fd); os.close(wav_fd)
    try:
        subprocess.run(["say", "-v", cfg["mac_voice"], "-r", str(rate), "-o", aiff, full], check=True, capture_output=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", aiff, wav], check=True, capture_output=True)
        with open(wav, "rb") as f: return f.read()
    finally:
        for p in (aiff, wav):
            try: os.unlink(p)
            except: pass


def speak_pyttsx3(text, cfg, speed):
    import pyttsx3
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with _lock:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []
            gender = cfg["pyttsx3_gender"]
            vid    = None
            for v in voices:
                name = (v.name or "").lower()
                if gender == "female" and any(k in name for k in ["female", "zira", "hazel", "samantha"]):
                    vid = v.id; break
                if gender == "male" and any(k in name for k in ["male", "david", "mark", "daniel"]):
                    vid = v.id; break
            if not vid and voices: vid = voices[0].id
            if vid: engine.setProperty("voice", vid)
            engine.setProperty("rate",   int(cfg["rate"] * speed))
            engine.setProperty("volume", 1.0)
            engine.save_to_file(text, tmp)
            engine.runAndWait()
            engine.stop()
        with open(tmp, "rb") as f: return f.read()
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
    if not text:         return jsonify({"error": "text is required"}), 400
    if len(text) > 5000: return jsonify({"error": "text too long"}), 400

    lang    = (body.get("language") or "english").lower()
    profile = body.get("profile", "adult-male")
    speed   = max(0.5, min(2.0, float(body.get("speed",  1.0))))
    volume  = max(0.0, min(1.0, float(body.get("volume", 1.0))))
    cfg     = VOICES.get((lang, profile)) or VOICES.get(("english", profile))
    text    = preprocess(text, lang)

    try:
        audio = speak_mac(text, cfg, speed) if IS_MAC else speak_pyttsx3(text, cfg, speed)
        if not audio: return jsonify({"error": "No audio generated"}), 500
        return send_file(io.BytesIO(audio), mimetype="audio/wav", download_name="speech.wav")
    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr.decode(errors="replace")}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  TTS Converter → http://localhost:{port}")
    print(f"  Platform : {platform.system()}")
    print(f"  Engine   : {'macOS say' if IS_MAC else 'pyttsx3'}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
