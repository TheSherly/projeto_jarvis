"""
llm_client.py — Cliente para comunicação com o Gemma 12B.

Encapsula a API OpenAI-compatible para enviar mensagens ao modelo.
Como o servidor Gemma não suporta tool calling nativo, implementamos
tool calling via prompt engineering (o LLM retorna JSON com a ferramenta).
"""

import logging
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuração do cliente
GEMMA_BASE_URL = os.getenv("GEMMA_BASE_URL", "https://llm.liaufms.org/v1/gemma-3-12b-it")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY", "")
MODEL_NAME = "google/gemma-3-12b-it"


def get_client() -> OpenAI:
    """Cria e retorna um cliente OpenAI configurado para o Gemma 12B."""
    if not GEMMA_API_KEY:
        raise ValueError("GEMMA_API_KEY não encontrada. Configure o arquivo .env.")
    return OpenAI(base_url=GEMMA_BASE_URL, api_key=GEMMA_API_KEY)


def chat(messages: list[dict]) -> str:
    """
    Envia mensagens para o Gemma 12B e retorna a resposta como texto.

    O tool calling é implementado via prompt engineering: o system prompt
    instrui o modelo a retornar JSON quando quiser chamar uma ferramenta.

    Args:
        messages: Lista de mensagens no formato OpenAI (role, content).

    Returns:
        Texto da resposta do modelo.
    """
    client = get_client()

    logger.info(f"Enviando requisição para LLM com {len(messages)} mensagem(ns)")

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
        content = response.choices[0].message.content or ""

        logger.info(f"LLM respondeu: {content[:150]}...")
        return content

    except Exception as e:
        logger.error(f"Erro ao comunicar com LLM: {type(e).__name__}: {e}")
        raise
