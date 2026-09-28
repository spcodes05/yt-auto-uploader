# 🎬 YouTube Auto-Uploader

A multi-agent AI pipeline that turns a **single topic** into a finished YouTube video: script, voiceover, slides, thumbnail, rendered video, and upload.

Type a topic → get a private video on your YouTube channel.

```
python main.py "How Machine Learning Works"
```

---

## ✨ Features

- **One command, full video**: script to upload with no manual editing
- **Multi-agent design** built with [Google ADK](https://google.github.io/adk-docs/) and Gemini
- **Parallel media production**: audio, slides and thumbnail are created at the same time
- **Safe by default**: videos upload as **private** so you can review before publishing
- **Batch mode**: pass several topics and it processes them one after another
- **Secrets stay local**: API keys live in `.env`, which is git-ignored

---

## 🧠 How it works

```
Topic
  │
  ▼
ScriptAgent ─────────► title, narration, 5 key points, tags, description
  │
  ▼
MediaProductionTeam (runs in parallel)
  ├─ AudioAgent      ─► voiceover (gTTS)        → output/audio/
  ├─ SlidesAgent     ─► 1920x1080 slides (Pillow) → output/slides/
  └─ ThumbnailAgent  ─► 1280x720 thumbnail       → output/thumbnails/
  │
  ▼
RenderAgent ─────────► slides + audio → MP4 (MoviePy) → output/videos/
  │
  ▼
YouTubeAgent ────────► uploads via YouTube Data API v3 (private)
```

| Stage | Tool / Library |
|-------|----------------|
| Agent orchestration | Google ADK (`SequentialAgent`, `ParallelAgent`) |
| Language model | Gemini (configurable) |
| Text-to-speech | gTTS |
| Slides and thumbnail | Pillow |
| Video rendering | MoviePy |
| Upload | YouTube Data API v3 |

---

## 📋 Prerequisites

- **Python 3.10+**
- **Git**
- A **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey)
- A **Google Cloud project** with the **YouTube Data API v3** enabled and an OAuth **Desktop app** client (`client_secrets.json`)
- *(Optional)* [FFmpeg](https://ffmpeg.org/download.html), since MoviePy usually bundles its own

---

## 🚀 Setup

**1. Clone the repo**
```bash
git clone https://github.com/spcodes05/yt-auto-uploader.git
cd yt-auto-uploader
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your Gemini API key**

Copy `.env.example` to `.env` and edit it:
```env
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: change the model if Google retires this one
GEMINI_MODEL=gemini-3.5-flash-lite
```
No quotes and no spaces around `=`.

**5. Add YouTube credentials**
1. Open the [Google Cloud Console](https://console.cloud.google.com) and create a project.
2. Enable **YouTube Data API v3** under *APIs & Services → Library*.
3. Configure the **OAuth consent screen** (External) and add your Gmail as a **Test user**.
4. Create **Credentials → OAuth client ID → Desktop app**.
5. Download the JSON, rename it to `client_secrets.json`, and place it in the project root.

---

## ▶️ Usage

**Single video**
```bash
python main.py "How Machine Learning Works"
```

**Batch of videos**
```bash
python main.py "How Neural Networks Learn" "What is Blockchain" "Quantum Computing Explained"
```

On the **first upload**, a browser window opens for Google login. Approve access (click *Continue* on the "unverified app" warning). A `token.pickle` file is saved, so later runs skip the login.

Then open [YouTube Studio](https://studio.youtube.com) → **Content**. Your video is there as **Private**. Change visibility when you're happy with it.

---

## 📁 Project structure

```
yt-auto-uploader/
├── main.py              # agents, tools and pipeline
├── requirements.txt     # Python dependencies
├── .env.example         # template for your secrets
├── .gitignore           # keeps secrets and outputs out of Git
├── README.md
└── output/              # generated at runtime (git-ignored)
    ├── audio/
    ├── slides/
    ├── thumbnails/
    └── videos/
```

---

## 🔐 Security

Never commit these files (they are already in `.gitignore`):

| File | Why |
|------|-----|
| `.env` | contains your Gemini API key |
| `client_secrets.json` | your Google OAuth client |
| `token.pickle` | your saved YouTube login |

If a key is ever exposed, **delete it and create a new one** in AI Studio. Google may disable leaked keys automatically.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `GOOGLE_API_KEY missing` | Check that `.env` is in the same folder as `main.py` and is saved |
| `403 ... reported as leaked` | That key is dead. Create a new key in AI Studio |
| `403 ... project has been denied access` | The Google Cloud project is blocked. Create a key in a **new project** or use a different Google account |
| `404 ... model no longer available` | Set `GEMINI_MODEL` in `.env` to a current model name |
| `client_secrets.json not found` | Put the file in the project root with that exact name |
| `Access blocked` at YouTube login | Add your Gmail under **Test users** on the OAuth consent screen |
| `python` not recognized | Reinstall Python and tick **Add Python to PATH** |
| `ModuleNotFoundError` | Activate the virtual environment, then run `pip install -r requirements.txt` |

---

## ⚠️ Notes and limits

- Unverified Google Cloud projects can only upload **private** videos through the YouTube API, which matches this project's default.
- The YouTube Data API has a **daily quota**; each upload uses a large share of it, so batch runs may hit the limit.
- Text-to-speech uses gTTS (requires an internet connection).
- AI-generated scripts can contain mistakes. **Review every video before making it public.**

---

## 🗺️ Ideas for the future

- Better voices (neural TTS)
- Images or stock footage in slides
- Subtitle generation
- Scheduled uploads
- Thumbnail upload via the API

---
