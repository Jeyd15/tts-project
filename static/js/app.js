"use strict";

const $ = id => document.getElementById(id);

const textarea    = $("inputText");
const speakBtn    = $("speakBtn");
const stopBtn     = $("stopBtn");
const clearBtn    = $("clearBtn");
const speedSlider = $("speedSlider");
const volSlider   = $("volSlider");
const speedVal    = $("speedVal");
const volVal      = $("volVal");
const statusDot   = $("statusDot");
const statusBar   = $("statusBar");
const statusText  = $("statusText");
const waveform    = $("waveform");
const progressWrap = $("progressWrap");
const progressBar  = $("progressBar");
const voiceLabel  = $("voiceLabel");
const voiceInfo   = $("voiceInfo");
const voiceCount  = $("voiceCount");
const audioPlayer = $("audioPlayer");

let lang    = "english";
let profile = "adult-male";
let blobUrl = null;

const VOICES = {
  english: {
    "adult-male":   "Daniel · 🇬🇧 British",
    "adult-female": "Samantha · 🇺🇸 American",
    "young-boy":    "Junior · 🇺🇸 American",
    "young-girl":   "Karen · 🇦🇺 Australian",
  },
  spanish: {
    "adult-male":   "Reed · 🇲🇽 Spanish",
    "adult-female": "Mónica · 🇪🇸 Castilian",
    "young-boy":    "Junior · 🇲🇽 Spanish",
    "young-girl":   "Paulina · 🇲🇽 Mexican",
  },
  tagalog: {
    "adult-male":   "Rishi · 🇵🇭 Filipino",
    "adult-female": "Tessa · 🇵🇭 Filipino",
    "young-boy":    "Junior · 🇵🇭 Filipino",
    "young-girl":   "Karen · 🇵🇭 Filipino",
  },
};

const SAMPLES = {
  english: {
    "adult-male":   "Welcome. Type your text here and I will read it aloud for you.",
    "adult-female": "Hello! Type anything here and I will speak it out loud.",
    "young-boy":    "Hey! Type something and I will read it for you!",
    "young-girl":   "Hi! Write anything and I will say it out loud!",
  },
  spanish: {
    "adult-male":   "Bienvenido. Escribe tu texto aquí y lo leeré en voz alta.",
    "adult-female": "¡Hola! Escribe cualquier cosa y lo diré en voz alta.",
    "young-boy":    "¡Hola! Escribe algo y lo leeré para ti.",
    "young-girl":   "¡Hola! Escribe cualquier cosa y lo diré en voz alta.",
  },
  tagalog: {
    "adult-male":   "Maligayang pagdating. Mag-type ng teksto at babasahin ko ito para sa iyo.",
    "adult-female": "Kamusta! Mag-type ng kahit ano at sasabihin ko ito nang malakas.",
    "young-boy":    "Hoy! Mag-type ka at babasahin ko para sa iyo!",
    "young-girl":   "Hi! Isulat mo ang kahit ano at sasabihin ko ito!",
  },
};

function updateUI() {
  const name = (VOICES[lang] || {})[profile] || "–";
  voiceLabel.textContent = name;
  voiceInfo.textContent  = name;
  const sample = (SAMPLES[lang] || {})[profile];
  if (sample) { textarea.value = sample; updateCharCount(); }
}

function updateCharCount() {
  const len = textarea.value.trim().length;
  $("charCount").textContent = len + " chars";
  $("charCount").classList.toggle("warn", len > 3000);
}

function setSpeaking(active) {
  speakBtn.disabled    = active;
  speakBtn.textContent = active ? "⏸ Generating…" : "▶ SPEAK";
  statusDot.classList.toggle("speaking", active);
  statusBar.classList.toggle("speaking", active);
  waveform.classList.toggle("active", active);
  progressWrap.classList.toggle("visible", active);
  if (!active) progressBar.style.width = "0%";
}

function setStatus(msg) { statusText.textContent = msg; }
function setProgress(p)  { progressBar.style.width = Math.min(100, p) + "%"; }
function revokeBlob()    { if (blobUrl) { URL.revokeObjectURL(blobUrl); blobUrl = null; } }

// Init
(async () => {
  try {
    const data = await fetch("/api/voices").then(r => r.json());
    if (data.count) voiceCount.textContent = data.count + " voices";
  } catch { voiceCount.textContent = ""; }
  updateUI();
})();

document.querySelectorAll(".lang-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    lang = btn.dataset.lang;
    updateUI();
  });
});

document.querySelectorAll(".voice-card").forEach(card => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".voice-card").forEach(c => c.classList.remove("active"));
    card.classList.add("active");
    profile = card.dataset.profile;
    updateUI();
  });
});

speedSlider.addEventListener("input", () => speedVal.textContent = parseFloat(speedSlider.value).toFixed(2) + "×");
volSlider.addEventListener("input",   () => volVal.textContent   = Math.round(volSlider.value * 100) + "%");
textarea.addEventListener("input", updateCharCount);

speakBtn.addEventListener("click", async () => {
  const text = textarea.value.trim();
  if (!text) { textarea.focus(); return; }
  audioPlayer.pause(); audioPlayer.src = ""; revokeBlob();
  setSpeaking(true); setStatus("Generating…"); setProgress(20);
  try {
    const res = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, language: lang, profile, speed: parseFloat(speedSlider.value), volume: parseFloat(volSlider.value) }),
    });
    setProgress(70);
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.error || res.statusText); }
    blobUrl = URL.createObjectURL(await res.blob());
    audioPlayer.src = blobUrl;
    audioPlayer.volume = parseFloat(volSlider.value);
    setProgress(90); setStatus("Playing…"); speakBtn.textContent = "⏸ Playing…";
    audioPlayer.onended = () => { setSpeaking(false); setStatus("Done ✓"); setTimeout(() => setStatus("Ready"), 2000); };
    audioPlayer.onerror = () => { setSpeaking(false); setStatus("Playback error"); };
    await audioPlayer.play();
  } catch (err) {
    setSpeaking(false); setStatus("Error: " + err.message); setTimeout(() => setStatus("Ready"), 4000);
  }
});

stopBtn.addEventListener("click", () => {
  audioPlayer.pause(); audioPlayer.src = ""; revokeBlob();
  setSpeaking(false); setStatus("Stopped"); setTimeout(() => setStatus("Ready"), 2000);
});

clearBtn.addEventListener("click", () => {
  audioPlayer.pause(); audioPlayer.src = ""; revokeBlob();
  setSpeaking(false); textarea.value = ""; updateCharCount(); setStatus("Ready"); textarea.focus();
});
