import requests
from moviepy.editor import VideoFileClip
import speech_recognition as sr
import subprocess
from pytube import YouTube
import os
import glob
import yt_dlp
import json
import re


def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*#]', '_', filename)


def normalize_path(path):
    return path.replace('\\', '/')


def download_audio(url, output_dir):
    cookies_path = 'website/render/cookies.txt'
    try:
        # Ensure the output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Download the info dictionary without downloading the audio first to get the title
        with yt_dlp.YoutubeDL({'cookiefile': cookies_path}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            audio_title = info_dict.get('title', 'audio')
            sanitized_title = sanitize_filename(audio_title)

        # Update the output template to use the sanitized title
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, f'{sanitized_title}.%(ext)s'),
            'cookiefile': cookies_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download audio using the sanitized title
            ydl.extract_info(url, download=True)

        # Construct the full path of the downloaded file
        full_audio_path = os.path.join(output_dir, f"{sanitized_title}.wav")
        print(f"Download completed successfully! Audio saved to {full_audio_path}")
        return full_audio_path

    except Exception as e:
        print("An error occurred while downloading the audio:", str(e))
        return None


def transcribe_audio(audio_path):
    print("Transcription...")
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="pl-PL")
            return text
    except sr.UnknownValueError:
        print("Speech Recognition could not understand the audio")
        return ""
    except sr.RequestError as e:
        print("Could not request results from Speech Recognition service; {0}".format(e))
        return ""


def create_json_output(transcription, video_url, audio_path, json_output_path):
    try:
        # Define the base directory that should be stripped
        base_directory = 'website/static/'

        # Remove the base directory part from the audio_path
        if audio_path.startswith(base_directory):
            relative_audio_path = audio_path[len(base_directory):]
        else:
            relative_audio_path = audio_path


        # Load existing data
        if os.path.exists(json_output_path):
            with open(json_output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        next_id = 1
        if existing_data:
            max_id = max(entry.get("id", 0) for entry in existing_data)
            next_id = max_id + 1

        # Create the new data dictionary
        new_data = {
            "id": next_id,  # Add unique ID
            "text": transcription,
            "author": "AuthorName",  # Replace with actual author if available
            "link": video_url,
            "wav": relative_audio_path  # Path relative to the static directory
        }

        # Check for duplicates
        entry_exists = any(
            entry['text'] == new_data['text'] and
            entry['author'] == new_data['author'] and
            entry['link'] == new_data['link'] and
            entry['wav'] == new_data['wav']
            for entry in existing_data
        )

        if not entry_exists:
            # Append new data if it does not exist
            existing_data.append(new_data)
            # Save to JSON
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
        else:
            print("Entry already exists. Skipping addition.")

    except Exception as e:
        print(f"An error occurred while creating JSON output: {e}")



def save_text(text, filename):
    with open(filename, 'w') as f:
        f.write(text)


def process_clip(clip_url):
    audio_dir = 'website/static/klipy'
    audio_path = download_audio(clip_url, audio_dir)

    if audio_path:
        transcription_file = os.path.splitext(audio_path)[0] + '_transcription.txt'
        transcription = transcribe_audio(audio_path)
        save_text(transcription, transcription_file)

        # Create JSON output
        json_output_path = 'website/data/quotes.json'
        create_json_output(transcription, clip_url, audio_path, json_output_path)
