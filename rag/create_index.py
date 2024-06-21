from pymongo.mongo_client import MongoClient
from pymongo.operations import SearchIndexModel
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
db = client['instagram_profiles']
collection = db['embeddings']
# Create your index model, then create the search index
search_index_model = SearchIndexModel(
  definition={
    "fields": [
      {
        "type": "vector",
        "path": "text",
        "numDimensions": 1024,
        "similarity": "euclidean"
      }
    ]
  },
  name="vector_index",
  type="vectorSearch",
)
result = collection.create_search_index(model=search_index_model)
print(result)