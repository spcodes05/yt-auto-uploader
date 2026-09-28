# YouTube Auto-Uploader (multi-agent)

Topic in -> script, voiceover, slides, thumbnail, video, YouTube upload (private).
Built with Google ADK + Gemini, gTTS, MoviePy, Pillow.

## Setup
1. Install FFmpeg (https://ffmpeg.org) and make sure `ffmpeg` works in your terminal.
2. `python -m venv .venv` then activate it.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your Gemini API key.
5. Put your Google OAuth `client_secrets.json` in this folder (YouTube Data API v3 enabled).
6. `python main.py "How Machine Learning Works"`

First upload opens a browser to log in; a `token.pickle` is saved for next time.

## Never commit
`.env`, `client_secrets.json`, `token.pickle` (already in `.gitignore`).
