# RAG Application - Run Instructions

This guide explains how to start the backend and frontend for your Retrieval-Augmented Generation (RAG) web app, and how to use the interface.

---

## 1. Prerequisites

Before running the app, make sure you have:

* Python 3.9 or later installed.
* All dependencies installed from `requirements.txt`:

  ```bash
  pip install -r requirements.txt
  ```
* A valid MongoDB Atlas cluster with a **vector search index** created on your `embedding` field.
* A Gemini API key set in your environment variables:

  ```bash
  export GEMINI_API_KEY="your_gemini_api_key_here"
  ```
* (Optional) A Tavily API key if you want to enable web search fallback:

  ```bash
  export TAVILY_API_KEY="your_tavily_api_key_here"
  ```

---

## 2. Starting the Application

From the project root directory, run:

```bash
python run_servers.py
```

This will start **two servers**:

* **FastAPI backend** at: `http://127.0.0.1:8000`
* **Gradio UI frontend** at: `http://127.0.0.1:7860`

You should see terminal output confirming both servers are running.

---

## 3. Using the Gradio Interface

1. Open your browser and go to:

   ```
   http://127.0.0.1:7860
   ```

2. **Upload a PDF**

   * Click the *Upload PDF* section.
   * Select a local PDF file.
   * The backend will process the PDF, split it into chunks, create embeddings, and insert them into MongoDB. (Large PDF files may cause timeout)

3. **Ask a Question**

   * Enter your query in the chat box.
   * The system will retrieve the most relevant document chunks from MongoDB.
   * The chunks will be combined with your question to form an augmented prompt.
   * The Gemini model will generate an answer.

4. **View the Response**

   * The answer will appear in the Gradio chat area.
   * If integrated, source document metadata may be included.

---

## 4. Optional Debugging

If you want to confirm that your vector search is working before involving the LLM:

* Call the debug endpoint directly:

  ```bash
  curl "http://127.0.0.1:8000/search-debug?q=your+query&k=5"
  ```
* You should see a JSON list of top matches with `content` or `text` fields and similarity scores.

---

## 5. Stopping the App

Press `CTRL + C` in the terminal where the servers are running to stop both FastAPI and Gradio.

---

## 6. Notes

* Make sure your MongoDB Atlas Search index name and field match your code (`vector_index` on `embedding`).
* Environment variables are recommended for sensitive values; do **not** hardcode your API keys in source code.
* If retrieval returns an empty list, verify:

  * You inserted data into the same DB/collection you are querying.
  * The vector index exists and matches embedding dimensions.
  * Your `MONGODB_URI`, `MONGODB_DB`, and `MONGODB_COLLECTION` are correct.
