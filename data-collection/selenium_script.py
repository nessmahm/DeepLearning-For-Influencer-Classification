from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import requests
import os
import time
import uuid
import json
from utils.extract_hashtags import extract_and_remove_hashtags
from pymongo import MongoClient
from selenium.webdriver.common.action_chains import ActionChains
from influencers import influencers
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
db = client['instagram_profiles']
collection = db['profiles']
notFoundCollection= db['not_found']


service = Service("D:\PFA\insta-scrape\chromedriver-win64\chromedriver.exe")
driver = webdriver.Chrome(service=service)
actions = ActionChains(driver)
driver.get("https://www.instagram.com/")

time.sleep(5)
username = driver.find_element(By.XPATH,
                               "/html/body/div[2]/div/div/div[2]/div/div/div[1]/section/main/article/div[2]/div[1]/div[2]/form/div/div[1]/div/label/input")
username.send_keys("tanex15893")
password = driver.find_element(By.XPATH,
                               "/html/body/div[2]/div/div/div[2]/div/div/div[1]/section/main/article/div[2]/div[1]/div[2]/form/div/div[2]/div/label/input")
password.send_keys("nessma00")
password.send_keys(Keys.ENTER)

time.sleep(10)

# Print the influencers

def scrape_profiles():
    for influencer in influencers:
        user = influencer["account_name"]
        already_scraped_profile = collection.find_one({"username": influencer["account_name"]})
        not_found_profile = notFoundCollection.find_one({"username": influencer["account_name"]})
        if already_scraped_profile or not_found_profile:
            print(f"Profile for {user} already exists in the database. Returning cached data.")
            continue

        driver.get(f"https://www.instagram.com/{user}/")
        time.sleep(30)
        try:
            more_infos = driver.find_element(By.TAG_NAME, "ul")
            number_of_posts = more_infos.find_element(By.XPATH,
                                                      "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[1]/span/span")
            followers = more_infos.find_element(By.XPATH,
                                                "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[2]/a/span/span")
            bio = more_infos.find_element(By.XPATH,
                                          "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/div[3]/h1")

            try:
                followees = more_infos.find_element(By.XPATH,
                                                    "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[3]/a/span/span")
            except NoSuchElementException:
                followees = more_infos.find_element(By.XPATH,
                                                    "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[3]/span/span")

            data = {
                'username': user,
                'followers': followers.text,
                'followees': followees.text,
                'bio': bio.text,
                "categories": influencer.get("topics", []),
                "country": influencer.get('country', "Tunisia"),
                "ER": influencer.get("ER", None),
                'posts': [],
            }

            post_count = 0
            downloaded_urls = set()
            while post_count < 50:
                last_height = driver.execute_script("return document.body.scrollHeight")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(8)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break

                posts = driver.find_elements(By.CLASS_NAME, '_aagv')
                for post in posts:
                    if post_count >= 50:
                        break
                    image = post.find_element(By.TAG_NAME, 'img')

                    hashtags, post_caption = extract_and_remove_hashtags(image.get_attribute('alt'))
                    image_url = image.get_attribute('src')

                    if image_url not in downloaded_urls:
                        post_count += 1
                        downloaded_urls.add(image_url)
                        data['posts'].append({
                            'caption': post_caption,
                            'imageUrl': image_url,
                            'hashtags': hashtags,
                            # 'likes': likes.text,
                            # 'comments': comments.text,

                        })
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            os.makedirs(f"photos-2/{user}", exist_ok=True)
                            with open(f"photos-2/{user}/{post_count}.png", "wb") as file:
                                file.write(response.content)
                            print(f"Image {post_count} de {user} téléchargée avec succès.")
                        else:
                            print(f"Échec du téléchargement de l'image {post_count} de {user}.")

            # Add data to the database
            if len(data['posts']) > 0:
                collection.insert_one(data)
                if len(data['posts']) < 50:
                    print(f'Scraped less than 50 posts for user {user}')
                print(f'Scraping profile {user} done.')
        except Exception as e:
            if isinstance(e, NoSuchElementException):
                print("Error 'no such elemnt' while scraping profile" + user)
                notFoundCollection.insert_one({
                    "username": influencer["account_name"],
                    "categories": influencer.get("topics", []),
                    "country": influencer.get("country", "Tunisia"),
                    "ER": influencer.get("ER", None),
                })
            else:
                print('Unkown error when scripting profile' + user, str(e))


