from langchain_text_splitters import RecursiveCharacterTextSplitter
from load_data import load_document
from prompts import context_aware 
def split_text(docs,chunk_size=800,chunk_overlap=150):
    split = RecursiveCharacterTextSplitter(
        separators=["\n\n","\n","."," ",""],
        chunk_size=chunk_size,
        chunk_overlap = chunk_overlap
    )

    chunks = split.split_documents(docs)
    awared_chunks = context_aware(chunks)
    return awared_chunks
    
