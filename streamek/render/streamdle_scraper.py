from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import csv
import json
import time
import re

# Load streamer data
streamers_data_path = '../data/data_quote.json'
with open(streamers_data_path, 'r') as file:
    streamers_data = json.load(file)

# Extract streamer names into a list
streamer_names = [streamer['streamer'] for streamer in streamers_data]

# Initialize Selenium WebDriver (make sure to have the appropriate WebDriver for your browser)
driver = webdriver.Chrome()
output_file = '../data/streamer_data.csv'


def remove_repeated_commas(output_file):
    with open(output_file, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        cleaned_rows = []

        for row in reader:
            cleaned_row = re.sub(r',+', ',', ','.join(row)).split(',')
            cleaned_rows.append(cleaned_row)

    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(cleaned_rows)


# Function to scrape data from the specified streamer page
def scrape_streamer_data(streamer):
    url = f"https://stats.streamelements.com/c/{streamer.lower()}"
    driver.get(url)
    time.sleep(2)
    try:
        # Wait until the main content is loaded
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception as e:
        print(f"Page loading timeout or error for {streamer}: {e}")
        return {}

    # Use BeautifulSoup to parse the page source after it loads
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    data = {}

    # List of stats to scrape
    stats = ['Top Twitch Emotes', 'Top 7TV Emotes', 'Top BTTV Emotes', 'Top FFZ Emotes', 'Top Commands']

    for stat in stats:
        try:
            # Locate the stat div
            stat_div = soup.find('div', text=stat)
            if stat_div:
                # Get the parent div that contains the results
                parent_div = stat_div.find_parent('div', class_='c0167')
                # Find the top 5 entries based on positions
                entry_class = 'rowNoEmote' if stat == 'Top Commands' else 'rowHasEmote'
                entries = parent_div.find_all('div', class_=entry_class, limit=7)

                results = []
                for entry in entries:
                    entry_parts = entry.find_all('div')

                    if stat == 'Top Commands':
                        # Extract rank, name, and stats for commands
                        if len(entry_parts) >= 4:
                            rank = entry_parts[0].get_text(strip=True)
                            name = entry_parts[2].get_text(strip=True)
                            stats_value = entry_parts[3].get_text(strip=True).replace(u'\xa0', ' ')
                            results.append({'Rank': rank, 'Name': name, 'Stats': stats_value})
                    else:
                        # Extract data for emotes
                        if len(entry_parts) >= 5:
                            rank = entry_parts[0].get_text(strip=True)
                            name = entry_parts[4].get_text(strip=True).replace(u'\xa0', ' ')
                            stats_value = entry_parts[5].get_text(strip=True).replace(u'\xa0', ' ')
                            img_tag = entry.find('img')
                            img_url = img_tag['src'] if img_tag else 'No image'
                            results.append({'Rank': rank, 'Name': name, 'Stats': stats_value, 'ImageURL': img_url})

                data[stat] = results
            else:
                print(f"Stat '{stat}' not found for {streamer}.")
        except Exception as e:
            print(f"Error scraping '{stat}' for {streamer}: {e}")

    return data


# Dictionary to hold all streamer data
all_streamer_data = {}

# Scrape data for each streamer
for streamer in streamer_names:
    all_streamer_data[streamer] = scrape_streamer_data(streamer)

# Function to write data to CSV
def write_data_to_csv(output_file, streamer_data):
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = [
            'Streamer', 'stat',
            'Emote 1 Name', 'Emote 1 Stats', 'Emote 1 ImageURL',
            'Emote 2 Name', 'Emote 2 Stats', 'Emote 2 ImageURL',
            'Emote 3 Name', 'Emote 3 Stats', 'Emote 3 ImageURL',
            'Emote 4 Name', 'Emote 4 Stats', 'Emote 4 ImageURL',
            'Emote 5 Name', 'Emote 5 Stats', 'Emote 5 ImageURL',
            'Emote 6 Name', 'Emote 6 Stats', 'Emote 6 ImageURL',
            'Emote 7 Name', 'Emote 7 Stats', 'Emote 7 ImageURL',
            'Command 1 Name', 'Command 1 Stats',
            'Command 2 Name', 'Command 2 Stats',
            'Command 3 Name', 'Command 3 Stats',
            'Command 4 Name', 'Command 4 Stats',
            'Command 5 Name', 'Command 5 Stats',
            'Command 6 Name', 'Command 6 Stats',
            'Command 7 Name', 'Command 7 Stats'

        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for streamer_name, stats in streamer_data.items():
            for stat, entries in stats.items():
                if stat == 'Top Commands':
                    # Fill missing entries with empty strings if there are less than 5 commands
                    while len(entries) < 7:
                        entries.append({'Name': '', 'Stats': ''})

                    # Write only relevant data for commands, avoiding empty columns
                    writer.writerow({
                        'Streamer': streamer_name,
                        'stat': stat,
                        'Command 1 Name': entries[0]['Name'], 'Command 1 Stats': entries[0]['Stats'] or '',
                        'Command 2 Name': entries[1]['Name'], 'Command 2 Stats': entries[1]['Stats'] or '',
                        'Command 3 Name': entries[2]['Name'], 'Command 3 Stats': entries[2]['Stats'] or '',
                        'Command 4 Name': entries[3]['Name'], 'Command 4 Stats': entries[3]['Stats'] or '',
                        'Command 5 Name': entries[4]['Name'], 'Command 5 Stats': entries[4]['Stats'] or '',
                        'Command 6 Name': entries[5]['Name'], 'Command 6 Stats': entries[5]['Stats'] or '',
                        'Command 7 Name': entries[6]['Name'], 'Command 7 Stats': entries[6]['Stats'] or ''
                    })
                else:
                    # Fill missing entries with empty strings if there are less than 5 emotes
                    while len(entries) < 7:
                        entries.append({'Name': '', 'Stats': '', 'ImageURL': ''})

                    # Write the emote data
                    writer.writerow({
                        'Streamer': streamer_name,
                        'stat': stat,
                        'Emote 1 Name': entries[0]['Name'], 'Emote 1 Stats': entries[0]['Stats'],
                        'Emote 1 ImageURL': entries[0]['ImageURL'],
                        'Emote 2 Name': entries[1]['Name'], 'Emote 2 Stats': entries[1]['Stats'],
                        'Emote 2 ImageURL': entries[1]['ImageURL'],
                        'Emote 3 Name': entries[2]['Name'], 'Emote 3 Stats': entries[2]['Stats'],
                        'Emote 3 ImageURL': entries[2]['ImageURL'],
                        'Emote 4 Name': entries[3]['Name'], 'Emote 4 Stats': entries[3]['Stats'],
                        'Emote 4 ImageURL': entries[3]['ImageURL'],
                        'Emote 5 Name': entries[4]['Name'], 'Emote 5 Stats': entries[4]['Stats'],
                        'Emote 5 ImageURL': entries[4]['ImageURL'],
                        'Emote 6 Name': entries[5]['Name'], 'Emote 6 Stats': entries[5]['Stats'],
                        'Emote 6 ImageURL': entries[5]['ImageURL'],
                        'Emote 7 Name': entries[6]['Name'], 'Emote 7 Stats': entries[6]['Stats'],
                        'Emote 7 ImageURL': entries[6]['ImageURL']
                    })

# Write all scraped data to CSV
write_data_to_csv(output_file, all_streamer_data)

# Clean up and close the driver
driver.quit()
remove_repeated_commas(output_file)
