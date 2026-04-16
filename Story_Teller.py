# ============================================
# FINAL AI STORY VIDEO GENERATOR (STABLE)
# ============================================

import speech_recognition as sr
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import os
import random
import requests
import subprocess
import re

from gtts import gTTS
from PIL import Image, ImageDraw
import cv2


# ------------------------------
# AUDIO → TEXT
# ------------------------------
def live_speech_to_text(duration=5):
    fs = 44100
    print("🎤 Speak now...")

    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()

    recording = np.int16(recording * 32767)
    write("temp.wav", fs, recording)

    r = sr.Recognizer()
    with sr.AudioFile("temp.wav") as source:
        audio = r.record(source)

    try:
        text = r.recognize_google(audio)
        print("📝 You said:", text)
        return text
    except:
        print("❌ Speech recognition failed")
        return ""


# ------------------------------
# LOAD MODEL
# ------------------------------
print("🔄 Loading AI model...")
tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")


# ------------------------------
# STORY GENERATION
# ------------------------------
def generate_story(keywords):
    prompt = f"""
You are a creative storyteller for children.

Write a detailed fantasy story based on this idea:
"{keywords}"

Follow this structure strictly:

1. Introduce a main character (child or animal)
2. Describe a situation related to the idea
3. Introduce a problem or challenge
4. Show how the character solves it
5. End with a clear moral related to "{keywords}"

Rules:
- Minimum 180 words
- Use simple English
- Make it emotional and engaging
- Make it logical and meaningful
- Do NOT repeat sentences
- Do NOT generate random or broken text

Story:
"""

    inputs = tokenizer(prompt, return_tensors="pt")

    outputs = model.generate(
        inputs["input_ids"],
        max_new_tokens=400,
        do_sample=True,
        temperature=0.85,
        top_p=0.92,
        repetition_penalty=1.25
    )

    story = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return story.strip()

# ------------------------------
# TEXT TO SPEECH
# ------------------------------
def text_to_speech(story):
    print("\n🔊 Generating narration...")
    tts = gTTS(text=story, lang='en')
    tts.save("story.mp3")


# ------------------------------
# SMART IMAGE PROMPT
# ------------------------------
def get_image_from_story(scene, index):
    import requests
    from PIL import Image
    from io import BytesIO

    prompt = scene.replace(" ", "%20")
    url = f"https://source.unsplash.com/1280x720/?{prompt},fantasy,cartoon"

    filename = f"scene_{index}.jpg"

    try:
        response = requests.get(url, timeout=10)

        # ✅ Check valid response
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.verify()  # validate image

            # reopen (required after verify)
            img = Image.open(BytesIO(response.content))
            img.save(filename)

            return filename

    except Exception as e:
        print(f"⚠️ Image failed for scene {index}, using fallback")

    # 🔥 FALLBACK (always works)
    fallback_url = "https://picsum.photos/1280/720"
    img_data = requests.get(fallback_url).content

    with open(filename, 'wb') as f:
        f.write(img_data)

    return filename


# ------------------------------
# MUSIC SELECTION
# ------------------------------
def get_music_from_story(story):
    import requests

    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    filename = "bg_music.mp3"

    try:
        response = requests.get(url, timeout=10)
        with open(filename, "wb") as f:
            f.write(response.content)

        return filename

    except:
        print("⚠️ Music download failed")
        return None


# ------------------------------
# VIDEO GENERATION
# ------------------------------
def create_video(story):
    print("\n🎬 Creating video...")

    scenes = [s.strip() for s in story.split(".") if s.strip() != ""]

    width, height = 1280, 720
    fps = 24

    temp_video = "temp_video.mp4"

    video = cv2.VideoWriter(
        temp_video,
        cv2.VideoWriter_fourcc(*'mp4v'),
        fps,
        (width, height)
    )

    ffmpeg_path = r"E:\misc\AI Projects\Story_Teller_project\ffmpeg-2026-04-09-git-d3d0b7a5ee-essentials_build\ffmpeg-2026-04-09-git-d3d0b7a5ee-essentials_build\bin\ffmpeg.exe"

    # Get audio duration
    result = subprocess.run(
        [ffmpeg_path, "-i", "story.mp3"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )

    duration_match = re.search(r"Duration: (\d+):(\d+):(\d+.\d+)", result.stderr)

    if duration_match:
        h, m, s = duration_match.groups()
        audio_duration = int(h)*3600 + int(m)*60 + float(s)
    else:
        audio_duration = 10

    scene_duration = audio_duration / len(scenes)

    from PIL import ImageFont

    for i, scene in enumerate(scenes):
        print(f"🖼️ Scene {i+1}")

        img_path = get_image_from_story(scene, i)
        img = Image.open(img_path).resize((width, height))

        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        draw.text(
            (50, height - 120),
            scene[:80],
            font=font,
            fill=(255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0)
        )

        frame = np.array(img)
        frames_count = int(fps * scene_duration)

        for j in range(frames_count):
            scale = 1 + (j / frames_count) * 0.08
            resized = cv2.resize(frame, None, fx=scale, fy=scale)

            h, w = resized.shape[:2]
            start_x = (w - width) // 2
            start_y = (h - height) // 2

            cropped = resized[start_y:start_y+height, start_x:start_x+width]

            video.write(cropped)

    video.release()

    print("🎬 Merging audio...")

    subprocess.run([
        ffmpeg_path,
        "-y",
        "-i", temp_video,
        "-i", "story.mp3",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "final_story.mp4"
    ])

    print("🎉 FINAL VIDEO CREATED!")


# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    text = live_speech_to_text()

    if text:
        print("\n✅ Speech converted")

        story = generate_story(text)
        print("\n📖 Story:\n", story)

        if story:
            text_to_speech(story)
            create_video(story)

            print("\n🎬 PROJECT COMPLETED SUCCESSFULLY!")

        else:
            print("\n❌ Story generation failed")

    else:
        print("\n⚠️ Try speaking clearly")