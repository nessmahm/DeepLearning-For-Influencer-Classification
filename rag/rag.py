from get_embeddings import get_embedding
from transformers import AutoTokenizer, AutoModelForCausalLM
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
db = client['instagram_profiles']
collection = db['embeddings']
def vector_search(user_query, collection):
    """
    Perform a vector search in the MongoDB collection based on the user query.

    Args:
    user_query (str): The user's query string.
    collection (MongoCollection): The MongoDB collection to search.

    Returns:
    list: A list of matching documents.
    """

    # Generate embedding for the user query
    query_embedding = get_embedding(user_query)

    if query_embedding is None:
        return "Invalid query or embedding generation failed."

    # Define the vector search pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "queryVector": query_embedding,
                "path": "embedding",
                "numCandidates": 150,  # Number of candidate matches to consider
                "limit": 4,  # Return top 4 matches
            }
        },
        {
            "$project": {
                "_id": 0,  # Exclude the _id field
                "username": 1,
                "text": 1,  # Include the plot field
                "categories": 1,  # Include the title field
                "hashtags": 1,  # Include the genres field
                "followers": 1,
                "followees": 1,
                "posts":1,
                "score": {"$meta": "vectorSearchScore"},  # Include the search score
            }
        },
    ]

    # Execute the search
    results = collection.aggregate(pipeline)
    return list(results)

def get_search_result(query, collection):

    get_knowledge = vector_search(query, collection)

    search_result = ""
    for result in get_knowledge:
        search_result += f"Username: {result.get('username', 'N/A')}, Categories:{result.get('categories',[])} Followers: {result.get('followers',0)}\n"

    return search_result

query = ''
while query != 'q':
    query = input('Ask Gemma A Question About Tunisian Influencers')
    source_information = get_search_result(query, collection)
    combined_information = (
        f"Query: {query}\nContinue to answer the query by using the Search Results:\n{source_information}.<model>"
    )

    access_token=os.getenv('GEMMA_TOKEN')
    tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it",token=access_token)
    model = AutoModelForCausalLM.from_pretrained("google/gemma-2b-it",token=access_token)
    input_ids = tokenizer(combined_information, return_tensors="pt")
    response = model.generate(**input_ids, max_new_tokens=500)
    generated_text = tokenizer.batch_decode(response,
                                        skip_special_tokens=True,
                                        clean_up_tokenization_spaces=False)[0]
    print('Response:',generated_text.split('<model>')[-1])