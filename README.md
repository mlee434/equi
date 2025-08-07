# Shakespeare Chatbot Take Home

download and install [Ollama](https://ollama.com)
have docker running
use uv as Python package manager `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`

```
ollama pull nomic-embed-text
export OPENAI_API_KEY=<your key here>

uv run python plays_to_json.py
uv run python poetry_to_json.py
docker-compose up -d
uv run python load_weaviate.py
uv run python start_api.py
(in a separate terminal) open demo_frontend.html
```

## Considerations

### Loading Data

 - Local Weaviate and Ollama for vector db and embeddings to be independent from token quotas
 - Tried to use local llama3.2 for generation but got very poor results
 - Separate parsing Shakespeare's work from loading Weaviate into two distinct steps

 ### Bot Architecture

  - Separation of concerns of
    - Searching Weaviate
    - Calling ChatGPT
    - Coordinating ChatGPT and Weaviate
    - Context enrichment

### API

 - FastAPI

### Frontend

 - Vibe coded

 ## Opportunities

 - Pydantic base classes
   - Abstract base AI and Vector search classes with interface
     - Swap out OpenAI or Weaviate with no code changes required elsewhere
 - I chunked the plays into each character's dialogues
   - Chunks are too small, lack of context in one dialogue, weird semantic search results
 - Perhaps an LLM step to translate the user's query into a higher quality Weaviate semantic search query
 - Different context for first response vs. later in conversation
 - Move conversation management to AIClient instead of core
 - Dynamically decide not enough context and search for more from Weaviate
 - Generally more experimentation with bot steps and structure
 - Implement using orchestration engine like Temporal
 - Containerize API