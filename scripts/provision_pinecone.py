import os
import sys
# pyrefly: ignore [missing-import]
from pinecone import Pinecone, ServerlessSpec

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from pathlib import Path
import yaml

# Resolve config directory to load settings
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.yml"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("Error: PINECONE_API_KEY environment variable is not set.")
        print("Please set it before running this script: export PINECONE_API_KEY='your_key'")
        sys.exit(1)

    try:
        config = load_config()
        index_name = config["vector_store"]["index_name"]
        dimension = config["embedding"]["dimensions"]
    except Exception as e:
        print(f"Error loading settings.yml: {e}")
        sys.exit(1)

    print(f"Connecting to Pinecone...")
    pc = Pinecone(api_key=api_key)

    existing_indexes = [index.name for index in pc.list_indexes()]

    if index_name in existing_indexes:
        print(f"✅ Index '{index_name}' already exists.")
    else:
        print(f"🚀 Creating index '{index_name}' with dimension {dimension}...")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        print("✅ Index created successfully!")

if __name__ == "__main__":
    main()
