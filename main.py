
from embedding import hybird_search
from load_data import load_document
from prompts import query_parsing
from embedding import (symmetric_search,keyword_search,hybird_search)
from splitting import split_text
from query_ret import query_retreive

url = input("enter the url : ")
docs = load_document(url)
chunks = split_text(docs)
symentic_value= symmetric_search(chunks)
keyword_value = keyword_search(chunks)
hybird_value = hybird_search(symentic_value,keyword_value)

query = input("How I can help you? ")
parsed_query = query_retreive(query,hybird_value)
