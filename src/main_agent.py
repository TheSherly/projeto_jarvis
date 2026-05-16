"""
main_agent.py — Agente coordenador do Jarvis Acadêmico.

Implementa o loop principal do agente com tool calling via prompt engineering:
1. Recebe mensagem do usuário
2. Envia para o LLM com system prompt que instrui sobre ferramentas
3. Se o LLM retornar JSON com tool_call → parseia, executa e envia resultado de volta
4. Repete até o LLM retornar resposta de texto (sem tool_call)
5. Retorna resposta final ao usuário

A decisão de qual ferramenta chamar é feita inteiramente pela LLM.
"""

import json
import re
import logging
from src import llm_client, database, rag_core
from src.tools import executar_ferramenta
from src.prompts import get_system_prompt

logger = logging.getLogger(__name__)

# Número máximo de iterações do loop de tool calling (segurança)
MAX_TOOL_ITERATIONS = 5


def _extrair_tool_call(resposta: str) -> dict | None:
    """
    Tenta extrair uma chamada de ferramenta da resposta do LLM.

    O LLM é instruído a retornar JSON no formato:
    {"tool_call": "nome", "arguments": {...}}

    Args:
        resposta: Texto da resposta do LLM.

    Returns:
        Dicionário com tool_call e arguments, ou None se não for uma chamada.
    """
    texto = resposta.strip()

    # Tenta extrair JSON de bloco de código ```json ... ```
    json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', texto, re.DOTALL)
    if json_block:
        texto_json = json_block.group(1)
    else:
        # Tenta encontrar JSON direto na resposta
        json_match = re.search(r'(\{[^{}]*"tool_call"[^{}]*\})', texto, re.DOTALL)
        if json_match:
            texto_json = json_match.group(1)
        else:
            return None

    try:
        dados = json.loads(texto_json)
        if "tool_call" in dados and "arguments" in dados:
            return dados
    except json.JSONDecodeError:
        logger.warning(f"JSON inválido encontrado na resposta: {texto_json[:100]}")

    return None


class JarvisAgent:
    """Agente principal do Jarvis Acadêmico."""

    def __init__(self):
        """Inicializa o agente: banco de dados, RAG e configurações."""
        logger.info("Inicializando Jarvis Agent...")

        # Inicializa banco de dados
        database.init_db()
        database.popular_dados_exemplo()
        logger.info("Banco de dados pronto.")

        # Inicializa RAG
        try:
            rag_core.inicializar_rag()
            logger.info("RAG inicializado.")
        except Exception as e:
            logger.error(f"Erro ao inicializar RAG: {e}")
            logger.warning("RAG não disponível. Funcionalidades de busca em materiais limitadas.")

        logger.info("Jarvis Agent inicializado com sucesso!")

    def processar_mensagem(self, mensagem: str, historico: list[dict] = None) -> dict:
        """
        Processa uma mensagem do usuário e retorna a resposta do Jarvis.

        Implementa o loop de tool calling via prompt engineering:
        - Envia para o LLM
        - Se o LLM retornar JSON com tool_call → executa e envia resultado
        - Repete até resposta de texto

        Args:
            mensagem: Texto da mensagem do usuário.
            historico: Lista de mensagens anteriores da conversa.

        Returns:
            Dicionário com:
            - resposta: texto da resposta do Jarvis
            - tool_logs: lista de logs de ferramentas executadas
        """
        logger.info(f"Processando mensagem: '{mensagem[:80]}...'")

        # Monta o histórico de mensagens
        messages = []

        # System prompt
        messages.append({
            "role": "system",
            "content": get_system_prompt()
        })

        # Histórico da conversa (apenas user/assistant, sem mensagens internas de tool)
        if historico:
            messages.extend(historico)

        # Mensagem atual do usuário
        messages.append({
            "role": "user",
            "content": mensagem
        })

        # Log de ferramentas executadas nesta interação
        tool_logs = []

        # Loop de tool calling
        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info(f"Iteração {iteration + 1} do loop de tool calling")

            try:
                resposta_llm = llm_client.chat(messages=messages)
            except Exception as e:
                logger.error(f"Erro na comunicação com LLM: {e}")
                return {
                    "resposta": f"Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente em alguns instantes.",
                    "tool_logs": tool_logs
                }

            # Verifica se a resposta contém uma chamada de ferramenta
            tool_call = _extrair_tool_call(resposta_llm)

            if tool_call is None:
                # Resposta de texto puro — é a resposta final
                logger.info(f"Resposta final obtida na iteração {iteration + 1}")
                return {
                    "resposta": resposta_llm,
                    "tool_logs": tool_logs
                }

            # É uma chamada de ferramenta — executar
            nome = tool_call["tool_call"]
            argumentos = tool_call["arguments"]

            logger.info(f"LLM solicitou ferramenta: {nome}({argumentos})")

            # Executa a ferramenta
            resultado = executar_ferramenta(nome, argumentos)

            # Log da ferramenta (requisito do trabalho)
            tool_log = {
                "ferramenta": nome,
                "entrada": argumentos,
                "saida": resultado
            }
            tool_logs.append(tool_log)
            logger.info(f"Resultado de {nome}: {resultado[:150]}...")

            # Adiciona a tentativa de tool call e o resultado ao histórico
            messages.append({
                "role": "assistant",
                "content": resposta_llm
            })
            messages.append({
                "role": "user",
                "content": f"Resultado da ferramenta {nome}:\n{resultado}\n\nAgora, com base nesse resultado, responda ao usuário de forma natural e informativa em português. Não retorne JSON, responda diretamente ao usuário."
            })

        # Se chegou aqui, atingiu o limite de iterações
        logger.warning(f"Limite de {MAX_TOOL_ITERATIONS} iterações atingido!")
        return {
            "resposta": "Desculpe, não consegui completar o processamento. Tente reformular sua pergunta.",
            "tool_logs": tool_logs
        }
