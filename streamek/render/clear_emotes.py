import json

# Function to remove emotes from the data
def clear_emotes(data):
    for entry in data:
        if "emotes" in entry:
            del entry["emotes"]
    return data

# Load data from file
with open('website/data/data_emoji.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# import json
#
# # Load data from file
# with open('website/data/quotes.json', 'r', encoding='utf-8') as file:
#     data = json.load(file)
#
# # Add id to each dictionary in the list
# for i, entry in enumerate(data):
#     entry_with_id_first = {'id': i + 1}
#     entry_with_id_first.update(entry)
#     data[i] = entry_with_id_first
#
# # Save the modified data back to the file
# with open('website/data/quotes.json', 'w', encoding='utf-8') as file:
#     json.dump(data, file, ensure_ascii=False, indent=4)
#
# print("added id")

