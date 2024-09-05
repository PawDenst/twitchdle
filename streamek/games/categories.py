from flask import Flask, render_template, request, Blueprint, redirect, url_for, session, jsonify, g, current_app
import random
import json
import os
import logging
import requests
from datetime import datetime, timedelta

categories_app = Blueprint('categories_app', __name__)

# Configure logging
#logging.basicConfig(filename='/var/log/twitchdle.log', level=logging.INFO)


used_streamers_file = 'website/data/hidden_streamers.json'


# Function to load used streamers
def load_used_streamers():
    if os.path.exists(used_streamers_file):
        with open(used_streamers_file, 'r', encoding='utf-8') as file:
            return json.load(file).get('used', [])
    return []


# Function to save used streamers
def save_used_streamers(used_streamers):
    with open(used_streamers_file, 'w', encoding='utf-8') as file:
        json.dump({'used': used_streamers}, file)


# Function to log request details
@categories_app.before_request
def log_request_info():
    # Extract the real IP address
    if 'X-Forwarded-For' in request.headers:
        ip_address = request.headers.getlist('X-Forwarded-For')[0]
    else:
        ip_address = request.remote_addr

    method = request.method
    url = request.url
    user_agent = request.headers.get('User-Agent')
    logging.info(f"Request from IP: {ip_address}, Method: {method}, URL: {url}, User-Agent: {user_agent}")


# Function to load streamers data
def load_streamers():
    with open('website/data/updated_streamers.json', 'r', encoding='utf-8') as file:
        return json.load(file)["streamers"]


streamer = None


# Function to initialize a new streamer
def initialize_streamer():
    global streamer
    streamers = load_streamers()
    used_streamers = load_used_streamers()

    # Get list of available streamers
    available_streamers = [s for s in streamers if s not in used_streamers]

    # Reset used streamers if all streamers have been used
    if not available_streamers:
        used_streamers = []
        available_streamers = list(streamers.keys())
        save_used_streamers(used_streamers)

    # Choose a new streamer from available ones
    seed_categories = current_app.config['seed_categories']
    random.seed(seed_categories)
    streamer = random.choice(available_streamers)

    # Save the new streamer as used
    used_streamers.append(streamer)
    save_used_streamers(used_streamers)

    logging.info(f"New streamer initialized: {streamer}")


@categories_app.before_app_request
def before_first_request():
    if streamer is None:
        initialize_streamer()


# Path to the completion count file
completion_count_file = 'website/data/game_states.json'


def get_completion_count():
    if os.path.exists(completion_count_file):
        with open(completion_count_file, 'r') as file:
            return json.load(file).get('count', 0)
    return 0


def increment_completion_count():
    count = get_completion_count() + 1
    with open(completion_count_file, 'w') as file:
        json.dump({'count': count}, file)


def reset_completion_count():
    with open(completion_count_file, 'w') as file:
        json.dump({'count': 0}, file)


def generate_summary(compared_data):
    symbols = {
        "green": "🟩",
        "orange": "🟧",
        "red": "🟥",
        "greater": "⬇️",
        "lesser": "⬆️"
    }
    summary = "".join(symbols.get(compared_data[category], "⬜") for category in compared_data if category != "Image")
    return summary


def verify_recaptcha(token):
    secret_key = 'key'  # Replace with your secret key
    recaptcha_url = 'https://www.google.com/recaptcha/api/siteverify'
    response = requests.post(recaptcha_url, data={
        'secret': secret_key,
        'response': token
    })
    result = response.json()
    print(f"reCAPTCHA verification result: {result}")  # Debugging line
    return result.get('success', False)


