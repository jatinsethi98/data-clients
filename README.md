# data-clients

Shared data-access clients for external services. A modular Python toolkit providing unified interfaces for Gmail, Google Calendar, web fetching, LLM calls, embeddings, vector stores, iMessage, browser history, and macOS Contacts.

## Install

```bash
pip install data-clients                          # core only (no deps)
pip install data-clients[gmail]                   # Gmail API client
pip install data-clients[llm]                     # Anthropic Claude wrapper
pip install data-clients[embeddings]              # Voyage AI + httpx embedders
pip install data-clients[vectorstore-chroma]      # ChromaDB backend
pip install data-clients[vectorstore-qdrant]      # Qdrant backend (sync + async)
pip install data-clients[calendar]                # Google Calendar client
pip install data-clients[web]                     # SSRF-safe web fetcher + Brave Search
pip install data-clients[contacts]                # macOS Contacts (pyobjc)
pip install data-clients[all]                     # everything
```

For development:
```bash
pip install -e ".[all,dev]"
```

## Modules

### Gmail (`data_clients.gmail`)
Full Gmail API client with send, batch retrieval, History API sync, labels, query builder, and MIME parsing. Uses `google-auth` (not `oauth2client`).

```python
from data_clients.gmail import Gmail, AuthManager, query, label, parse_message
```

### LLM (`data_clients.llm`)
Sync and async wrappers around the Anthropic SDK with retry logic, streaming, and tool use support.

```python
from data_clients.llm import LLMClient, AsyncLLMClient

client = LLMClient()  # reads ANTHROPIC_API_KEY from env
result = client.generate("You are helpful.", "What is 2+2?")
print(result["text"])
```

### Embeddings (`data_clients.embeddings`)
Abstract base with Voyage AI, OpenAI, and Ollama backends.

```python
from data_clients.embeddings import VoyageEmbedder, OpenAIEmbedder, OllamaEmbedder

embedder = VoyageEmbedder(api_key="...")
vector = embedder.embed("hello world")
```

### Vector Stores (`data_clients.vectorstore`)
Abstract base with ChromaDB and Qdrant backends (sync + async).

```python
from data_clients.vectorstore import ChromaVectorStore, AsyncQdrantVectorStore

# Sync ChromaDB
store = ChromaVectorStore(persist_dir=Path("./chroma"))

# Async Qdrant
store = await AsyncQdrantVectorStore.create(url="http://localhost:6333")
results = await store.search(query_embedding, n_results=10)
```

### Calendar (`data_clients.calendar`)
Google Calendar client with sync and async methods.

```python
from data_clients.calendar import CalendarClient
client = CalendarClient(credentials)
events = client.list_events(time_min="2024-01-01T00:00:00Z")
```

### Web (`data_clients.web`)
SSRF-safe URL fetcher and Brave Search client.

```python
from data_clients.web import WebFetcher, BraveSearchClient
```

### iMessage (`data_clients.imessage`)
Read-only access to macOS Messages chat.db and AppleScript sending.

### Browser (`data_clients.browser`)
Safari and Chrome history reader.

### Contacts (`data_clients.contacts`)
macOS Contacts via pyobjc (runtime-guarded).

## Requirements

- Python >= 3.11
- All external dependencies are optional (installed via extras)

## License

MIT
