import sys
import logging
# pyrefly: ignore [missing-import]
from FlagEmbedding import FlagModel

# Configure basic logging to silence verbose model loading warnings unless necessary
logging.basicConfig(level=logging.WARNING)

def main():
    print("🚀 Loading BGE model (BAAI/bge-small-en-v1.5)...")
    try:
        # Load the local embedding model
        # use_fp16=True speeds up inference and lowers memory footprint
        model = FlagModel(
            'BAAI/bge-small-en-v1.5',
            query_instruction_for_retrieval="Represent this sentence for searching relevant passages: ",
            use_fp16=True
        )
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        sys.exit(1)
    
    test_chunks = [
        "OpenAI just released a new language model that outperforms GPT-4 on coding benchmarks.",
        "A recent research paper introduces a novel approach to optimizing vector embeddings using cosine similarity.",
        "The startup raised $50 million in Series A funding to build an open-source alternative to proprietary LLMs."
    ]
    
    print(f"\n🧠 Generating embeddings for {len(test_chunks)} test chunks...")
    try:
        embeddings = model.encode(test_chunks)
    except Exception as e:
        print(f"❌ Failed to generate embeddings: {e}")
        sys.exit(1)
    
    print("\n✅ Embedding Generation Successful!")
    print(f"Total chunks processed: {len(embeddings)}")
    
    # Verify dimensions
    dimensions = len(embeddings[0])
    print(f"Vector Dimensions: {dimensions} (Expected: 384)\n")
    
    if dimensions != 384:
        print("⚠️ WARNING: The generated embeddings do not match the expected 384 dimensions!")
    
    for i, chunk in enumerate(test_chunks):
        print(f"--- Chunk {i+1} ---")
        print(f"Text: '{chunk}'")
        # Show just the first 5 floats to avoid cluttering the terminal
        preview = [round(float(val), 5) for val in embeddings[i][:5]]
        print(f"Embedding preview (first 5 floats): {preview} ...")
        print("-" * 40)

if __name__ == "__main__":
    main()