@categories_app.route('/categories', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        recaptcha_response = request.form.get('g-recaptcha-response')
        if not verify_recaptcha(recaptcha_response):
            return jsonify({"error": "reCAPTCHA verification failed"}), 400

    # Your existing code to load streamers and handle form submission...

    streamers = load_streamers()
    user_session = g.session_data

    # Initialize session variables if not present
    if 'guessed_streamers' not in user_session:
        user_session['guessed_streamers'] = []
    if 'guessed_summaries' not in user_session:
        user_session['guessed_summaries'] = []
    if 'hidden_streamer' not in user_session:
        user_session['hidden_streamer'] = streamer
    if 'success_message' not in user_session:
        user_session['success_message'] = None
    if 'attempt_count' not in user_session:
        user_session['attempt_count'] = 0
    if 'available_streamers' not in user_session:
        user_session['available_streamers'] = list(streamers.keys())

    print(user_session['hidden_streamer'])
    logging.info(f"Hidden Streamer: {user_session['hidden_streamer']}")

    # Process POST request when user submits a guess
    if request.method == 'POST' and not user_session['success_message']:
        guessed_streamer = request.form['streamer'].strip().lower()
        logging.info(f"Guessed Streamer: {guessed_streamer}")
        user_session['attempt_count'] += 1

        if guessed_streamer not in [gs[0].lower() for gs in user_session['guessed_streamers']]:
            for original_name, data in streamers.items():
                if guessed_streamer == original_name.lower():
                    data_guessed = data
                    break
            else:
                data_guessed = None

            data_hidden = streamers.get(user_session['hidden_streamer'])

            if data_guessed and data_hidden:
                compared_data = {}
                for category, guessed_value in data_guessed.items():
                    hidden_value = data_hidden.get(category)
                    if hidden_value:
                        if category == 'Top 2 Streamowane Gry':
                            guessed_games = guessed_value.split(', ')
                            if guessed_value == hidden_value:
                                compared_data[category] = "green"
                            elif any(game.strip() == hidden_game.strip() for hidden_game in hidden_value.split(',') for
                                     game in guessed_games):
                                compared_data[category] = "orange"
                            else:
                                compared_data[category] = "red"
                        elif guessed_value == hidden_value:
                            compared_data[category] = "green"
                        elif isinstance(guessed_value, int) and isinstance(hidden_value, int):
                            if guessed_value < hidden_value:
                                compared_data[category] = "lesser"
                            else:
                                compared_data[category] = "greater"
                        else:
                            compared_data[category] = "red"
                    else:
                        compared_data[category] = "red"

                user_session['guessed_streamers'].insert(0, (
                    original_name, data_guessed, compared_data, "newest"))
                user_session['guessed_summaries'].insert(0, generate_summary(compared_data))

                if guessed_streamer == user_session['hidden_streamer'].lower():
                    user_session['success_message'] = True
                    increment_completion_count()

                if original_name in user_session['available_streamers']:
                    user_session['available_streamers'].remove(original_name)

    # Calculate closest higher and closest lower range for each category
    min_ranges = {}
    for category in streamers[user_session['hidden_streamer']].keys():
        if category != 'Image':
            guessed_values = [gs[1].get(category, float('inf')) for gs in user_session['guessed_streamers']]
            if guessed_values:
                guessed_values.sort()
                min_guess = None
                max_guess = None

                # Find closest higher and closest lower values
                for value in guessed_values:
                    if value >= streamers[user_session['hidden_streamer']][category] and (
                            max_guess is None or value < max_guess):
                        max_guess = value
                    if value <= streamers[user_session['hidden_streamer']][category]:
                        min_guess = value

                # Determine the correct range based on closest values found
                if min_guess is not None and max_guess is not None:
                    min_ranges[category] = (min_guess, max_guess)
                else:
                    min_ranges[category] = (
                        min_guess if min_guess is not None else ' ', max_guess if max_guess is not None else ' ',
                        'min' if min_guess is not None else 'max')

    hidden_streamer_image = streamers[user_session['hidden_streamer']]["Image"]
    hidden_streamer_key = user_session['hidden_streamer']
    completion_count = get_completion_count()

    return render_template('categories.html', guessed_streamers=user_session['guessed_streamers'],
                           success_message=user_session['success_message'],
                           attempt_count=user_session['attempt_count'], hidden_streamer_image=hidden_streamer_image,
                           hidden_streamer_key=hidden_streamer_key,
                           guessed_summaries=user_session['guessed_summaries'], completion_count=completion_count,
                           min_ranges=min_ranges)

@categories_app.route('/restart', methods=['POST'])
def restart():
    session.clear()
    return redirect(url_for('categories_app.index'))


@categories_app.route('/fetch_streamer_data', methods=['GET'])
def fetch_streamer_data():
    user_session = g.session_data
    available_streamers = user_session.get('available_streamers', [])
    streamers = load_streamers()
    # Only send necessary data to the client
    filtered_streamers = {k: {'Image': v['Image']} for k, v in streamers.items() if k in available_streamers}
    return jsonify({"streamers": filtered_streamers})


def get_time_until_reset():
    now = datetime.now()
    reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now >= reset_time:
        reset_time += timedelta(days=1)
    time_until_reset = reset_time - now
    return {
        'hours': time_until_reset.seconds // 3600,
        'minutes': (time_until_reset.seconds % 3600) // 60,
        'seconds': time_until_reset.seconds % 60
    }

@categories_app.route('/time_until_reset')
def time_until_reset():
    return jsonify(get_time_until_reset())