import os
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, Blueprint, session, jsonify, g, send_file, current_app
import datetime
import random
import json
import re
from datetime import datetime, timedelta
from stats import update_user_stats

from pydub import AudioSegment

quote_app = Blueprint('quote_app', __name__)

quote_file = 'website/data/quotes.json'
used_quotes_file = 'website/data/used_quotes.json'
correct_guesses_count_file = 'website/data/quote_correct_count.json'
daily_quote = None


def read_correct_guesses_count():
    with open(correct_guesses_count_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['correct_guesses_count']


def update_correct_guesses_count():
    count = read_correct_guesses_count()
    count += 1
    with open(correct_guesses_count_file, 'w', encoding='utf-8') as file:
        json.dump({"correct_guesses_count": count}, file)
    return count


def reset_correct_guesses_count():
    with open(correct_guesses_count_file, 'w') as file:
        json.dump({'correct_guesses_count': 0}, file)


def get_audio_slice(wav_file, percentage):
    static_dir = os.path.join('website', 'static')
    wav_file = wav_file.replace('\\', '/')
    wav_path = os.path.join(static_dir, wav_file)

    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"No such file or directory: '{wav_path}'")

    audio = AudioSegment.from_wav(wav_path)
    slice_point = len(audio) * percentage // 100
    sliced_audio = audio[:slice_point]

    buf = BytesIO()
    sliced_audio.export(buf, format='wav')
    buf.seek(0)
    return buf


def load_streamers():
    with open('website/data/data_quote.json', 'r', encoding='utf-8') as file:
        streamers_list = json.load(file)
        return {streamer['streamer'].lower(): streamer for streamer in streamers_list}


# Load quotes from file
def load_quotes():
    with open(quote_file, 'r', encoding='utf-8') as file:
        return json.load(file)

