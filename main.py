# -*- coding: utf-8 -*-
"""YouTube Auto-Uploader - multi-agent pipeline (Google ADK + Gemini).

Usage:
    python main.py "How Machine Learning Works"
    python main.py "Topic one" "Topic two"      # batch
"""

import os
import sys
import json
import asyncio
import pickle
from datetime import datetime

from dotenv import load_dotenv

# Load GOOGLE_API_KEY from .env BEFORE importing ADK
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("GOOGLE_API_KEY missing. Add it to your .env file.")

from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

# Folder structure
for folder in ["output/videos", "output/audio", "output/slides", "output/thumbnails", "logs"]:
    os.makedirs(folder, exist_ok=True)

# ----------------------------------------------------------------------------
# Retry config
# ----------------------------------------------------------------------------
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# ----------------------------------------------------------------------------
# Font helper (works on Linux, Windows, macOS)
# ----------------------------------------------------------------------------
def load_font(bold: bool, size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

# ----------------------------------------------------------------------------
# Tools - media creation
# ----------------------------------------------------------------------------
def create_audio_from_script(script_text: str, topic: str) -> dict:
    """Generate TTS audio from script text

    Args:
        script_text: The narration script text to convert to speech
        topic: The video topic name for file naming

    Returns:
        dict: Contains audio_path, duration, and status
    """
    try:
        print("      🎤 Creating audio...")
        safe_topic = topic.replace(' ', '_').replace('/', '_')[:50]
        audio_path = f"output/audio/audio_{safe_topic}.mp3"

        tts = gTTS(text=script_text, lang='en', slow=False)
        tts.save(audio_path)

        audio = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close()

        print(f"      ✅ Audio created: {duration:.1f}s")
        return {"audio_path": audio_path, "duration": duration, "status": "success"}
    except Exception as e:
        print(f"      ❌ Audio failed: {e}")
        return {"status": "error", "message": str(e)}


def create_slide_image(text: str, slide_num: int, total_slides: int, topic: str) -> str:
    """Create a single slide image"""
    img = Image.new('RGB', (1920, 1080), color='#ffffff')
    draw = ImageDraw.Draw(img)

    title_font = load_font(True, 80)
    body_font = load_font(False, 55)
    small_font = load_font(False, 28)

    draw.rectangle([0, 0, 1920, 15], fill='#2563eb')
    draw.rectangle([0, 1000, 1920, 1080], fill='#f1f5f9')
    draw.text((60, 1025), f"Slide {slide_num} of {total_slides}", fill='#64748b', font=small_font)

    margin_left = 120
    max_width = 1920 - 240
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=body_font)
        if bbox[2] - bbox[0] > max_width:
            if len(current_line) > 1:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    if slide_num == 1:
        y_offset = (1080 - len(lines) * 100) // 2
        for line in lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            x = (1920 - (bbox[2] - bbox[0])) // 2
            draw.text((x, y_offset), line, fill='#1e293b', font=title_font)
            y_offset += 110
        line_y = y_offset + 20
        draw.rectangle([480, line_y, 1440, line_y + 4], fill='#2563eb')
    else:
        y_offset = 220
        for line in lines[:5]:
            bullet_y = y_offset + 15
            draw.ellipse([margin_left, bullet_y, margin_left + 15, bullet_y + 15], fill='#2563eb')
            draw.text((margin_left + 40, y_offset), line, fill='#1e293b', font=body_font)
            y_offset += 90

    safe_topic = topic.replace(' ', '_').replace('/', '_')[:50]
    slide_path = f"output/slides/slide_{safe_topic}_{slide_num:03d}.png"
    img.save(slide_path)
    return slide_path


def create_slides_from_content(script_data: dict, topic: str) -> dict:
    """Create all slides from script data"""
    try:
        print("      📊 Creating slides...")
        slide_paths = []

        title = script_data.get('title', topic)
        key_points = script_data.get('key_points', [])
        total_slides = len(key_points) + 1

        slide_paths.append(create_slide_image(title, 1, total_slides, topic))
        for i, point in enumerate(key_points, start=2):
            slide_paths.append(create_slide_image(point, i, total_slides, topic))

        print(f"      ✅ Created {len(slide_paths)} slides")
        return {"slide_paths": slide_paths, "count": len(slide_paths), "status": "success"}
    except Exception as e:
        print(f"      ❌ Slides failed: {e}")
        return {"status": "error", "message": str(e)}


