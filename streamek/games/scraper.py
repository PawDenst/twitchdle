from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import csv
import json
import time


def check_viewer_change(channel, year, driver):
    channel_url = f'https://sullygnome.com/channel/{channel}/{year}'
    driver.get(channel_url)
    channel_page_source = driver.page_source
    channel_soup = BeautifulSoup(channel_page_source, 'html.parser')

    # Find the average viewers element
    avg_viewers_panel = channel_soup.find('div', class_='InfoStatPanelTL')  # You might need to adjust this selector
    if avg_viewers_panel:
        avg_viewers_text = avg_viewers_panel.text.strip()
        try:
            avg_viewers = int(avg_viewers_text.replace(',', ''))  # Remove commas and convert to integer
            return avg_viewers > 20
        except ValueError:
            return False  # Handle the case where conversion fails (e.g., text isn't a number)
    return False

def scrape_top_games(channel, driver):
    game_url = f'https://sullygnome.com/channel/{channel}/30/games'
    driver.get(game_url)
    time.sleep(0.5)  # Wait for page to load
    game_page_source = driver.page_source
    game_soup = BeautifulSoup(game_page_source, 'html.parser')
    table = game_soup.find('table')
    top_games = []
    if table:
        rows = table.find_all('tr')[1:]  # Exclude the header row
        for row in rows[:2]:  # Get the top two games
            cells = row.find_all('td')
            top_game = cells[1].text.strip()  # Get the game name from the second column
            top_games.append(top_game)
    return top_games

channel_changes = {}
channel_games = {}

# Specify the URL of the page to scrape
url = 'https://sullygnome.com/channels/30/watched?language=pl'

# Configure Selenium WebDriver (ensure you have chromedriver installed)
driver = webdriver.Chrome()

# Load the webpage
driver.get(url)

# Select the 100 option from the dropdown
select = Select(driver.find_element(By.NAME, 'tblControl_length'))
select.select_by_value('50')

# Wait for the page to reload with the new number of entries
time.sleep(2)

# Extract the page source after JavaScript execution
page_source = driver.page_source

# Parse the HTML content of the page
soup = BeautifulSoup(page_source, 'html.parser')

# Find the table containing the data
table = soup.find('table')

if table:
    # Initialize a list to store channel data
    channel_data = []

    # Extract table rows
    rows = table.find_all('tr')[1:]  # Exclude the header row

    # Iterate through each row and extract the data
    for row in rows:
        # Extract data from each cell in the row
        cells = row.find_all('td')
        numer = cells[0].text.strip()
        image_url = cells[1].find('img')['src']  # Extract image URL from the second column
        channel = cells[2].text.strip()
        watch_time = cells[3].text.strip()
        stream_time = cells[4].text.strip()
        peak_viewers = cells[5].text.strip()
        average_viewers = cells[6].text.strip()
        followers = cells[7].text.strip()
        followers_gained = cells[8].text.strip()

        top_games = scrape_top_games(channel, driver)
        if top_games:
            channel_games[channel] = top_games

        for year in range(2015, 2025):
            if check_viewer_change(channel, year, driver):
                if channel not in channel_changes:
                    channel_changes[channel] = []
                channel_changes[channel].append(year)
                break

        # Store the extracted data in a dictionary
        channel_info = {
            'Numer': numer,
            'Channel': channel,
            'Image URL': image_url,
            'Watch time (hours)': watch_time,
            'Stream time (hours)': stream_time,
            'Peak viewers': peak_viewers,
            'Average viewers': average_viewers,
            'Followers': followers,
            'Followers gained': followers_gained,
            'Top Games': ', '.join(top_games)  # Add top games info to the dictionary, separated by comma
        }

        # Append the channel info to the list
        channel_data.append(channel_info)

    # Write the data to a CSV file
    with open('../data/sullygnome_data.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=channel_data[0].keys())
        writer.writeheader()
        writer.writerows(channel_data)

    print('Data successfully scraped and saved to sullygnome_data.csv')
else:
    print('No table found on the page.')

# Write the channel_changes dictionary to a JSON file
with open('../data/channel_changes.json', 'w', encoding='utf-8') as file:
    json.dump(channel_changes, file, ensure_ascii=False, indent=4)
print('Channel changes successfully saved to channel_changes.json')

# Close the WebDriver
driver.quit()
