import io, os, re, tempfile, threading
import pyttsx3
from flask import Flask, render_template, request, jsonify, send_file

app   = Flask(__name__)
_lock = threading.Lock()

VOICES = {
    ("english", "adult-male"):   {"gender": "male",   "rate": 150},
    ("english", "adult-female"): {"gender": "female", "rate": 170},
    ("english", "young-boy"):    {"gender": "male",   "rate": 210},
    ("english", "young-girl"):   {"gender": "female", "rate": 215},
    ("spanish", "adult-male"):   {"gender": "male",   "rate": 135},
    ("spanish", "adult-female"): {"gender": "female", "rate": 162},
    ("spanish", "young-boy"):    {"gender": "male",   "rate": 205},
    ("spanish", "young-girl"):   {"gender": "female", "rate": 208},
    ("tagalog", "adult-male"):   {"gender": "male",   "rate": 130},
    ("tagalog", "adult-female"): {"gender": "female", "rate": 148},
    ("tagalog", "young-boy"):    {"gender": "male",   "rate": 172},
    ("tagalog", "young-girl"):   {"gender": "female", "rate": 178},
}

ABBR = {
    "english": [(r"\bMr\.",  "Mister"), (r"\bMrs\.", "Missus"),
                (r"\bDr\.",  "Doctor"), (r"\betc\.", "et cetera")],
    "spanish": [(r"\bDr\.",  "Doctor"), (r"\bSr\.",  "Señor"), (r"\bSra\.", "Señora")],
    "tagalog": [],
}

FEMALE = ["female", "zira", "hazel", "samantha", "karen", "tessa", "victoria", "monica", "paulina"]
MALE   = ["male", "david", "mark", "daniel", "alex", "fred", "junior", "reed", "rishi"]

def preprocess(text, lang):
    for pattern, replacement in ABBR.get(lang, []):
        text = re.sub(pattern, replacement, text)
    return text.strip()

def pick_voice(voices, gender):
    keywords = FEMALE if gender == "female" else MALE
    for kw in keywords:
        for v in voices:
            if kw in (v.name or "").lower() or kw in (v.id or "").lower():
                return v.id
    return voices[0].id if voices else None

def speak(text, gender, rate):
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with _lock:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []
            vid    = pick_voice(voices, gender)
            if vid: engine.setProperty("voice", vid)
            engine.setProperty("rate",   rate)
            engine.setProperty("volume", 1.0)
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

    if not text:         return jsonify({"error": "text is required"}), 400
    if len(text) > 5000: return jsonify({"error": "text too long"}), 400

    lang    = (body.get("language") or "english").lower()
    profile = body.get("profile", "adult-male")
    speed   = max(0.5, min(2.0, float(body.get("speed", 1.0))))
    cfg     = VOICES.get((lang, profile)) or VOICES[("english", "adult-male")]

    text  = preprocess(text, lang)
    rate  = int(cfg["rate"] * speed)

    try:
        audio = speak(text, cfg["gender"], rate)
        if not audio: return jsonify({"error": "No audio generated"}), 500
        return send_file(io.BytesIO(audio), mimetype="audio/wav", download_name="speech.wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  TTS Converter → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
