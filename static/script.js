/* MUS 150 Quiz — frontend logic */

let currentSongId = null;
let currentTermId = null;
let allSongs = [];
let allTerms = [];

// ── Tab switching ────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(s => s.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById(`tab-${tab}`).classList.remove("hidden");
  });
});

// ── Boot ─────────────────────────────────────────────────────────────────
(async function init() {
  await Promise.all([loadSongs(), loadTerms()]);
})();

async function loadSongs() {
  const res = await fetch("/api/songs");
  allSongs = await res.json();

  const grid = document.getElementById("song-list-grid");
  allSongs.forEach(s => {
    const tile = document.createElement("div");
    tile.className = "song-tile";
    tile.innerHTML = `
      <div class="tile-title">${s.title}</div>
      <div class="tile-show">${s.show}</div>
      <span class="tile-badge${s.is_video ? " video" : ""}">${s.is_video ? "VIDEO" : "AUDIO"}</span>`;
    tile.addEventListener("click", () => {
      document.querySelector('.tab-btn[data-tab="part1"]').click();
      loadSong(s.id);
    });
    grid.appendChild(tile);
  });
}

async function loadTerms() {
  const res = await fetch("/api/short_answers");
  allTerms = await res.json();

  const sel = document.getElementById("term-select");
  allTerms.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.term;
    sel.appendChild(opt);
  });
}

// ── Part I controls ──────────────────────────────────────────────────────
document.getElementById("btn-random-song").addEventListener("click", async () => {
  const res = await fetch("/api/songs/random");
  const song = await res.json();
  loadSong(song.id);
});


function loadSong(id) {
  const song = allSongs.find(s => s.id === id);
  if (!song) return;

  currentSongId = id;
  document.getElementById("player-area").classList.remove("hidden");
  hideResult("listening");
  resetListeningForm();

  const audioPlayer = document.getElementById("audio-player");
  const audioSource = document.getElementById("audio-source");

  // Server converts WMA to MP3, so always request as mp3
  const encodedFile = encodeURIComponent(song.audio_file);
  audioSource.src = `/audio/${encodedFile}`;
  audioSource.type = "audio/mpeg";
  audioPlayer.load();

}

function resetListeningForm() {
  ["f-composer","f-lyricist","f-show","f-date","f-context","f-musical-features","f-significance"]
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ""; });
  document.getElementById("revealed-song-title").classList.add("hidden");
}

// ── Part I grading ───────────────────────────────────────────────────────
document.getElementById("listening-form").addEventListener("submit", async e => {
  e.preventDefault();
  if (!currentSongId) return;

  const answers = {
    composer: document.getElementById("f-composer").value,
    lyricist: document.getElementById("f-lyricist").value,
    show: document.getElementById("f-show").value,
    date: document.getElementById("f-date").value,
    context: document.getElementById("f-context").value,
    musical_features: document.getElementById("f-musical-features").value,
    significance: document.getElementById("f-significance").value,
  };

  showLoading(true);
  try {
    const res = await fetch("/api/grade/listening", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ song_id: currentSongId, answers }),
    });
    const data = await res.json();
    showListeningResult(data);
  } catch (err) {
    alert("Error grading: " + err.message);
  } finally {
    showLoading(false);
  }
});

function showListeningResult(data) {
  const panel = document.getElementById("result-listening");
  panel.classList.remove("hidden");

  // Now reveal the song identity
  const song = allSongs.find(s => s.id === currentSongId);
  if (song) {
    document.getElementById("revealed-song-title").textContent = `"${song.title}" — ${song.show}`;
    document.getElementById("revealed-song-title").classList.remove("hidden");
  }

  const scoreEl = document.getElementById("score-listening");
  scoreEl.textContent = data.score ?? "?";
  const score = Number(data.score);
  scoreEl.className = "score-value " + (score >= 6 ? "score-high" : score >= 4 ? "score-mid" : "score-low");

  // Breakdown
  const bd = data.breakdown || {};
  document.getElementById("breakdown-listening").innerHTML = `
    <strong>Identification:</strong> ${bd.identification || "—"}<br>
    <strong>Musical Features:</strong> ${bd.musical_features || "—"}<br>
    <strong>Significance:</strong> ${bd.significance || "—"}
  `;

  document.getElementById("feedback-listening").textContent = data.feedback || "";

  // Correct answers
  const ca = data.correct_answers || {};
  const caEl = document.getElementById("correct-answers-listening");
  caEl.innerHTML = Object.entries({
    "Composer": ca.composer,
    "Lyricist": ca.lyricist,
    "Show": ca.show,
    "Date": ca.date,
    "Context": ca.context,
    "Musical Features": ca.musical_features,
    "Significance": ca.significance,
  }).map(([k, v]) => v ? `
    <div class="answer-row">
      <span class="answer-key">${k}</span>
      <span class="answer-val">${v}</span>
    </div>` : "").join("");

  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

document.getElementById("btn-next-listening").addEventListener("click", async () => {
  const res = await fetch("/api/songs/random");
  const song = await res.json();
  loadSong(song.id);
  document.getElementById("player-area").scrollIntoView({ behavior: "smooth", block: "start" });
});

// ── Part II controls ─────────────────────────────────────────────────────
document.getElementById("btn-random-term").addEventListener("click", async () => {
  const res = await fetch("/api/short_answers/random");
  const term = await res.json();
  loadTerm(term.id);
});

document.getElementById("term-select").addEventListener("change", e => {
  if (e.target.value) loadTerm(e.target.value);
});

function loadTerm(id) {
  const term = allTerms.find(t => t.id === id);
  if (!term) return;

  currentTermId = id;
  document.getElementById("current-term").textContent = term.term;
  document.getElementById("term-area").classList.remove("hidden");
  document.getElementById("f-answer").value = "";
  hideResult("short");
  document.getElementById("term-select").value = id;
}

// ── Part II grading ──────────────────────────────────────────────────────
document.getElementById("short-answer-form").addEventListener("submit", async e => {
  e.preventDefault();
  if (!currentTermId) return;

  const answer = document.getElementById("f-answer").value;

  showLoading(true);
  try {
    const res = await fetch("/api/grade/short_answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term_id: currentTermId, answer }),
    });
    const data = await res.json();
    showShortResult(data);
  } catch (err) {
    alert("Error grading: " + err.message);
  } finally {
    showLoading(false);
  }
});

function showShortResult(data) {
  const panel = document.getElementById("result-short");
  panel.classList.remove("hidden");

  const scoreEl = document.getElementById("score-short");
  scoreEl.textContent = data.score ?? "?";
  const score = Number(data.score);
  scoreEl.className = "score-value " + (score >= 4 ? "score-high" : score >= 2 ? "score-mid" : "score-low");

  document.getElementById("feedback-short").textContent = data.feedback || "";
  document.getElementById("model-answer-short").textContent = data.model_answer || "";

  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

document.getElementById("btn-next-short").addEventListener("click", async () => {
  const res = await fetch("/api/short_answers/random");
  const term = await res.json();
  loadTerm(term.id);
  document.getElementById("term-area").scrollIntoView({ behavior: "smooth", block: "start" });
});

// ── Helpers ───────────────────────────────────────────────────────────────
function hideResult(which) {
  document.getElementById(`result-${which}`).classList.add("hidden");
}

function showLoading(show) {
  document.getElementById("loading-overlay").classList.toggle("hidden", !show);
}
