from flask import Blueprint, render_template, jsonify, current_app, request, make_response
import json
import random
import secrets
import logging
import requests
from datetime import datetime, timedelta

emotes_app = Blueprint('emotes_app', __name__, template_folder='../templates')


# Configure logging
# logging.basicConfig(filename='/var/log/twitchdle.log', level=logging.INFO)


with open('website/data/data_emoji.json', 'r', encoding='utf-8') as file:
    emojis_data = json.load(file)

session_data_emotes = {}
streamer = None
current_streamer_index = None
correct_guesses_counter = {'count': 0}


@emotes_app.route('/verify_captcha', methods=['POST'])
def verify_captcha():
    data = request.get_json()
    recaptcha_response = data.get('recaptcha_response')

    secret_key = 'key'
    payload = {
        'secret': secret_key,
        'response': recaptcha_response
    }

    response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
    result = response.json()

    return jsonify({'success': result.get('success', False)})


@emotes_app.before_request
def log_request_info():
    # Extract the real IP address
    if 'X-Forwarded-For' in request.headers:
        ip_address = request.headers.getlist('X-Forwarded-For')[0]
    else:
        ip_address = request.remote_addr

    method = request.method
    url = request.url
    user_agent = request.headers.get('User-Agent')
    logging.info(f"EMOTES: Request from IP: {ip_address}, Method: {method}, URL: {url}, User-Agent: {user_agent}")


def initialize_streamer():
    global streamer, current_streamer_index
    seed = current_app.config.get('seed')
    if seed is None:
        current_app.logger.error("Seed not found in app config")
        return
    random.seed(seed)
    current_streamer_index = random.randint(0, len(emojis_data) - 1)
    streamer = emojis_data[current_streamer_index]


@emotes_app.before_app_request
def before_first_request():
    initialize_streamer()


def get_session_id():
    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = secrets.token_urlsafe()
    if session_id not in session_data_emotes:
        session_data_emotes[session_id] = {}
    return session_id


@emotes_app.route('/emotes')
def emotes():
    session_id = get_session_id()
    current_emoji = streamer['emotes'][0]
    response = make_response(render_template('emotes.html', streamer=streamer['streamer'], current_emoji=current_emoji))
    response.set_cookie('session_id', session_id)
    return response


@emotes_app.route('/emojis_data')
def get_emojis_data():
    return jsonify({'emotes': streamer['emotes'], 'streamer_index': current_streamer_index})


@emotes_app.route('/trigger_start_game')
def trigger_start_game():
    session_id = get_session_id()
    session_data_emotes[session_id]['game_started'] = True
    response = jsonify({'start_game': True})
    response.set_cookie('session_id', session_id)
    return response


@emotes_app.route('/fetch_streamer_details/<int:streamer_index>')
def fetch_streamer_details(streamer_index):
    if 0 <= streamer_index < len(emojis_data):
        streamer_data = emojis_data[streamer_index]
        return jsonify({'streamer': streamer_data['streamer'], 'image_url': streamer_data['image_url']})
    else:
        return jsonify({'error': 'Invalid streamer index'})


@emotes_app.route('/fetch_streamer_details_by_name/<string:streamer_name>')
def fetch_streamer_details_by_name(streamer_name):
    streamer_name_lower = streamer_name.lower()
    for streamer_data in emojis_data:
        if streamer_data['streamer'].lower() == streamer_name_lower:
            return jsonify({'streamer': streamer_data['streamer'], 'image_url': streamer_data['image_url']})
    return jsonify({'error': 'Streamer not found'}), 404


@emotes_app.route('/correct_guesses_count')
def correct_guesses_count():
    return jsonify({'correct_guesses_count': correct_guesses_counter['count']})


def generate_token():
    return secrets.token_urlsafe()


@emotes_app.route('/get_increment_token')
def get_increment_token():
    session_id = get_session_id()
    if session_data_emotes[session_id].get('has_incremented'):
        return jsonify({'error': 'You have already incremented the counter'}), 403

    token = generate_token()
    session_data_emotes[session_id]['increment_token'] = token
    response = jsonify({'token': token})
    response.set_cookie('session_id', session_id)
    return response


@emotes_app.route('/increment_correct_guesses', methods=['POST'])
def increment_correct_guesses():
    session_id = get_session_id()
    if session_data_emotes[session_id].get('has_incremented'):
        return jsonify({'error': 'You have already incremented the counter'}), 403

    token = request.headers.get('X-Increment-Token')
    if not token or token != session_data_emotes[session_id].get('increment_token'):
        return jsonify({'error': 'Unauthorized'}), 403

    correct_guesses_counter['count'] += 1
    session_data_emotes[session_id]['increment_token'] = None  # Invalidate the token after use
    session_data_emotes[session_id]['has_incremented'] = True  # Mark that the user has incremented
    response = jsonify({'correct_guesses_count': correct_guesses_counter['count']})
    response.set_cookie('session_id', session_id)
    return response


@emotes_app.route('/reset_correct_guesses')
def reset_correct_guesses():
    correct_guesses_counter['count'] = 0
    for session_id in session_data_emotes:
        session_data_emotes[session_id]['has_incremented'] = False  # Allow incrementing again after reset
    return jsonify({'correct_guesses_count': correct_guesses_counter['count']})


def reset_correct_guesses_counter():
    correct_guesses_counter['count'] = 0
    for session_id in session_data_emotes:
        session_data_emotes[session_id]['has_incremented'] = False  # Allow incrementing again after reset


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

@emotes_app.route('/time_until_reset')
def time_until_reset():
    return jsonify(get_time_until_reset())
