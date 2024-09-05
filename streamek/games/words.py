from flask import Flask, render_template, request, Blueprint, session
import random

words_app = Blueprint('words_app', __name__)

def load_text(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        text = file.read()
    return text

def initialize_game():
    session['incorrect_guesses'] = []
    session['bad_guesses_count'] = session.get('bad_guesses_count', 0)
    random.seed(42)
    text = load_text('ttv_transcription.txt')
    words = text.split()

    start_word_count = max(1, int(len(words) * 0.85))
    remaining_words = random.sample(words, len(words) - start_word_count)

    guessed_words = ["[ ]" if word in remaining_words else word for word in words]
    hint_used = False
    next_word_index = 0
    hints_used_count = 0

    return guessed_words, words, hint_used, next_word_index, hints_used_count


def provide_hint(guessed_words, words, next_word_index, hints_used_count):
    while next_word_index < len(words):
        hint_word = words[next_word_index]
        if hint_word.lower() not in (word.lower() for word in guessed_words):
            guessed_words_copy = guessed_words[:]
            for i, word in enumerate(words):
                if word.lower() == hint_word.lower():
                    guessed_words_copy[i] = hint_word
            return guessed_words_copy, hint_word, next_word_index + 1, hints_used_count + 1
        next_word_index += 1
    return guessed_words, None, next_word_index, hints_used_count

@words_app.route('/guessing-game', methods=['GET', 'POST'])
def guessing_game():
    if request.method == 'GET':
        guessed_words, words, hint_used, next_word_index, hints_used_count = initialize_game()
        return render_template('guessing_game.html', guessed_words=guessed_words, words=words,
                               hint_used=hint_used,
                               next_word_index=next_word_index, game_finished=False, streamer_guessed=False,
                               hints_used_count=hints_used_count, all_words_guessed=False,
                               incorrect_guesses=session.get('incorrect_guesses', []),
                               bad_guesses_count=session.get('bad_guesses_count', 0))
    elif request.method == 'POST':
        guessed_words = request.form.getlist('guessed_words[]')
        words = request.form.getlist('words[]')
        bad_guesses_count = session.get('bad_guesses_count', 0)
        next_word_index = int(request.form.get('next_word_index') or 0)
        hints_used_count = int(request.form.get('hints_used_count') or 0)

        if 'skip_stage' in request.form:
            guessed_words = words[:]
            all_words_guessed = True
            return render_template('guessing_game.html', guessed_words=guessed_words, words=words,
                                   bad_guesses_count=bad_guesses_count, hint_used=False,
                                   next_word_index=next_word_index, game_finished=False,
                                   hints_used_count=hints_used_count, all_words_guessed=all_words_guessed,
                                   streamer_guessed=False, incorrect_guesses=session.get('incorrect_guesses', []))

        if 'predefined_name' in request.form:
            correct_name = request.form['predefined_name'].strip().lower()
            predefined_name = "mammon"
            all_words_guessed = all(word != '[ ]' for word in guessed_words)
            if correct_name == predefined_name and all_words_guessed:
                return render_template('guessing_game.html', guessed_words=guessed_words, words=words,
                                       bad_guesses_count=bad_guesses_count, next_word_index=next_word_index,
                                       hints_used_count=hints_used_count, game_finished=True, streamer_guessed=True,
                                       all_words_guessed=all_words_guessed, incorrect_guesses=session.get('incorrect_guesses', []))
            else:
                return render_template('guessing_game.html', guessed_words=guessed_words, words=words,
                                       bad_guesses_count=bad_guesses_count, next_word_index=next_word_index,
                                       hints_used_count=hints_used_count, game_finished=True, streamer_guessed=False,
                                       all_words_guessed=all_words_guessed, incorrect_guesses=session.get('incorrect_guesses', []))

        if 'finish_game' in request.form or all(word != '[ ]' for word in guessed_words):
            return render_template('guessing_game.html', guessed_words=guessed_words, words=words,
                                   bad_guesses_count=bad_guesses_count, hint_used=False,
                                   next_word_index=next_word_index, game_finished=True,
                                   hints_used_count=hints_used_count, all_words_guessed=True,
                                   streamer_guessed=False, incorrect_guesses=session.get('incorrect_guesses', []))

        elif 'hint' in request.form:
            guessed_words, hint_word, next_word_index, hints_used_count = provide_hint(guessed_words, words, next_word_index, hints_used_count)
            all_words_guessed = all(word != '[ ]' for word in guessed_words)
            return render_template('guessing_game.html', guessed_words=guessed_words, words=words,
                                   bad_guesses_count=bad_guesses_count, hint_word=hint_word,
                                   next_word_index=next_word_index, game_finished=False,
                                   hints_used_count=hints_used_count, all_words_guessed=all_words_guessed,
                                   streamer_guessed=False, incorrect_guesses=session.get('incorrect_guesses', []))

        else:
            guess = request.form['guess'].strip().lower()
            correct_guesses = []

            for guess_word in guess.split():
                guess_word_lower = guess_word.lower()
                if guess_word_lower in map(str.lower, guessed_words):
                    correct_guesses.append('You already guessed {}'.format(guess_word))
                elif guess_word_lower in map(str.lower, words):
                    for idx, word in enumerate(words):
                        if guess_word_lower == word.lower():
                            guessed_words[idx] = word
                            correct_guesses.append(word)
                else:
                    if guess_word_lower not in session.get('incorrect_guesses', []):
                        # If the guess is not already in the guessed words, add it to incorrect guesses
                        bad_guesses_count += 1
                        session.setdefault('incorrect_guesses', []).append(guess_word_lower)

            hint_used = bad_guesses_count >= 3
            all_words_guessed = all(word != '[ ]' for word in guessed_words)

            # Store the updated guessed words and incorrect guesses in the session
            session['guessed_words'] = guessed_words
            session['bad_guesses_count'] = bad_guesses_count

            return render_template('guessing_game.html', guessed_words=guessed_words, words=words,
                                   correct_guesses=correct_guesses,
                                   hint_used=hint_used, next_word_index=next_word_index,
                                   game_finished=False, hints_used_count=hints_used_count,
                                   all_words_guessed=all_words_guessed, streamer_guessed=False,
                                   incorrect_guesses=session.get('incorrect_guesses', []),
                                   bad_guesses_count=session.get('bad_guesses_count', 0))