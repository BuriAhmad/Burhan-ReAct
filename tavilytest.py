import os
from tavily import TavilyClient
import google.generativeai as genai

# API Keys
GEMINI_API_KEY = "AIzaSyAfBQ_-bI2qhiyhXo2UhWQBCtD--y7rJHs"
TAVILY_API_KEY = "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"  # Replace with your Tavily API key

# Configure APIs
genai.configure(api_key=GEMINI_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

def rag_search_and_generate(query, max_results=3):
    """
    Perform RAG using Tavily for retrieval and Gemini for generation
    """
    # Step 1: Retrieve relevant information using Tavily
    print(f"Searching for: {query}")
    search_results = tavily_client.search(
        query=query,
        max_results=max_results,
        include_answer=True,
        include_raw_content=False
    )
    
    # Step 2: Extract and format retrieved content
    retrieved_content = []
    for result in search_results.get('results', []):
        content = f"Source: {result['url']}\nContent: {result['content']}\n"
        retrieved_content.append(content)
    
    context = "\n---\n".join(retrieved_content)
    
    # Step 3: Generate response using Gemini with retrieved context
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Based on the following retrieved information, provide a comprehensive answer to the question: "{query}"
    
    Retrieved Information:
    {context}
    
    Please provide a well-structured answer based on the above sources.
    """
    
    response = model.generate_content(prompt)
    
    return {
        'query': query,
        'retrieved_sources': [result['url'] for result in search_results.get('results', [])],
        'generated_answer': response.text,
        'raw_search_results': search_results
    }

# Example usage
if __name__ == "__main__":
    query = "who is Waqar Ahmed from assistant professor at lums?"
    result = rag_search_and_generate(query)
    
    print("=" * 50)
    print(f"Query: {result['query']}")
    print("=" * 50)
    print("Sources used:")
    for i, source in enumerate(result['retrieved_sources'], 1):
        print(f"{i}. {source}")
    print("=" * 50)
    print("Generated Answer:")
    print(result['generated_answer'])