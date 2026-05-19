import os
import json
import random
import re
from flask import Flask, jsonify, request, send_from_directory, render_template

import anthropic

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")

with open(os.path.join(DATA_DIR, "songs.json")) as f:
    SONGS = json.load(f)

with open(os.path.join(DATA_DIR, "short_answer.json")) as f:
    SHORT_ANSWERS = json.load(f)

def get_claude_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/songs")
def list_songs():
    songs = []
    for s in SONGS:
        songs.append({
            "id": s["id"],
            "title": s["title"],
            "show": s["show"],
            "is_video": s["is_video"],
            "audio_file": s.get("audio_file"),
            "video_note": s.get("video_note"),
        })
    return jsonify(songs)


@app.route("/api/songs/random")
def random_song():
    exclude_videos = request.args.get("exclude_videos", "false").lower() == "true"
    pool = [s for s in SONGS if not (exclude_videos and s["is_video"])]
    if not pool:
        return jsonify({"error": "No songs available"}), 404
    s = random.choice(pool)
    return jsonify({
        "id": s["id"],
        "title": s["title"],
        "show": s["show"],
        "is_video": s["is_video"],
        "audio_file": s.get("audio_file"),
        "video_note": s.get("video_note"),
    })


@app.route("/api/songs/<song_id>")
def get_song(song_id):
    song = next((s for s in SONGS if s["id"] == song_id), None)
    if not song:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "id": song["id"],
        "title": song["title"],
        "show": song["show"],
        "is_video": song["is_video"],
        "audio_file": song.get("audio_file"),
        "video_note": song.get("video_note"),
    })


@app.route("/api/short_answers")
def list_short_answers():
    return jsonify([{"id": s["id"], "term": s["term"]} for s in SHORT_ANSWERS])


@app.route("/api/short_answers/random")
def random_short_answer():
    item = random.choice(SHORT_ANSWERS)
    return jsonify({"id": item["id"], "term": item["term"]})


@app.route("/api/grade/listening", methods=["POST"])
def grade_listening():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    song_id = data.get("song_id")
    answers = data.get("answers", {})

    song = next((s for s in SONGS if s["id"] == song_id), None)
    if not song:
        return jsonify({"error": "Song not found"}), 404

    feature_prompt = "The student should describe striking musical features (form, type of music, style, word painting, quotation, poetic details, etc.) and the significance of the excerpt."

    prompt = f"""You are grading a music history exam for MUS 150/THEA 150 (Musical Theater History), Prof. Sheppard, Spring 2026.

SONG BEING IDENTIFIED: "{song['title']}" from "{song['show']}"

CORRECT INFORMATION:
- Composer: {song['composer']}
- Lyricist: {song['lyricist']}
- Show: {song['show']}
- Approximate date: {song['year']}
- Dramatic context / characters: {song['context']}
- Key musical features: {song['musical_features']}
- Significance: {song['significance']}

STUDENT'S ANSWERS:
- Composer: {answers.get('composer', '(blank)')}
- Lyricist: {answers.get('lyricist', '(blank)')}
- Show title: {answers.get('show', '(blank)')}
- Approximate date: {answers.get('date', '(blank)')}
- Dramatic context / characters: {answers.get('context', '(blank)')}
- Musical features / description: {answers.get('musical_features', '(blank)')}
- Significance: {answers.get('significance', '(blank)')}

GRADING INSTRUCTIONS:
{feature_prompt}
- Total: 8 points
- Identification fields (composer, lyricist, show, date, context/characters): ~4 points total. Award partial credit generously for partial identification.
- Musical features / visual-musical relationship: ~2 points
- Significance: ~2 points
- Full sentences are NOT required. Bullet points and fragments are fine.
- Be generous with partial credit — this is a study quiz for practice.
- The date only needs to be approximate (within 5 years is fine; decade is acceptable).

Respond with ONLY valid JSON in this exact format:
{{
  "score": <number 0-8>,
  "breakdown": {{
    "identification": "<brief comment on composer/lyricist/show/date/context answers>",
    "musical_features": "<brief comment on their musical/visual description>",
    "significance": "<brief comment on their significance answer>"
  }},
  "feedback": "<2-4 sentences of overall feedback — what they got right, what they missed, encouragement>",
  "correct_answers": {{
    "composer": "{song['composer']}",
    "lyricist": "{song['lyricist']}",
    "show": "{song['show']}",
    "date": "{song['year']}",
    "context": "<concise version of context>",
    "musical_features": "<key features to note>",
    "significance": "<key significance points>"
  }}
}}"""

    try:
        client = get_claude_client()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Extract JSON block if wrapped in markdown
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(raw)
        return jsonify(result)
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse grading response", "raw": raw}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/grade/short_answer", methods=["POST"])
def grade_short_answer():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    term_id = data.get("term_id")
    answer = data.get("answer", "").strip()

    item = next((s for s in SHORT_ANSWERS if s["id"] == term_id), None)
    if not item:
        return jsonify({"error": "Term not found"}), 404

    prompt = f"""You are grading a short-answer identification question for MUS 150/THEA 150 (Musical Theater History), Prof. Sheppard, Spring 2026.

TERM TO IDENTIFY: "{item['term']}"

CORRECT / EXPECTED INFORMATION:
{item['correct_answer']}

STUDENT'S ANSWER:
{answer if answer else '(blank)'}

GRADING INSTRUCTIONS:
- Total: 5 points
- The student must identify/define what this is (who or what it is, basic facts): ~2 points
- The student should explain significance in musical theater history: ~2 points
- Relevant examples cited: ~1 point
- Full sentences are NOT required, but complete information is.
- Be generous with partial credit. Award points for anything correct.
- If the answer is blank or shows no knowledge, award 0.

Respond with ONLY valid JSON in this exact format:
{{
  "score": <number 0-5>,
  "feedback": "<3-5 sentences: what they got right, what was missing, what a strong answer includes>",
  "model_answer": "<a concise model answer they can study from, 3-6 sentences>"
}}"""

    try:
        client = get_claude_client()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(raw)
        return jsonify(result)
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse grading response", "raw": raw}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/audio/<path:filename>")
def serve_audio(filename):
    # WMA files are converted to MP3 in Docker; serve the MP3 version
    if filename.lower().endswith(".wma"):
        filename = filename[:-4] + ".mp3"
    return send_from_directory(AUDIO_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
