from get_embeddings import get_embedding
import pandas as pd
from pymongo import MongoClient
dataset_df = pd.read_csv('../dataset/profiles.csv',lineterminator='\n')
dataset_df["embedding"] = dataset_df["text"].apply(get_embedding)
dataset_df = dataset_df[dataset_df['_id'] != None]
print(dataset_df.head())
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
db = client['instagram_profiles']
collection = db['embeddings']

documents = dataset_df.to_dict("records")
collection.insert_many(documents)