def create_thumbnail_image(title: str, topic: str) -> dict:
    """Create YouTube thumbnail"""
    try:
        print("      🎨 Creating thumbnail...")
        img = Image.new('RGB', (1280, 720), color='#0f172a')
        draw = ImageDraw.Draw(img)
        title_font = load_font(True, 80)

        draw.rectangle([0, 0, 40, 720], fill='#3b82f6')
        draw.rectangle([1240, 0, 1280, 720], fill='#8b5cf6')

        words = title.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            if bbox[2] - bbox[0] > 1100:
                if len(current_line) > 1:
                    lines.append(' '.join(current_line[:-1]))
                    current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        y_offset = (720 - len(lines) * 90) // 2
        for line in lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            x = (1280 - (bbox[2] - bbox[0])) // 2
            draw.text((x, y_offset), line, fill='white', font=title_font)
            y_offset += 100

        safe_topic = topic.replace(' ', '_').replace('/', '_')[:50]
        thumbnail_path = f"output/thumbnails/thumb_{safe_topic}.png"
        img.save(thumbnail_path)

        print("      ✅ Thumbnail created")
        return {"thumbnail_path": thumbnail_path, "status": "success"}
    except Exception as e:
        print(f"      ❌ Thumbnail failed: {e}")
        return {"status": "error", "message": str(e)}


def render_final_video(slide_paths_json: str, audio_path: str, topic: str) -> dict:
    """Render final video from slides and audio"""
    try:
        print("      🎬 Rendering video...")
        slide_paths = json.loads(slide_paths_json)

        audio = AudioFileClip(audio_path)
        duration_per_slide = audio.duration / len(slide_paths)

        clips = [ImageClip(p, duration=duration_per_slide) for p in slide_paths]
        video = concatenate_videoclips(clips, method="compose")
        video = video.set_audio(audio)

        safe_topic = topic.replace(' ', '_').replace('/', '_')[:50]
        video_path = f"output/videos/video_{safe_topic}.mp4"

        video.write_videofile(
            video_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None,
        )

        video.close()
        audio.close()

        file_size = round(os.path.getsize(video_path) / (1024 * 1024), 2)
        print(f"      ✅ Video rendered: {file_size}MB")
        return {"video_path": video_path, "file_size_mb": file_size, "status": "success"}
    except Exception as e:
        print(f"      ❌ Rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------------
# Tool - YouTube upload (local browser login)
# ----------------------------------------------------------------------------
def upload_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: str,
    privacy_status: str = "private",
) -> dict:
    """Upload video to YouTube

    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        tags: Comma-separated tags as string
        privacy_status: "public", "private", or "unlisted"

    Returns:
        dict: Contains video_id, url, and status
    """
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    credentials = None

    try:
        if os.path.exists('token.pickle'):
            print("   📂 Loading saved credentials...")
            with open('token.pickle', 'rb') as token:
                credentials = pickle.load(token)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print("   🔄 Refreshing expired credentials...")
                credentials.refresh(Request())
            else:
                if not os.path.exists('client_secrets.json'):
                    return {
                        "status": "error",
                        "message": "client_secrets.json not found in the project folder.",
                        "video_id": None,
                        "url": None,
                    }
                print("   🔐 Opening browser for Google login...")
                flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
                credentials = flow.run_local_server(port=0)

            with open('token.pickle', 'wb') as token:
                pickle.dump(credentials, token)

        youtube = build('youtube', 'v3', credentials=credentials)

        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        body = {
            'snippet': {
                'title': title[:100],
                'description': description,
                'tags': tag_list,
                'categoryId': '27',  # Education
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False,
            },
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

        print("   ⬆️  Uploading...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   ⬆️  {int(status.progress() * 100)}%")

        video_id = response['id']
        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"   ✅ Uploaded: {url}")
        return {"video_id": video_id, "url": url, "status": "success"}
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return {"status": "error", "message": str(e), "video_id": None, "url": None}

# ----------------------------------------------------------------------------
# Agents
# ----------------------------------------------------------------------------
def make_model():
    return Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config)

script_agent = Agent(
    name="ScriptAgent",
    model=make_model(),
    instruction="""You are a professional content writer for educational YouTube videos.

    Given a topic from the user, create a complete video script with the following structure:

    1. A catchy, SEO-friendly title (under 60 characters)
    2. A full narration script (approximately 150 words for a 60-second video)
    3. Exactly 5 key points that will be displayed as slides
    4. 5 relevant tags for YouTube
    5. A 2-3 sentence description for YouTube

    CRITICAL: Return ONLY a valid JSON object with NO markdown formatting, NO code blocks, NO backticks.
    Just pure JSON like this:

    {"title": "Your catchy title here", "script": "Full narration text that will be spoken...", "key_points": ["First key point", "Second key point", "Third key point", "Fourth key point", "Fifth key point"], "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"], "description": "YouTube description text"}

    Make the content engaging, educational, and easy to understand.""",
    output_key="script_data",
)

