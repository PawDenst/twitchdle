from flask import Flask, jsonify, session, g, current_app, request, send_from_directory
from flask_apscheduler import APScheduler
import json
import uuid
import secrets
import os
import random
import time
from datetime import datetime, date, timedelta

from main import main_app
from emotes import emotes_app, reset_correct_guesses_counter, session_data_emotes
from words import words_app
from policy import policy_app
from categories import categories_app, initialize_streamer
from quote import quote_app, reset_correct_guesses_count, initialize_quote


def generate_seed():
    return secrets.randbits(32)


def generate_seed_categories():
    return uuid.uuid4().int & (1 << 32) - 1


def generate_seed_quote():
    return uuid.uuid4().int & (1 << 30) - 3

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.template_folder = '../templates'
app.static_folder = '../static'
app.secret_key = 'secret_key'
app.config['seed'] = generate_seed()
app.config['seed_categories'] = generate_seed_categories()
app.config['seed_quote'] = generate_seed_quote()

app.register_blueprint(main_app)
app.register_blueprint(emotes_app)
app.register_blueprint(words_app)
app.register_blueprint(categories_app)
app.register_blueprint(quote_app)
app.register_blueprint(policy_app)

# Global dictionary to simulate session data
session_data = {}

completion_count_file = 'website/data/game_states.json'


def reset_completion_count():
    with open(completion_count_file, 'w') as file:
        json.dump({'count': 0}, file)


def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session.permanent = True  # Ensure the session is permanent
    return session['session_id']


@app.before_request
def load_session():
    session_id = get_session_id()
    g.session_data = session_data.get(session_id, {})

    last_visit_date = g.session_data.get('last_visit_date')
    current_date = date.today().isoformat()
    if not last_visit_date or last_visit_date != current_date:
        g.session_data['restart_game'] = True
        g.session_data['last_visit_date'] = current_date

    if 'game_started' not in g.session_data:
        g.session_data['game_started'] = False


@app.after_request
def save_session(response):
    session_id = get_session_id()
    session_data[session_id] = g.session_data
    return response


@app.route('/check_game_start_flag')
def check_game_start_flag():
    session_id = get_session_id()
    restart_game = session_data.get(session_id, {}).get('restart_game', False)
    session_data[session_id]['restart_game'] = False  # Reset the restart_game flag after checking
    return jsonify({'restart_game': restart_game})


@app.route('/fetch_streamer_data')
def fetch_streamer_data():
    with open('website/data/updated_streamers.json', 'r') as f:
        data = json.load(f)
        filtered_data = {k: {'Image': v['Image']} for k, v in data["streamers"].items()}
    return jsonify({"streamers": filtered_data})


@app.route('/fetch_streamer_emoji')
def fetch_streamer():
    with open('website/data/data_emoji.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        filtered_data = {
            streamer['streamer']: {
                'image_url': streamer['image_url']
            }
            for streamer in data  # Iterate over data directly assuming it's a list of dictionaries
        }
    return jsonify({"streamers": filtered_data})

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(app.root_path, 'ads.txt')

# Calculate remaining time until midnight and set session lifetime
now = datetime.now()
midnight = datetime.combine(now + timedelta(days=1), datetime.min.time())
remaining_time = midnight - now
app.config['PERMANENT_SESSION_LIFETIME'] = remaining_time

# Initialize APScheduler
scheduler = APScheduler()
scheduler.init_app(app)


def start_game_job():
    with app.app_context():
        session_data_emotes.clear()
        reset_correct_guesses_counter()
        current_app.logger.info('Setting restart_game flag to True for all sessions')
        for session_id in session_data_emotes:
            session_data_emotes[session_id] = session_data_emotes.get(session_id, {})
            session_data_emotes[session_id]['restart_game'] = True
        new_seed = generate_seed()
        current_app.config['seed'] = new_seed
        current_app.logger.info(f'Setting new seed: {new_seed}')


@scheduler.task('cron', id='start_game', hour='00', minute='00', second='00')  # Run every minute for testing
def emotes_scheduled_start_job():
    start_game_job()


@scheduler.task('cron', id='clear_session', hour='00', minute='00', second='00')
def categories_scheduled_start_job():
    with app.app_context():
        current_app.logger.info('Clearing session data for all users')
        session_data.clear()
        reset_completion_count()
        new_seed_categories = generate_seed_categories()
        current_app.config['seed_categories'] = new_seed_categories
        current_app.logger.info(f'Setting new seed: {new_seed_categories}')
        initialize_streamer()


@scheduler.task('cron', id='clear_quotes_session', hour='00', minute='00', second='00')
def quotes_scheduled_start_job():
    with app.app_context():
        current_app.logger.info('Clearing session data for all users')
        session_data.clear()
        reset_correct_guesses_count()
        new_seed_quote = generate_seed_quote()
        current_app.config['seed_quote'] = new_seed_quote
        current_app.logger.info(f'Setting new seed: {new_seed_quote}')
        initialize_quote()

if __name__ == "__main__":
    scheduler.start()
    app.run(debug=True)
