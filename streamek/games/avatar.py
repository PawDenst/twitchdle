import base64
from flask import Flask, render_template, request, jsonify, session, Blueprint, g, current_app, flash
import json
import random
import requests
from io import BytesIO
from PIL import Image
from stats import update_user_stats

avatar_app = Blueprint('avatar_app', __name__)
used_avatars_file = 'website/data/used_avatars.json'
avatar_correct_guesses_count_file = 'website/data/avatar_correct_count.json'
daily_avatar = None


def avatar_read_correct_guesses_count():
    with open(avatar_correct_guesses_count_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data['avatar_correct_guesses_count']


def avatar_update_correct_guesses_count():
    count = avatar_read_correct_guesses_count()
    count += 1
    with open(avatar_correct_guesses_count_file, 'w', encoding='utf-8') as file:
        json.dump({"avatar_correct_guesses_count": count}, file)
    return count


def avatar_reset_correct_guesses_count():
    with open(avatar_correct_guesses_count_file, 'w') as file:
        json.dump({'avatar_correct_guesses_count': 0}, file)


def load_streamers():
    # Load streamers data from the JSON file
    with open('website/data/data_quote.json', 'r', encoding='utf-8') as file:
        streamers_list = json.load(file)
        return {streamer['streamer'].lower(): streamer for streamer in streamers_list}


def load_used_avatar():
    try:
        with open(used_avatars_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Save used avatars to file
def save_used_avatars(used_avatars):
    with open(used_avatars_file, 'w', encoding='utf-8') as file:
        json.dump(used_avatars, file)


def fetch_image(image_url):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    return img


def get_cropped_image(img, crop_box):
    return img.crop(crop_box)


def initialize_avatar():
    global daily_avatar

    # Load avatars and used avatars
    avatars_dict = load_streamers()  # Load dictionary with streamers as keys
    used_avatars = load_used_avatar()

    # Get list of available avatars by filtering out those in used_avatars
    available_avatars = [avatar for streamer, avatar in avatars_dict.items() if streamer not in used_avatars]

    # Reset used avatars if all avatars have been used
    if not available_avatars:
        used_avatars = []
        available_avatars = list(avatars_dict.values())  # Use all avatars again
        save_used_avatars(used_avatars)

    # Choose a new avatar from available ones
    seed_avatar = current_app.config['seed_avatar']
    random.seed(seed_avatar)
    daily_avatar = random.choice(available_avatars)
    daily_avatar['word_count'] = len(daily_avatar['streamer'].split())  # Assuming you want word count for the streamer's name

    # Save the new avatar as used
    used_avatars.append(daily_avatar['streamer'].lower())  # Store the lowercase version to match the keys
    save_used_avatars(used_avatars)

    print(f"New daily avatar initialized: {daily_avatar['streamer']} with image URL: {daily_avatar['image_url']}")


@avatar_app.before_app_request
def before_first_request():
    if daily_avatar is None:
        initialize_avatar()


def generate_cropped_image(user_session):
    zoom_level = user_session.get('zoom_level', 5)  # Retrieve zoom level from session

    # Use the globally shared `daily_avatar` for all users
    current_image_url = daily_avatar['image_url']
    current_image = fetch_image(current_image_url)

    # Preserve the cropped image even after the player has won
    width, height = current_image.size

    # Modify the crop dimensions for zoom out (increase crop size as zoom_level increases)
    # You can adjust the multiplier as needed to control how quickly it zooms out
    scale_factor = (zoom_level + 3)  # Larger zoom_level means zoom out
    crop_width = width // scale_factor
    crop_height = height // scale_factor

    # Adjust the crop position to keep it centered as you zoom out
    crop_x = (width - crop_width) // 2  # Center horizontally
    crop_y = (height - crop_height) // 2  # Center vertically

    # Define the crop box (left, upper, right, lower)
    crop_box = (crop_x, crop_y, crop_x + crop_width, crop_y + crop_height)
    cropped_img = get_cropped_image(current_image, crop_box)

    img_bytes = BytesIO()
    cropped_img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    return img_base64


@avatar_app.route('/avatar', methods=['GET', 'POST'])
def avatar():
    streamers = load_streamers()
    user_session = g.session_data

    # Initialize session variables if not already set
    if 'available_streamers_avatar' not in user_session:
        user_session['available_streamers_avatar'] = list(streamers.keys())
    if 'guessed_avatars' not in user_session:
        user_session['guessed_avatars'] = []
    if 'avatar_result' not in user_session:
        user_session['avatar_result'] = None
    if 'avatar_guesses_counter' not in user_session:
        user_session['avatar_guesses_counter'] = 0
    if 'avatar_correct_guess_count' not in user_session:
        user_session['avatar_correct_guess_count'] = 0

    # Use global `daily_avatar` for current streamer and image
    current_streamer = daily_avatar['streamer'].lower()
    current_image_url = daily_avatar['image_url']

    # Restore session variable for zoom level
    zoom_level = user_session.get('zoom_level', 5)

    # Generate the available streamers map
    available_streamers_lower = {name.lower(): name for name in user_session['available_streamers_avatar']}
    guessed_avatars_lower = [g['name'].lower() for g in user_session['guessed_avatars']]

    # Generate cropped image
    image_data = generate_cropped_image(user_session)

    if request.method == 'POST':
        guess = request.form['streamer'].strip().lower()
        if guess in available_streamers_lower:
            guess = available_streamers_lower[guess]

            # Check if the guessed streamer exists in the streamers data
            if guess in available_streamers_lower:
                streamer_data = streamers[guess]
                image_url = streamer_data['image_url']  # Get the streamer's image URL

                if guess not in guessed_avatars_lower:
                    user_session['avatar_guesses_counter'] += 1
                    guessed_avatars_lower.append(guess)

                    # Check if the guessed avatar is already in the guessed_avatars list
                    if not any(avatar['name'].lower() == guess for avatar in user_session['guessed_avatars']):
                        if guess == current_streamer:
                            user_session['avatar_result'] = 'correct'
                            animation_class = 'correct-guess skok'
                            user_session['correct_guess_count'] = avatar_update_correct_guesses_count()
                            won = True
                            first_try = user_session['avatar_guesses_counter'] == 1
                            try:
                                update_user_stats(user_session['avatar_guesses_counter'], won, first_try, 'avatars')
                            except Exception as e:
                                print(f"Error updating user stats: {e}")  # Handle the error (optional logging)

                        else:
                            user_session['avatar_result'] = 'incorrect'
                            animation_class = 'shake'
                            won = False
                            try:
                                update_user_stats(user_session['avatar_guesses_counter'], won, False, 'avatars')
                            except Exception as e:
                                print(f"Error updating user stats: {e}")  # Handle the error (optional logging)
                            if zoom_level >= -1:
                                zoom_level -= 1  # Decrease zoom level on wrong guess
                                user_session['zoom_level'] = zoom_level  # Save zoom level in session
                            # Generate cropped image with increased zoom level
                            image_data = generate_cropped_image(user_session)

                        # Append the guess to the guessed_avatars list with its image
                        user_session['guessed_avatars'].insert(0, {
                            'name': streamer_data['streamer'],
                            'image': image_url,
                            "animation_class": animation_class
                        })
            else:
                flash('Invalid guess. Please select a streamer from the list.', 'error')

    user_session['avatar_correct_guess_count'] = avatar_read_correct_guesses_count()
    return render_template('avatar.html', image_data=image_data,
                           avatar_result=user_session['avatar_result'],
                           guessed_avatars=user_session['guessed_avatars'],
                           avatar_guesses_counter=user_session['avatar_guesses_counter'],
                           avatar_correct_guess_count=user_session['avatar_correct_guess_count'],
                           current_streamer=current_streamer,
                           current_image_url=current_image_url)


@avatar_app.route('/fetch_streamer_avatar', methods=['GET'])
def fetch_streamer_avatar():
    user_session = g.session_data
    available_streamers_avatar = user_session.get('available_streamers_avatar', [])
    streamers = load_streamers()
    filtered_streamers = {k: {'Image': v['image_url']} for k, v in streamers.items() if k in available_streamers_avatar}
    return jsonify({"streamers": filtered_streamers})
