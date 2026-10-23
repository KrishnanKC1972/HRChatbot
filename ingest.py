# -*- coding: utf-8 -*-
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from src.llm import get_embeddings
from config import settings
import os


def load_documents():
    documents = []
    # Load PDFs (primary HR policy knowledge base)
    if os.path.exists('data/hr_policies_pdf'):
        loader = DirectoryLoader('data/hr_policies_pdf', glob='**/*.pdf', loader_cls=PyPDFLoader, silent_errors=True)
        try:
            docs = loader.load()
            documents.extend(docs)
            print(f'Loaded {len(docs)} PDF pages')
        except Exception as e:
            print(f'Error loading PDFs: {e}')
    
    # Load HR scenario documents (complex / difficult cases)
    for d in ['data/hr_scenarios']:
        if os.path.exists(d):
            loader = DirectoryLoader(d, glob='**/*.txt', loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}, silent_errors=True)
            try:
                docs = loader.load()
                documents.extend(docs)
                print(f'Loaded {len(docs)} text docs from {d}')
            except Exception as e:
                print(f'Error loading from {d}: {e}')
    
    return documents


def split_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    splits = text_splitter.split_documents(documents)
    return splits


def create_vector_store(documents=None):
    if documents is None:
        documents = load_documents()
    splits = split_documents(documents)
    embeddings = get_embeddings()

    # Reset the collection so re-ingestion doesn't accumulate stale duplicates
    if os.path.exists(settings.chroma_persist_dir):
        try:
            existing = Chroma(
                persist_directory=settings.chroma_persist_dir,
                embedding_function=embeddings,
            )
            existing.delete_collection()
            print('Cleared existing ChromaDB collection')
        except Exception as e:
            print(f'Could not clear existing collection: {e}')

    vector_store = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )
    return vector_store


def main():
    print('Starting document ingestion (PDFs + complex scenarios)...')
    docs = load_documents()
    if len(docs) == 0:
        print('No documents found')
        return
    splits = split_documents(docs)
    create_vector_store(docs)
    print(f'Ingested {len(docs)} docs -> {len(splits)} chunks to {settings.chroma_persist_dir}')
    print('Done')


if __name__ == '__main__':
    main()