audio_agent = Agent(
    name="AudioAgent",
    model=make_model(),
    instruction="""You are an audio production agent.

    You have access to script_data from the ScriptAgent which contains a 'script' field with the narration text.

    Extract the script text and call create_audio_from_script with:
    - script_text: the value from script_data['script']
    - topic: the original user query (the topic they asked about)

    Call the function now with these parameters.""",
    tools=[FunctionTool(create_audio_from_script)],
    output_key="audio_data",
)

slides_agent = Agent(
    name="SlidesAgent",
    model=make_model(),
    instruction="""You are a visual design agent specializing in presentation slides.

    You have access to script_data from the ScriptAgent.

    Call create_slides_from_content with:
    - script_data: pass the entire script_data dictionary
    - topic: the original user query

    Call the function now.""",
    tools=[FunctionTool(create_slides_from_content)],
    output_key="slides_data",
)

thumbnail_agent = Agent(
    name="ThumbnailAgent",
    model=make_model(),
    instruction="""You are a thumbnail designer agent.

    You have access to script_data from the ScriptAgent which contains a 'title' field.

    Call create_thumbnail_image with:
    - title: the value from script_data['title']
    - topic: the original user query

    Call the function now.""",
    tools=[FunctionTool(create_thumbnail_image)],
    output_key="thumbnail_data",
)

render_agent = Agent(
    name="RenderAgent",
    model=make_model(),
    instruction="""You are a video rendering agent.

    You have:
    - slides_data containing 'slide_paths' (a list of file paths)
    - audio_data containing 'audio_path' (a string path)

    Steps:
    1. Extract slide_paths list from slides_data
    2. Convert to JSON string: json.dumps(slide_paths)
    3. Extract audio_path from audio_data
    4. Call render_final_video(slide_paths_json, audio_path, topic)

    The slide_paths_json parameter must be a JSON string (use json.dumps).

    Call the function now.""",
    tools=[FunctionTool(render_final_video)],
    output_key="video_data",
)

youtube_agent = Agent(
    name="YouTubeAgent",
    model=make_model(),
    instruction="""You are a YouTube upload agent.

    You have:
    - video_data containing 'video_path'
    - script_data containing 'title', 'description', and 'tags' (list)

    Steps:
    1. Extract video_path from video_data
    2. Extract title from script_data
    3. Extract description from script_data
    4. Convert tags list to comma-separated string: ", ".join(script_data['tags'])
    5. Call upload_to_youtube(video_path, title, description, tags_string, "private")

    IMPORTANT: tags must be a comma-separated string like "ai, tech, education"

    Call the function now.""",
    tools=[FunctionTool(upload_to_youtube)],
    output_key="youtube_data",
)

# ----------------------------------------------------------------------------
# Pipeline: Script -> (Audio | Slides | Thumbnail) -> Render -> Upload
# ----------------------------------------------------------------------------
parallel_media_team = ParallelAgent(
    name="MediaProductionTeam",
    sub_agents=[audio_agent, slides_agent, thumbnail_agent],
)

root_agent = SequentialAgent(
    name="YouTubeAutoUploader",
    sub_agents=[script_agent, parallel_media_team, render_agent, youtube_agent],
)

runner = InMemoryRunner(agent=root_agent)


async def create_and_upload_video(topic):
    """Create a complete video and upload to YouTube"""
    print(f"\n{'=' * 70}\n🎬 STARTING PIPELINE\n{'=' * 70}")
    print(f"📋 Topic: {topic}")
    print(f"⏰ Started: {datetime.now():%Y-%m-%d %H:%M:%S}\n")

    start = datetime.now()
    try:
        response = await runner.run_debug(topic)
        print(f"\n✅ PIPELINE COMPLETE in {(datetime.now() - start).total_seconds():.1f}s")
        return response
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


async def batch_create_and_upload(topics):
    """Create and upload multiple videos"""
    results = []
    total_start = datetime.now()

    for i, topic in enumerate(topics, 1):
        print(f"\n{'─' * 70}\n📹 Video {i}/{len(topics)}: {topic}\n{'─' * 70}")
        try:
            response = await create_and_upload_video(topic)
            results.append({"topic": topic, "status": "success", "response": response})
        except Exception as e:
            results.append({"topic": topic, "status": "failed", "error": str(e)})

    ok = len([r for r in results if r["status"] == "success"])
    print(f"\n📊 BATCH DONE: {ok}/{len(topics)} succeeded in "
          f"{(datetime.now() - total_start).total_seconds():.1f}s")
    return results


if __name__ == "__main__":
    topics = sys.argv[1:] or ["How Machine Learning Works"]
    if len(topics) == 1:
        asyncio.run(create_and_upload_video(topics[0]))
    else:
        asyncio.run(batch_create_and_upload(topics))
