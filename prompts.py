import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def get_response(messages):
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )

    return response.choices[0].message.content

def context_aware(chunk):
    contex = [
            {"role":"system","content" : "summarize next text and extract important information and put it on the top of the text"},
            {"role": "user", "content": chunk}
        ]
    return get_response(contex)


def query_parsing(query) :
    contex = [
            {"role":"system","content" : """Rewrite the user question for retrieval.
Clarify ambiguity, remove irrelevant details, and add useful terminology.
Do not answer the question. Return the search query only.
"""},
            {"role": "user", "content": query}
        ]
    return get_response(contex)


def route(query) :
    context =[
        {"role":"system","content" : """You are router agent :
        if the query depend on :
        -Documents
        -user or companny data 
        -politicies
        return ```retrieve``` 
        
        if the query is :
        -general convesation 
        -greeting 
        return ```direct_answer```
        """  }
    ]

def final_answer(query,context) :
    cintext 