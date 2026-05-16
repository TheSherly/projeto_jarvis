"""
rag_core.py — Pipeline RAG (Retrieval-Augmented Generation).

Responsável por:
1. Carregar documentos (PDFs e textos) do diretório data/
2. Dividir em chunks com sobreposição
3. Gerar embeddings com sentence-transformers
4. Indexar no ChromaDB
5. Buscar trechos relevantes para uma query
"""

import os
import logging
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Caminhos
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
VECTOR_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vector_db")

# Modelo de embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Instância global do ChromaDB client e collection
_chroma_client = None
_collection = None


def _get_collection():
    """Retorna a collection do ChromaDB, criando se necessário."""
    global _chroma_client, _collection

    if _collection is not None:
        return _collection

    _chroma_client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

    # Usa sentence-transformers para embeddings
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    _collection = _chroma_client.get_or_create_collection(
        name="materiais_academicos",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    logger.info(f"ChromaDB collection inicializada com {_collection.count()} documento(s)")
    return _collection


def carregar_documentos(data_dir: str = None) -> list[dict]:
    """
    Carrega todos os documentos da pasta data/.

    Suporta arquivos .pdf e .txt.

    Args:
        data_dir: Caminho do diretório de dados. Se None, usa DATA_DIR.

    Returns:
        Lista de dicionários com 'texto' e 'fonte' para cada documento.
    """
    if data_dir is None:
        data_dir = DATA_DIR

    documentos = []

    if not os.path.exists(data_dir):
        logger.warning(f"Diretório de dados não encontrado: {data_dir}")
        return documentos

    for filename in os.listdir(data_dir):
        filepath = os.path.join(data_dir, filename)

        if filename.lower().endswith(".pdf"):
            try:
                reader = PdfReader(filepath)
                texto = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        texto += page_text + "\n"
                if texto.strip():
                    documentos.append({"texto": texto, "fonte": filename})
                    logger.info(f"PDF carregado: {filename} ({len(texto)} caracteres)")
                else:
                    logger.warning(f"PDF sem texto extraível: {filename}")
            except Exception as e:
                logger.error(f"Erro ao ler PDF {filename}: {e}")

        elif filename.lower().endswith(".txt"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    texto = f.read()
                if texto.strip():
                    documentos.append({"texto": texto, "fonte": filename})
                    logger.info(f"TXT carregado: {filename} ({len(texto)} caracteres)")
            except Exception as e:
                logger.error(f"Erro ao ler TXT {filename}: {e}")

    logger.info(f"Total de documentos carregados: {len(documentos)}")
    return documentos


def chunkar_documentos(documentos: list[dict], chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    """
    Divide documentos em chunks menores com sobreposição.

    Usa RecursiveCharacterTextSplitter do LangChain para divisão inteligente
    que respeita limites de parágrafo, frase e palavra.

    Args:
        documentos: Lista de dicts com 'texto' e 'fonte'.
        chunk_size: Tamanho máximo de cada chunk em caracteres.
        chunk_overlap: Sobreposição entre chunks adjacentes.

    Returns:
        Lista de dicts com 'texto', 'fonte' e 'chunk_id'.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in documentos:
        partes = splitter.split_text(doc["texto"])
        for i, parte in enumerate(partes):
            chunks.append({
                "texto": parte,
                "fonte": doc["fonte"],
                "chunk_id": f"{doc['fonte']}_chunk_{i}"
            })

    logger.info(f"Documentos divididos em {len(chunks)} chunk(s) (tamanho={chunk_size}, overlap={chunk_overlap})")
    return chunks


def indexar(chunks: list[dict]):
    """
    Indexa os chunks no ChromaDB.

    Os embeddings são gerados automaticamente pela embedding function
    configurada na collection.

    Args:
        chunks: Lista de dicts com 'texto', 'fonte' e 'chunk_id'.
    """
    collection = _get_collection()

    # Verifica se já existem documentos indexados
    if collection.count() > 0:
        logger.info(f"Collection já possui {collection.count()} chunks indexados. Pulando re-indexação.")
        return

    if not chunks:
        logger.warning("Nenhum chunk para indexar.")
        return

    # Prepara dados para inserção em batches
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.add(
            documents=[c["texto"] for c in batch],
            metadatas=[{"fonte": c["fonte"]} for c in batch],
            ids=[c["chunk_id"] for c in batch]
        )

    logger.info(f"{len(chunks)} chunk(s) indexados no ChromaDB com sucesso.")


def buscar(query: str, n_results: int = 3) -> list[dict]:
    """
    Busca os chunks mais relevantes para uma query.

    Args:
        query: Texto da consulta do usuário.
        n_results: Número de resultados a retornar.

    Returns:
        Lista de dicts com 'texto', 'fonte' e 'distancia' para cada resultado.
    """
    collection = _get_collection()

    if collection.count() == 0:
        logger.warning("Nenhum documento indexado. Retornando vazio.")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )

    documentos = []
    for i in range(len(results["documents"][0])):
        documentos.append({
            "texto": results["documents"][0][i],
            "fonte": results["metadatas"][0][i]["fonte"],
            "distancia": results["distances"][0][i] if results.get("distances") else None,
        })

    logger.info(f"Busca RAG para '{query[:50]}...': {len(documentos)} resultado(s)")
    return documentos


def inicializar_rag():
    """
    Pipeline completo de inicialização do RAG:
    1. Carrega documentos de data/
    2. Divide em chunks
    3. Indexa no ChromaDB

    Deve ser chamada na inicialização do sistema.
    """
    logger.info("Inicializando pipeline RAG...")

    documentos = carregar_documentos()
    if not documentos:
        logger.warning("Nenhum documento encontrado em data/. RAG não terá materiais.")
        return

    chunks = chunkar_documentos(documentos)
    indexar(chunks)

    collection = _get_collection()
    logger.info(f"RAG inicializado com sucesso. Total de chunks indexados: {collection.count()}")


def get_status() -> dict:
    """Retorna informações sobre o estado atual do RAG."""
    collection = _get_collection()
    return {
        "total_chunks": collection.count(),
        "diretorio_dados": DATA_DIR,
        "diretorio_vetores": VECTOR_DB_DIR,
        "modelo_embeddings": EMBEDDING_MODEL,
    }
