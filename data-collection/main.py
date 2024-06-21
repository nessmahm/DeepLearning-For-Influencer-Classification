import csv
import instaloader
import itertools
from pymongo import MongoClient
import os
import requests
from influencers import influencers

from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
db = client['instagram_profiles']
collection = db['profiles']
notFoundCollection= db['not_found']

bot = instaloader.Instaloader()


# Define a function to download an image
def download_image(image_url,index, output_directory):
    filename = os.path.join(output_directory, str(index)+'.png')
    try:
        # Send a GET request to download the image
        response = requests.get(image_url)
        if not os.path.exists(output_directory):
            # Create the directory
            os.makedirs(output_directory)
        if response.status_code == 200:
            # Save the image to the output directory
            with open(filename, 'xb') as f:
                f.write(response.content)
            print(f"Image downloaded: {filename}")
        else:
            print(f"Failed to download image from {image_url}. HTTP status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading image from {image_url}: {str(e)}")

#bot.login("bojay46750", "nessma00")

def scrape_instagram_profile(influencer_name):
    try:
        # Check if the username already exists in the database
        already_scraped_profile = collection.find_one({"username": influencer_name})
        not_found_profile = notFoundCollection.find_one({"username": influencer_name})
        if already_scraped_profile or not_found_profile:
            print(f"Profile for {influencer_name} already exists in the database. Returning cached data.")
            return already_scraped_profile

        # If the username doesn't exist in the database, scrape it
        profile = instaloader.Profile.from_username(bot.context, influencer_name)

        if profile:
            posts = profile.get_posts()
            posts = list(itertools.islice(posts, 10))
            # Prepare data to be stored in the database
            profile_data = {
                "username": profile.username,
                "followers": profile.followers,
                "followees": profile.followees,
                "bio": profile.biography,
                "categories": influencer.get("topics", []),
                "country": influencer["country"],
                "ER": influencer.get("ER", None),
                "posts": [
                    {"caption": post.caption,
                     "comments": post.comments,
                     "imageUrl": post.url,
                     "likes": post.likes,
                     "hashtags": post.caption_hashtags,
                     }
                    for post in posts

                ]
            }
            for index, post in enumerate(posts):
                print('downloading image', index)
                download_image(post.url,index,f'./photos/{influencer_name}')

            # Store the scraped data in the database
            #collection.insert_one(profile_data)

            return profile_data
        else:
            print(f"Scraping {influencer_name} failed: Profile not found")
            return None



    except Exception as e:

        if isinstance(e, instaloader.ProfileNotExistsException):

            notFoundCollection.insert_one({

                "username": influencer_name,

            })

            print(f"Scraping {influencer_name} failed: Profile not found")

            return None

        else:

            print(f"An error occurred while scraping profile for {influencer_name}: {str(e)}")

            return None


# Function to save data to CSV (if needed)
def save_to_csv(data, csv_file_path):
    fieldnames = ["username", "followers", "followees", "bio", "caption", "comments", "imageUrl"]
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for entry in data:
            for post in entry["posts"]:
                row = {
                    "username": entry["username"],
                    "followers": entry["followers"],
                    "followees": entry["followees"],
                    "bio": entry["bio"],
                    "caption": post["caption"],
                    "comments": post["comments"],
                    "imageUrl": post["imageUrl"]
                }
                writer.writerow(row)

# Add more usernames as needed
data = []

"""for index, influencer in enumerate(influencers):
    profile_data = scrape_instagram_profile(influencer)
    if profile_data:
        data.append(profile_data)
        print(f"Scraping {influencer['account_name']} done")"""


# Loop through the MongoDB collection
def download_images_from_db():
    for document in collection.find():
        if 'posts' in document:
            for index , post in enumerate(document['posts']):
                if 'imageUrl' in post:
                    image_url = post['imageUrl']
                    download_image(image_url, index,f'./photos/{document["username"]}')
# CSV file path (optional)
csv_file_path = "instagram_data.csv"
# Save data to CSV (if needed)
save_to_csv(data, csv_file_path)

