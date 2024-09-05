import csv
import json
import os.path

# Function to update streamers' JSON data
def update_streamers_json(initial_data, csv_data, starting_years):
    updated_data = initial_data
    csv_streamers = set(row['Channel'] for row in csv_data)

    for row in csv_data:
        channel = row['Channel']
        start_year = starting_years.get(channel, [None])[0]
        top_games = row['Top Games'].split(', ')  # Split the top games string into a list
        top_games_str = ", ".join(top_games[:2])  # Join the top two games into a single string

        if channel in updated_data['streamers']:
            # Update existing streamer data, but do not change the "Płeć" field
            updated_data['streamers'][channel].update({
                "Image": row['Image URL'],
                "Top 2 Streamowane Gry": top_games_str,
                "Największa liczba widzów": int(row['Peak viewers'].replace(',', '').split('(')[0]),
                "Średnia liczba widzów": int(row['Average viewers'].replace(',', '').split('(')[0]),
                "Kiedy zaczął streamować": start_year,
                "Liczba obserwujących": int(row['Followers'].replace(',', ''))
            })
        else:
            # Add new streamer data
            updated_data['streamers'][channel] = {
                "Image": row['Image URL'],
                "Płeć": 'M',  # Set Płeć to 'M' for new streamers
                "Walczył we freak fightach": 'Nie',
                "Top 2 Streamowane Gry": top_games_str,
                "Największa liczba widzów": int(row['Peak viewers'].replace(',', '').split('(')[0]),
                "Średnia liczba widzów": int(row['Average viewers'].replace(',', '').split('(')[0]),
                "Kiedy zaczął streamować": start_year,
                "Liczba obserwujących": int(row['Followers'].replace(',', ''))
            }

    for channel in list(updated_data['streamers']):
        if channel not in csv_streamers:
            del updated_data['streamers'][channel]

    return updated_data

# Function to read JSON data from file
def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as jsonfile:
        return json.load(jsonfile)

# Function to write JSON data to file
def write_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=4)

# Function to update emotes JSON data
def update_emotes_json(csv_data, json_file):
    # Read existing JSON data if file exists
    if file_exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as jsonfile:
            streamers = json.load(jsonfile)
    else:
        streamers = []

    csv_streamer_names = set(row['Channel'] for row in csv_data)

    for row in csv_data:
        streamer_name = row['Channel']
        image_url = row['Image URL']
        existing_streamer = next((s for s in streamers if s['streamer'] == streamer_name), None)
        if existing_streamer is None:
            streamer = {
                'streamer': streamer_name,
                'image_url': image_url,
                'emotes': []
            }
            streamers.append(streamer)
        else:
            existing_streamer['image_url'] = image_url

    write_json(streamers, json_file)

# Function to check if a file exists
def file_exists(file_path):
    return os.path.exists(file_path)

# Define file paths
initial_json_file = '../data/updated_streamers.json'
starting_years_file = '../data/channel_changes.json'
csv_file = '../data/sullygnome_data.csv'
emotes_json_file = '../data/data_emoji.json'

# Read initial JSON data
initial_json_data = read_json(initial_json_file)

# Read starting years from file
starting_years_data = read_json(starting_years_file)

# Read CSV data
with open(csv_file, newline='', encoding='utf-8') as csvfile:
    csv_data = list(csv.DictReader(csvfile))

# Update streamers JSON data
updated_streamers_json = update_streamers_json(initial_json_data, csv_data, starting_years_data)

# Write updated streamers JSON data to file
write_json(updated_streamers_json, initial_json_file)

# Update emotes JSON data
update_emotes_json(csv_data, emotes_json_file)

print("Data updated successfully!")
