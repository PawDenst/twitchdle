from flask import Flask, render_template, request, jsonify, session, Blueprint, g, current_app, flash
import csv
import random
from stats import update_user_stats
import json
from stats import update_user_stats

stream_stats_app = Blueprint('stream_stats_app', __name__)
used_stats_file = 'website/data/used_stats.json'
stats_correct_guesses_count_file = 'website/data/stats_correct_count.json'
game_state = {
        'current_streamer': None,  # Set to None initially
        'wrong_guesses': 0,  # Track the number of wrong guesses
    }

def stats_read_correct_guesses_count():
    with open(stats_correct_guesses_count_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['stats_correct_guesses_count']


def stats_update_correct_guesses_count():
    count = stats_read_correct_guesses_count()
    count += 1
    with open(stats_correct_guesses_count_file, 'w', encoding='utf-8') as file:
        json.dump({"stats_correct_guesses_count": count}, file)
    return count


def stats_reset_correct_guesses_count():
    with open(stats_correct_guesses_count_file, 'w') as file:
        json.dump({'stats_correct_guesses_count': 0}, file)


def load_streamers():
    # Load streamers data from the JSON file
    with open('website/data/data_quote.json', 'r', encoding='utf-8') as file:
        streamers_list = json.load(file)
        return {streamer['streamer']: streamer for streamer in streamers_list}


def load_used_stats():
    try:
        with open(used_stats_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Save used stats to file
def save_used_stats(used_stats):
    with open(used_stats_file, 'w', encoding='utf-8') as file:
        json.dump(used_stats, file)


def load_streamer_data():
    streamer_data = {}

    with open('website/data/streamer_data.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            if len(row) < 3:
                continue

            streamer = row[0].strip()
            stat_category = row[1].strip()

            if streamer not in streamer_data:
                streamer_data[streamer] = {
                    'Twitch': [], '7TV': [], 'BTTV': [], 'FFZ': [], 'Commands': []
                }

            emotes_and_commands = row[2:]

            if any(cat in stat_category for cat in ['Twitch', '7TV', 'BTTV', 'FFZ']):
                for i in range(0, len(emotes_and_commands), 3):
                    if i + 2 >= len(emotes_and_commands):
                        break
                    emote_name = emotes_and_commands[i].strip()
                    emote_stats = emotes_and_commands[i + 1].strip()
                    emote_url = emotes_and_commands[i + 2].strip()

                    if emote_name and emote_stats and emote_url:
                        emote_data = {
                            'name': emote_name,
                            'stats': emote_stats,
                            'url': emote_url
                        }

                        if 'Twitch' in stat_category:
                            streamer_data[streamer]['Twitch'].append(emote_data)
                        elif '7TV' in stat_category:
                            streamer_data[streamer]['7TV'].append(emote_data)
                        elif 'BTTV' in stat_category:
                            streamer_data[streamer]['BTTV'].append(emote_data)
                        elif 'FFZ' in stat_category:
                            streamer_data[streamer]['FFZ'].append(emote_data)

            elif 'Commands' in stat_category:
                for i in range(0, len(emotes_and_commands), 2):
                    if i + 1 >= len(emotes_and_commands):
                        break
                    command_name = emotes_and_commands[i].strip()
                    command_stats = emotes_and_commands[i + 1].strip()

                    if command_name and command_stats:
                        command_data = {
                            'name': command_name,
                            'stats': command_stats
                        }
                        streamer_data[streamer]['Commands'].append(command_data)

    return streamer_data


streamer_data = load_streamer_data()


def initialize_stream_stats():
    global game_state

    # Load streamer data and used streamers
    streamer_dict = load_streamer_data()  # Load dictionary with streamers as keys
    used_stats = load_used_stats()  # Load previously used streamers

    # Get list of available streamers by filtering out used streamers
    available_streamers = [streamer for streamer in streamer_dict.keys() if streamer not in used_stats]

    # Reset used streamers if all have been used
    if not available_streamers:
        used_stats = []
        available_streamers = list(streamer_dict.keys())  # Use all streamers again
        save_used_stats(used_stats)

    streamers = load_streamers()
    selected_streamer = None

    # Loop until a valid streamer is found in streamer_data
    while available_streamers:
        # Seed random for reproducibility
        seed_stats = current_app.config['seed_stats']
        random.seed(seed_stats)
        candidate = random.choice(available_streamers)

        # If candidate exists in streamer_data, select it as the current streamer
        if candidate in streamer_dict:
            selected_streamer = candidate
            used_stats.append(selected_streamer.lower())  # Store in lowercase to avoid case mismatches
            break
        else:
            # If candidate does not exist, add it to used_stats and remove from available list
            used_stats.append(candidate.lower())
            available_streamers.remove(candidate)

    # Save the updated used_stats
    save_used_stats(used_stats)

    # Set up the selected streamer and image URL
    if selected_streamer:
        selected_streamer_image_url = streamers[selected_streamer]['image_url'] if selected_streamer in streamers else None
        game_state['current_streamer_image_url'] = selected_streamer_image_url
        game_state['current_streamer'] = selected_streamer
        game_state['wrong_guesses'] = 0
        print(f"New streamer selected for stream stats emote: {selected_streamer}")
    else:
        print("No valid streamer found. Please check your data.")



@stream_stats_app.before_app_request
def before_first_request():
    if game_state is None:
        initialize_stream_stats()


@stream_stats_app.route('/stream_stats', methods=['GET', 'POST'])
def stream_stats():
    streamers = load_streamers()  # Load streamers data
    user_session = g.session_data  # Access the session data

    # Initialize session variables if not already set
    if 'available_streamers_stats' not in user_session:
        user_session['available_streamers_stats'] = list(streamers.keys())
    if 'guessed_stats' not in user_session:
        user_session['guessed_stats'] = []
    if 'stats_result' not in user_session:
        user_session['stats_result'] = None
    if 'stats_guesses_counter' not in user_session:
        user_session['stats_guesses_counter'] = 0
    if 'stats_correct_guess_count' not in user_session:
        user_session['stats_correct_guess_count'] = 0
    if 'wrong_guesses' not in user_session:
        user_session['wrong_guesses'] = 0  # Initialize wrong_guesses for the session

    # Generate lowercase maps for available streamers (lowercase for comparison, original for display)
    available_streamers_lower = {name.lower(): name for name in user_session['available_streamers_stats']}

    # Initialize current streamer when the game starts (if not set)
    if game_state['current_streamer'] is None:
        initialize_stream_stats()

    current_streamer = game_state['current_streamer']
    current_streamer_image_url = game_state['current_streamer_image_url']
    streamer_hints = streamer_data[current_streamer]

    if request.method == 'POST':
        guess = request.form.get('streamer').strip().lower()  # Get user's guess in lowercase

        if guess in available_streamers_lower:
            # Get the original casing for the guessed streamer
            guessed_streamer = available_streamers_lower[guess]
            user_session['stats_guesses_counter'] += 1

            # Check if the guess is correct (compare lowercase)
            if guessed_streamer.lower() == game_state['current_streamer'].lower():
                user_session['stats_result'] = 'correct'
                user_session['wrong_guesses'] = 5
                user_session['stats_correct_guess_count'] = stats_update_correct_guesses_count()
                won = True
                first_try = user_session['stats_guesses_counter'] == 1
                animation_class = 'correct-guess skok'
                user_session['stats_correct_guess_count'] += 1
                try:
                    update_user_stats(user_session['stats_guesses_counter'], won, first_try, 'stats')
                except Exception as e:
                    print(f"Error updating user stats: {e}")  # Handle the error (optional logging)
            else:
                animation_class = 'shake'
                won = False
                user_session['wrong_guesses'] += 1  # Increment session-specific wrong guesses
                user_session['stats_result'] = 'incorrect'
                try:
                    update_user_stats(user_session['stats_guesses_counter'], won, False, 'stats')
                except Exception as e:
                    print(f"Error updating user stats: {e}")  # Handle the error (optional logging)

            # Add guessed streamer to session and update stats
            user_session['guessed_stats'].insert(0, {
                'name': guessed_streamer,  # This is in original casing
                'image': streamers[guessed_streamer]['image_url'],  # Get image URL using original casing
                'animation_class': animation_class
            })
            user_session['available_streamers_stats'].remove(guessed_streamer)  # Remove from available list
            available_streamers_lower.pop(guess)  # Remove from lowercase map

        else:
            flash('Invalid guess. Please select a valid streamer from the list.', 'error')

    # Prepare hints based on the session's wrong guesses
    hints_to_show = user_session['wrong_guesses'] + 1
    twitch_hint = streamer_hints['Twitch'][:hints_to_show]
    tv_hint = streamer_hints['7TV'][:hints_to_show]
    bttv_hint = streamer_hints['BTTV'][:hints_to_show]
    ffz_hint = streamer_hints['FFZ'][:hints_to_show]
    command_hint = streamer_hints['Commands'][:hints_to_show]
    command_hint_name = [command['name'] for command in streamer_hints['Commands'][:hints_to_show]]

    user_session['stats_correct_guess_count'] = stats_read_correct_guesses_count()
    # Render the page with the correct data
    return render_template(
        'stream_stats.html',
        twitch_hint=twitch_hint,
        tv_hint=tv_hint,
        bttv_hint=bttv_hint,
        ffz_hint=ffz_hint,
        command_hint=command_hint,
        command_hint_name=command_hint_name,
        wrong_guesses=user_session['wrong_guesses'],
        correct=False,
        stats_result=user_session['stats_result'],
        guessed_stats=user_session['guessed_stats'],  # Display guessed stats with correct casing
        stats_guesses_counter=user_session['stats_guesses_counter'],
        stats_correct_guess_count=user_session['stats_correct_guess_count'],
        current_streamer=current_streamer,
        current_streamer_image_url=current_streamer_image_url
    )


@stream_stats_app.route('/fetch_streamer_stats', methods=['GET'])
def fetch_streamer_stats():
    user_session = g.session_data
    available_streamers_stats = user_session.get('available_streamers_stats', [])
    streamers = load_streamers()
    filtered_streamers = {k: {'Image': v['image_url']} for k, v in streamers.items() if k in available_streamers_stats}
    return jsonify({"streamers": filtered_streamers})