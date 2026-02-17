import os

from dotenv import load_dotenv

load_dotenv()

ACTIVE_BROKER = os.getenv("BROKER", "groww").strip().lower()
PINECONE_INDEX_NAME_EQ = os.getenv("PINECONE_INDEX_NAME_EQ", "groww-instruments-eq")


