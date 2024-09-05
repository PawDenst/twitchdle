import csv
import requests
from PIL import Image, ImageEnhance
from io import BytesIO
import random

# Function to download image and resize it to square
def download_and_resize_image(url, size):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    img = img.resize((size, size), Image.LANCZOS)  # Using Lanczos resampling
    return img

# Function to create a square collage from the images
def create_square_collage(images, cols, rows, size):
    collage = Image.new('RGB', (cols*size, rows*size))
    for i, img in enumerate(images):
        collage.paste(img, ((i % cols)*size, (i // cols)*size))
    return collage

# Function to shuffle images ensuring identical images are not too close
def shuffle_images(images, cols):
    shuffled_images = []
    for img in images:
        shuffled_images.append(img)
        if len(shuffled_images) % cols == 0:  # Check if a row is complete
            # If a row is complete, shuffle the last cols images
            random.shuffle(shuffled_images[-cols:])
    return shuffled_images

# Read the CSV file and extract only the third column (image URLs)
image_urls = []
with open('../data/sullygnome_data.csv', 'r') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Skip the header row
    for row in reader:
        if len(row) >= 3:  # Checking if there are at least three columns
            image_url = row[2]  # Assuming the image URL is in the third column
            image_urls.append(image_url)

# Download and resize images
images = []
for url in image_urls:
    image = download_and_resize_image(url, 60)  # Resize to 60x60 with Lanczos resampling
    images.append(image)

# Shuffle the list of images ensuring identical images are not too close
shuffled_images = shuffle_images(images, 20)

# Calculate number of columns and rows to fill the entire page
total_images = len(shuffled_images)
cols = 20  # Number of columns
rows = (total_images // cols) + 1  # Number of rows based on the total number of images

# Fill the remaining spaces with the first few images to avoid black squares
for i in range(total_images, cols * rows):
    shuffled_images.append(images[i % total_images])

# Randomly shuffle all images
random.shuffle(shuffled_images)

# Create square collage
collage = create_square_collage(shuffled_images, cols, rows, 60)

# Darken the image
enhancer = ImageEnhance.Brightness(collage)
collage_dark = enhancer.enhance(0.75)  # Decrease brightness by 25%

# Save the darker collage as a PNG file
collage_dark.save('../static/collage.png')