# Load used quotes from file
def load_used_quotes():
    try:
        with open(used_quotes_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Save used quotes to file
def save_used_quotes(used_quotes):
    with open(used_quotes_file, 'w', encoding='utf-8') as file:
        json.dump(used_quotes, file)


def initialize_quote():
    global daily_quote
    quotes = load_quotes()
    used_quotes = load_used_quotes()

    # Get list of available quotes
    available_quotes = [q for q in quotes if q['id'] not in used_quotes]

    # Reset used quotes if all quotes have been used
    if not available_quotes:
        used_quotes = []
        available_quotes = quotes
        save_used_quotes(used_quotes)

    # Choose a new quote from available ones
    seed_quote = current_app.config['seed_quote']
    random.seed(seed_quote)
    daily_quote = random.choice(available_quotes)
    daily_quote['word_count'] = len(daily_quote['text'].split())

    # Save the new quote as used
    used_quotes.append(daily_quote['id'])
    save_used_quotes(used_quotes)

    print(f"New daily quote initialized: {daily_quote['text']}")


@quote_app.before_app_request
def before_first_request():
    if daily_quote is None:
        initialize_quote()


def extract_clip_id(url):
    # Use regex to find the clip ID between 'clip/' and '?'
    match = re.search(r'clip/(.+?)(\?)', url)
    if match:
        return match.group(1)
    return None


@quote_app.route('/quote', methods=['GET', 'POST'])
def quote():
    streamers = load_streamers()
    user_session = g.session_data

    if 'correct_guess_data' not in user_session:
        user_session['correct_guess_data'] = 0
    if 'quote_result' not in user_session:
        user_session['quote_result'] = None
    if 'guessed_quotes' not in user_session:
        user_session['guessed_quotes'] = []
    if 'guesses_counter' not in user_session:
        user_session['guesses_counter'] = 0
    if 'available_streamers_quote' not in user_session:
        user_session['available_streamers_quote'] = list(streamers.keys())
    if 'hint_used' not in user_session:
        user_session['hint_used'] = 0
    if 'correct_guess_count' not in user_session:
        user_session['correct_guess_count'] = 0

    available_streamers_lower = {name.lower(): name for name in user_session['available_streamers_quote']}
    guessed_quotes_lower = [g['name'].lower() for g in user_session['guessed_quotes']]

    if request.method == 'POST':
        if 'hint' in request.form:
            user_session['hint_used'] += 1
            hint_percentage = min(user_session['hint_used'] * 20, 100)
            user_session['sliced_wav'] = hint_percentage
        elif 'streamer' in request.form:
            guess = request.form['streamer'].strip().lower()

            # Validate the guess
            if guess in available_streamers_lower:
                streamer_guess_name = available_streamers_lower[guess]

                # Only count the guess if it hasn't been guessed before
                if guess not in guessed_quotes_lower:
                    user_session['guesses_counter'] += 1
                    guessed_quotes_lower.append(guess)

                    user_session['correct_guess_data'] = {
                        "name": daily_quote['author'],
                        "image": streamers[streamer_guess_name].get('image_url'),
                        "link": daily_quote['link'],
                        "wav": daily_quote['wav'],
                        "clip_id": extract_clip_id(daily_quote['link'])
                    }

                    if guess == daily_quote['author'].strip().lower():
                        user_session['quote_result'] = 'correct'
                        animation_class = 'correct-guess skok'
                        user_session['sliced_wav'] = 100  # Show full audio
                        user_session['correct_guess_count'] = update_correct_guesses_count()
                        won = True
                        first_try = user_session['guesses_counter'] == 1
                        try:
                            update_user_stats(user_session['guesses_counter'], won, first_try, 'quotes')
                        except Exception as e:
                            print(f"Error updating user stats: {e}")  # Handle the error (optional logging)
                    else:
                        user_session['quote_result'] = 'incorrect'
                        animation_class = 'shake'
                        won = False
                        try:
                            update_user_stats(user_session['guesses_counter'], won, False, 'quotes')
                        except Exception as e:
                            print(f"Error updating user stats: {e}")  # Handle the error (optional logging)


                    user_session['guessed_quotes'].insert(0, {
                        "name": streamer_guess_name,
                        "image": streamers[streamer_guess_name].get('image_url'),
                        "animation_class": animation_class
                    })
            else:
                flash('Invalid guess. Please select a streamer from the list.', 'error')

        return redirect(url_for('quote_app.quote'))

    quote_text = daily_quote['text']
    if user_session['quote_result'] != 'correct':
        if daily_quote['word_count'] > 16:
            if user_session['guesses_counter'] < 3:
                words_to_show = int(0.3 * daily_quote['word_count'])
                quote_text = ' '.join(quote_text.split()[:words_to_show])
            elif user_session['guesses_counter'] < 5:
                words_to_show_30 = int(0.3 * daily_quote['word_count'])
                words_to_show_60 = int(0.6 * daily_quote['word_count'])
                quote_text = ' '.join(quote_text.split()[:words_to_show_30]) + " ..."
                quote_text += ' ' + ' '.join(daily_quote['text'].split()[words_to_show_30:words_to_show_60])
            else:
                words_to_show_60 = int(0.6 * daily_quote['word_count'])
                quote_text = ' '.join(quote_text.split()[:words_to_show_60]) + " ..."
                quote_text += ' ' + ' '.join(daily_quote['text'].split()[words_to_show_60:])
        else:
            quote_text = daily_quote['text']

    sliced_wav_percentage = user_session.get('sliced_wav', None)
    user_session['correct_guess_count'] = read_correct_guesses_count()
    return render_template(
        'quote.html',
        correct_guess_data=user_session['correct_guess_data'],
        quote_text=quote_text,
        quote_author=daily_quote['author'],
        quote_link=daily_quote['link'],
        quote_wav=daily_quote['wav'],
        quote_result=user_session['quote_result'],
        guessed_quotes=user_session['guessed_quotes'],
        guesses_counter=user_session['guesses_counter'],
        hint_used=user_session['hint_used'],
        sliced_wav_percentage=sliced_wav_percentage,
        daily_quote=daily_quote,
        correct_guess_count=user_session['correct_guess_count']  # Pass the correct guess count to the template
    )


@quote_app.route('/get_audio_slice')
def get_audio_slice_endpoint():
    percentage = request.args.get('percentage', type=int)
    wav_file = daily_quote['wav']
    audio_slice = get_audio_slice(wav_file, percentage)
    return send_file(audio_slice, mimetype='audio/wav')

@quote_app.route('/fetch_streamer_quote', methods=['GET'])
def fetch_streamer_quote():
    user_session = g.session_data
    available_streamers_quote = user_session.get('available_streamers_quote', [])
    streamers = load_streamers()
    filtered_streamers = {k: {'Image': v['image_url']} for k, v in streamers.items() if k in available_streamers_quote}
    return jsonify({"streamers": filtered_streamers})
