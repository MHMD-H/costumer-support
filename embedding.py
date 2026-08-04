from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever


def symmetric_search(chunks,k=5):
    embeddings  = OpenAIEmbeddings(model="text-embedding-3-large")
    vectordb = Chroma.from_documents(documents=chunks,embedding=embeddings,persist_directory="chroma/")
    symmetric_retriever = vectordb.as_retriever(kwargs={"K" : k})
    return symmetric_retriever

def keyword_search(chunks,k=5):
    keyword_retriever = BM25Retriever.from_documents(documents=chunks)
    keyword_retriever.k = k
    return keyword_retriever

keyword_retriever = keyword_search()
symmetric_retriever = symmetric_search()
def hybird_search(keyword_retriever,symmetric_retriever,keyword_w=.3,symmetric_c=.7):
    hybird_retriver = EnsembleRetriever(
        retrievers=[keyword_retriever,
        symmetric_retriever],
        weights= [keyword_w,symmetric_c])
    return hybird_retriver