def update_influencers():
    query = {"$expr": {"$lte": [{"$size": "$posts"}, 10]}}
    influencers_to_update = collection.find(query)

    for influencer in influencers_to_update:
        user = influencer["username"]
        print("scraping", influencer["username"] , "start")

        driver.get(f"https://www.instagram.com/{user}/")
        time.sleep(30)
        try:
            data = {
                'posts': [],
            }

            post_count = 0
            downloaded_urls = set()
            while post_count < 50:
                last_height = driver.execute_script("return document.body.scrollHeight")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(10)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break

                posts = driver.find_elements(By.CLASS_NAME, '_aagv')
                for post in posts:

                    if post_count >= 50:
                        break
                    image = post.find_element(By.TAG_NAME, 'img')

                    hashtags, post_caption = extract_and_remove_hashtags(image.get_attribute('alt'))
                    image_url = image.get_attribute('src')

                    if image_url not in downloaded_urls:
                        post_count += 1
                        downloaded_urls.add(image_url)
                        data['posts'].append({
                            'caption': post_caption,
                            'imageUrl': image_url,
                            'hashtags': hashtags,
                            # 'likes': likes.text,
                            # 'comments': comments.text,

                        })
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            os.makedirs(f"photos-2/{user}", exist_ok=True)
                            with open(f"photos-2/{user}/{post_count}.png", "wb") as file:
                                file.write(response.content)
                            print(f"Image {post_count} de {user} téléchargée avec succès.")
                        else:
                            print(f"Échec du téléchargement de l'image {post_count} de {user}.")

            # Add data to the database
            if len(data['posts']) > 0:
                collection.update_one({'username': influencer['username']}, {"$set": data})
                if len(data['posts']) < 50:
                    print(f'Scraped less than 50 posts for user {user}')
                print(f'Scraping profile {user} done.')
        except Exception as e:
            if isinstance(e, NoSuchElementException):
                print("Error 'no such elemnt' while scraping profile" + user)
                notFoundCollection.insert_one({
                    "username": influencer["username"],
                    "categories": influencer.get("topics", []),
                    "country": influencer.get("country", "Tunisia"),
                    "ER": influencer.get("ER", None),
                })
                collection.delete_one({"_id": influencer["_id"]})
            else:
                print('Unkown error when scripting profile' + user, str(e))

def delete_duplicate_profiles():
    pipeline = [
        {"$group": {"_id": "$username", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    for doc in collection.aggregate(pipeline):
        username = doc["_id"]
        # Find documents with the same username
        duplicate_docs = list(collection.find({"username": username}))
        # Remove the first document from the duplicates list
        duplicate_docs.pop(0)
        # Delete duplicate documents
        for dup_doc in duplicate_docs:
            collection.delete_one({"_id": dup_doc["_id"]})


    # Iterate over duplicate usernames
#update_influencers()
#scrape_profiles()

def scrape_profile(username):
    user = username
    already_scraped_profile = collection.find_one({"username": username})
    not_found_profile = notFoundCollection.find_one({"username": username})
    if already_scraped_profile or not_found_profile:
        print(f"Profile for {user} already exists in the database. Returning cached data.")
        return already_scraped_profile

    driver.get(f"https://www.instagram.com/{user}/")
    time.sleep(30)
    try:
        more_infos = driver.find_element(By.TAG_NAME, "ul")
        number_of_posts = more_infos.find_element(By.XPATH,
                                                  "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[1]/span/span")
        followers = more_infos.find_element(By.XPATH,
                                            "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[2]/a/span/span")
        bio = more_infos.find_element(By.XPATH,
                                      "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/div[3]/h1")

        try:
            followees = more_infos.find_element(By.XPATH,
                                                "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[3]/a/span/span")
        except NoSuchElementException:
            followees = more_infos.find_element(By.XPATH,
                                                "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/section/main/div/header/section/ul/li[3]/span/span")

        data = {
            'username': user,
            'followers': followers.text,
            'followees': followees.text,
            'bio': bio.text,
            'posts': [],
        }

        post_count = 0
        downloaded_urls = set()
        while post_count < 50:
            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(8)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break

            posts = driver.find_elements(By.CLASS_NAME, '_aagv')
            for post in posts:
                if post_count >= 50:
                    break
                image = post.find_element(By.TAG_NAME, 'img')

                hashtags, post_caption = extract_and_remove_hashtags(image.get_attribute('alt'))
                image_url = image.get_attribute('src')

                if image_url not in downloaded_urls:
                    post_count += 1
                    downloaded_urls.add(image_url)
                    data['posts'].append({
                        'caption': post_caption,
                        'imageUrl': image_url,
                        'hashtags': hashtags,
                        # 'likes': likes.text,
                        # 'comments': comments.text,

                    })
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        os.makedirs(f"photos-2/{user}", exist_ok=True)
                        with open(f"photos-2/{user}/{post_count}.png", "wb") as file:
                            file.write(response.content)
                        print(f"Image {post_count} de {user} téléchargée avec succès.")
                    else:
                        print(f"Échec du téléchargement de l'image {post_count} de {user}.")

        # Add data to the database
        if len(data['posts']) > 0:
            collection.insert_one(data)
            if len(data['posts']) < 50:
                print(f'Scraped less than 50 posts for user {user}')
            print(f'Scraping profile {user} done.')
    except Exception as e:
        if isinstance(e, NoSuchElementException):
            print("Error 'no such elemnt' while scraping profile" + user)
            notFoundCollection.insert_one({
                "username": username,
            })
        else:
            print('Unkown error when scripting profile' + user, str(e))
driver.quit()
