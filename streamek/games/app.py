from flask import Flask, jsonify, session, g, current_app, request, send_from_directory, render_template
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
from avatar import avatar_app, avatar_reset_correct_guesses_count, initialize_avatar
from stats import get_user_id, load_user_stats, update_user_stats, init_game_stats


def generate_seed():
    return secrets.randbits(32)


def generate_seed_categories():
    return uuid.uuid4().int & (1 << 32) - 1


def generate_seed_quote():
    return (uuid.uuid4().int & (1 << 30) - 3) ^ 0xABCDEF


def generate_seed_avatar():
    return (uuid.uuid4().int & (1 << 30) - 10) ^ 0x123456


app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.template_folder = '../templates'
app.static_folder = '../static'
app.secret_key = 'supersecretkey'
app.config['seed'] = generate_seed()
app.config['seed_categories'] = generate_seed_categories()
app.config['seed_quote'] = generate_seed_quote()
app.config['seed_avatar'] = generate_seed_avatar()

app.register_blueprint(main_app)
app.register_blueprint(emotes_app)
app.register_blueprint(words_app)
app.register_blueprint(categories_app)
app.register_blueprint(quote_app)
app.register_blueprint(policy_app)
app.register_blueprint(avatar_app)

# Global dictionary to simulate session data
session_data = {}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365 * 100)
app.config.update(
    SESSION_COOKIE_SECURE=True,   # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY=True, # Prevent client-side scripts from accessing the cookie
    SESSION_COOKIE_SAMESITE='Lax' # Restrict cross-site request sharing of the cookie
)

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
    session.permanent = True
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
# now = datetime.now()
# midnight = datetime.combine(now + timedelta(days=1), datetime.min.time())
# remaining_time = midnight - now
# app.config['PERMANENT_SESSION_LIFETIME'] = remaining_time

# Initialize APScheduler
scheduler = APScheduler()
scheduler.init_app(app)


@app.route('/api/game-status', methods=['GET'])
def get_game_status():
    # Check if the game is flagged as started in session_data_emotes or a global variable
    game_started = any(session.get('restart_game', False) for session in session_data_emotes.values())

    return jsonify({
        'game_started': game_started
    })


@app.route('/api/reset-game-flag', methods=['POST'])
def reset_game_flag():
    for session_id in session_data_emotes:
        session_data_emotes[session_id]['restart_game'] = False
    return jsonify({'status': 'success'})



def start_game_job():
    with app.app_context():
        reset_correct_guesses_counter()
        current_app.logger.info('Setting restart_game flag to True for all sessions')
        new_seed = generate_seed()
        current_app.config['seed'] = new_seed
        current_app.logger.info(f'Setting new seed: {new_seed}')

        # Update session data for all active sessions
        for session_id in session_data_emotes:
            session_data_emotes[session_id] = session_data_emotes.get(session_id, {})
            session_data_emotes[session_id]['restart_game'] = True

            # Set game state in session data
            session_data_emotes[session_id]['game_state'] = {
                'emojiIndex': 0,
                'attemptsCount': 0,
                'congratulationsVisible': False
            }
            current_app.logger.info(f'Updated game state for session: {session_id}')


@scheduler.task('cron', id='start_game', hour='00', minute='00', second='00')  # Run every minute for testing
def emotes_scheduled_start_job():
    start_game_job()


@scheduler.task('cron', id='clear_session', hour='00', minute='00', second='00')
def categories_scheduled_start_job():
    with app.app_context():
        current_app.logger.info('Clearing session data for all users')
        for session_id, user_session in session_data.items():
            if 'guessed_streamers' in user_session:
                user_session.pop('guessed_streamers', None)
            if 'guessed_summaries' in user_session:
                user_session.pop('guessed_summaries', None)
            if 'hidden_streamer' in user_session:
                user_session.pop('hidden_streamer', None)
            if 'success_message' in user_session:
                user_session.pop('success_message', None)
            if 'attempt_count' in user_session:
                user_session.pop('attempt_count', None)
            if 'available_streamers' in user_session:
                user_session.pop('available_streamers', None)
        reset_completion_count()
        new_seed_categories = generate_seed_categories()
        current_app.config['seed_categories'] = new_seed_categories
        current_app.logger.info(f'Setting new seed: {new_seed_categories}')
        initialize_streamer()


@scheduler.task('cron', id='clear_quotes_session', hour='00', minute='00', second='00')
def quotes_scheduled_start_job():
    with app.app_context():
        current_app.logger.info('Clearing session data for all users')
        for session_id, user_session in session_data.items():
            user_session.pop('correct_guess_data', None)
            user_session.pop('quote_result', None)
            user_session.pop('guessed_quotes', None)
            user_session.pop('guesses_counter', None)
            user_session.pop('available_streamers_quote', None)
            user_session.pop('hint_used', None)
            user_session.pop('correct_guess_count', None)
        reset_correct_guesses_count()
        new_seed_quote = generate_seed_quote()
        current_app.config['seed_quote'] = new_seed_quote
        current_app.logger.info(f'Setting new seed: {new_seed_quote}')
        initialize_quote()


@scheduler.task('cron', id='clear_avatar_session', hour='00', minute='00', second='00')
def avatar_scheduled_start_job():
    with app.app_context():
        current_app.logger.info('Clearing session data for all users')
        for session_id, user_session in session_data.items():
            if 'available_streamers_avatar' in user_session:
                user_session.pop('available_streamers_avatar', None)
            if 'guessed_avatars' in user_session:
                user_session.pop('guessed_avatars', None)
            if 'avatar_result' in user_session:
                user_session.pop('avatar_result', None)
            if 'avatar_guesses_counter' in user_session:
                user_session.pop('avatar_guesses_counter', None)
            if 'avatar_correct_guess_count' in user_session:
                user_session.pop('avatar_correct_guess_count', None)
            if 'zoom_level' in user_session:
                user_session.pop('zoom_level', None)
        avatar_reset_correct_guesses_count()
        new_seed_avatar = generate_seed_avatar()
        current_app.config['seed_avatar'] = new_seed_avatar
        current_app.logger.info(f'Setting new seed: {new_seed_avatar}')
        initialize_avatar()


@app.route('/user_statistics')
def user_statistics():
    try:
        user_id = get_user_id()
        user_stats = load_user_stats()

        # Provide default stats structure if user_id not present in user_stats
        user_data = user_stats.get(user_id, {
            "categories": init_game_stats(),
            "quotes": init_game_stats(),
            "avatars": init_game_stats(),
            "emotes": init_game_stats()
        })
    except Exception as e:
        print(f"Error loading user statistics: {e}")
        user_data = {
            "categories": init_game_stats(),
            "quotes": init_game_stats(),
            "avatars": init_game_stats(),
            "emotes": init_game_stats()
        }

    return render_template('user_statistics.html', user_data=user_data)


@app.route('/update_user_stats', methods=['POST'])
def update_user_stats_route():
    try:
        data = request.json
        attempts = data.get('attempts')
        won = data.get('won')
        first_try = data.get('first_try')
        game_type = 'emotes'  # Hardcoded for this context

        # Call the update_user_stats function
        update_user_stats(attempts, won, first_try, game_type)
    except Exception as e:
        print(f"Error updating user statistics: {e}")
        # Return a failure response if there's an issue
        return jsonify({'status': 'failure', 'error': str(e)}), 500

    return jsonify({'status': 'success'})


if __name__ == "__main__":
    scheduler.start()
    app.run(debug=True)
