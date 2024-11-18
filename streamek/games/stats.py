import os
import json
import uuid
from flask import session
from datetime import datetime, timedelta
import threading

user_stats_file = 'website/data/user_stats.json'

# Load user statistics from the file
file_lock = threading.Lock()


# Modify the save_user_stats function to use the lock
def save_user_stats(user_stats):
    try:
        with file_lock:
            with open(user_stats_file, 'w', encoding='utf-8') as file:
                json.dump(user_stats, file, indent=4)
    except IOError as e:
        print(f"Error saving user stats: {e}")


# Similarly, apply the lock in the load_user_stats function
def load_user_stats():
    with file_lock:
        if os.path.exists(user_stats_file):
            try:
                with open(user_stats_file, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                print("Error: Invalid JSON format in user_stats.json.")
                return {}
        return {}


# Calculate the global average attempt count for all users
def calculate_global_average_attempts(game_type):
    user_stats = load_user_stats()
    total_attempts = 0
    total_games = 0

    # Loop through all users and sum the attempts and games played for the specified game type
    for user_data in user_stats.values():
        if game_type in user_data:
            total_attempts += user_data[game_type]["total_attempts"]
            total_games += user_data[game_type]["games_played"]

    # Avoid division by zero
    if total_games > 0:
        return total_attempts / total_games
    return 0.0


# Get the current user ID or create a new one
def get_user_id():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    session.permanent = True
    return session['user_id']


# Update user statistics based on the outcome of a game
def update_user_stats(attempts, won, first_try, game_type):
    user_id = get_user_id()  # Get or create user ID
    user_stats = load_user_stats()  # Load existing stats
    today = datetime.now().strftime("%Y-%m-%d")  # Get today's date

    # Initialize user if not present in user_stats
    if user_id not in user_stats:
        user_stats[user_id] = {
            "categories": init_game_stats(),
            "quotes": init_game_stats(),
            "avatars": init_game_stats(),
            "emotes": init_game_stats(),
            "stats": init_game_stats()  # Initialize "stats"
        }

    # Ensure the game_type key exists for the user
    if game_type not in user_stats[user_id]:
        user_stats[user_id][game_type] = init_game_stats()

    # Get game stats for the current game type
    user_data = user_stats[user_id][game_type]

    # Check if user has already played today and won
    if user_data['last_played'] == today and user_data.get('won_today', True):
        return

    # Increment games_played if it's a new day
    if user_data['last_played'] != today:
        user_data['games_played'] += 1

        # Check if it's a consecutive day
        if user_data['last_played'] == (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"):
            user_data['daily_series'] += 1
        else:
            user_data['daily_series'] = 1

        # Update longest series if necessary
        if user_data['daily_series'] > user_data['longest_series']:
            user_data['longest_series'] = user_data['daily_series']

    # Update stats based on whether the game was won
    if won:
        user_data['won_today'] = True
        user_data['games_won'] += 1
        user_data['total_attempts'] += attempts
        user_data['average_attempt_count'] = user_data['total_attempts'] / user_data['games_played']

        if first_try:
            user_data['first_try_wins'] += 1
    else:
        user_data['won_today'] = False

    # Update last played date
    user_data['last_played'] = today

    # Save updated statistics
    user_stats[user_id][game_type] = user_data
    save_user_stats(user_stats)

    # Calculate the global average attempt count for comparison
    global_avg_attempts = calculate_global_average_attempts(game_type)
    user_avg_attempts = user_data['average_attempt_count']

    # Return this data for the template
    return user_avg_attempts, global_avg_attempts


# Initialize a new game statistics structure
def init_game_stats():
    return {
        "games_played": 0,
        "games_won": 0,
        "total_attempts": 0,
        "average_attempt_count": 0.0,
        "first_try_wins": 0,
        "daily_series": 0,
        "longest_series": 0,
        "last_played": "",
        "won_today": False
    }
