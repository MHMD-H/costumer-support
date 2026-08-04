import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# PDF / Web / Notion Loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    WebBaseLoader,
    NotionDirectoryLoader,
)


# YouTube
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.blob_loaders import FileSystemBlobLoader
from langchain_community.document_loaders.parsers import OpenAIWhisperParser
from langchain_community.document_loaders.blob_loaders.youtube_audio import (
    YoutubeAudioLoader,
)


#load api key from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("GROQ_API_KEY"),base_url="https://api.groq.com/openai/v1")

def define_format(url) :
    url=url
    source = None
    if url.startswith(("http://","https://"))  :
        if "youtube" in url or "youtu.be" in url : return url , "youtube"
        else : return url,"web"
    format = Path(url).suffix.lstrip(".")
    if format == "pdf" :
        return url,"pdf"
    
    elif "notion" in url :
        return url,"notion"
    else :
        raise ValueError("this type are not supported")
def load_document(url) :
    #load PDF document
    url,file_type = define_format(url)
    if file_type == "pdf" :
        loader = PyPDFLoader(url)
    elif file_type == "web" :
        loader = WebBaseLoader(url)
    elif file_type == "notion" :
        loader = NotionDirectoryLoader(url)
    elif file_type == "youtube" :
        save_dir = "downloads/"
        YoutubeAudioLoader([url],save_dir).load()

        loader = GenericLoader(
            FileSystemBlobLoader(save_dir,glob = "*.mp3"),
            OpenAIWhisperParser()
        )
    docs = loader.load()

    return docs




