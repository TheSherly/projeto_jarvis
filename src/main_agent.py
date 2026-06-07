"""
main_agent.py — Agente coordenador do Jarvis Acadêmico.

Implementa o loop principal do agente com tool calling via prompt engineering:
1. Recebe mensagem do usuário
2. Envia para o LLM com system prompt que instrui sobre ferramentas
3. Se o LLM retornar JSONs com tool_call → parseia, executa e envia resultados de volta
4. Repete até o LLM retornar resposta de texto (sem tool_call)
5. Retorna resposta final ao usuário

Suporta:
- Múltiplas chamadas de ferramenta numa mesma resposta (ex: adicionar 2 eventos)
- Raciocínio multi-step (ex: consultar agenda → buscar RAG → responder)

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
MAX_TOOL_ITERATIONS = 10


def _extrair_todos_jsons(texto: str) -> list[str]:
    """
    Extrai todos os objetos JSON completos de um texto usando contagem de chaves.

    Suporta objetos aninhados e múltiplos JSONs na mesma string,
    seja em blocos ```json``` ou diretamente no texto.

    Args:
        texto: Texto que pode conter um ou mais JSONs embutidos.

    Returns:
        Lista de strings, cada uma sendo um JSON completo.
    """
    jsons = []
    i = 0

    while i < len(texto):
        # Procura a próxima abertura de chave
        inicio = texto.find('{', i)
        if inicio == -1:
            break

        profundidade = 0
        in_string = False
        escape = False

        for j in range(inicio, len(texto)):
            c = texto[j]

            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if c == '{':
                profundidade += 1
            elif c == '}':
                profundidade -= 1
                if profundidade == 0:
                    candidato = texto[inicio:j + 1]
                    jsons.append(candidato)
                    i = j + 1
                    break
        else:
            # Saiu do for sem fechar todas as chaves
            break

        if profundidade != 0:
            break

    return jsons


def _extrair_tool_calls(resposta: str) -> list[dict]:
    """
    Extrai todas as chamadas de ferramenta da resposta do LLM.

    O LLM pode retornar uma ou mais chamadas no formato:
    {"tool_call": "nome", "arguments": {...}}

    Args:
        resposta: Texto da resposta do LLM.

    Returns:
        Lista de dicionários com tool_call e arguments.
        Lista vazia se não houver chamadas.
    """
    texto = resposta.strip()

    # Remove marcadores de bloco de código markdown
    texto_limpo = re.sub(r'```(?:json)?\s*', '', texto)
    texto_limpo = texto_limpo.replace('```', '')

    # Extrai todos os JSONs do texto
    jsons_encontrados = _extrair_todos_jsons(texto_limpo)

    tool_calls = []
    for json_str in jsons_encontrados:
        try:
            dados = json.loads(json_str)
            if isinstance(dados, dict) and "tool_call" in dados and "arguments" in dados:
                tool_calls.append(dados)
        except json.JSONDecodeError:
            logger.warning(f"JSON inválido encontrado na resposta: {json_str[:100]}")

    return tool_calls


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
        - Se o LLM retornar JSONs com tool_call → executa todos e envia resultados
        - Repete até resposta de texto (multi-step)

        Suporta:
        - Múltiplas ferramentas numa mesma resposta (paralelo)
        - Chamadas sequenciais em iterações diferentes (multi-step)

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

        # Loop de tool calling (multi-step)
        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info(f"Iteração {iteration + 1} do loop de tool calling")

            try:
                resposta_llm = llm_client.chat(messages=messages)
            except Exception as e:
                logger.error(f"Erro na comunicação com LLM: {e}")
                return {
                    "resposta": "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente em alguns instantes.",
                    "tool_logs": tool_logs
                }

            # Extrai todas as chamadas de ferramenta da resposta
            calls = _extrair_tool_calls(resposta_llm)

            if not calls:
                # Sem tool calls — é a resposta final de texto
                logger.info(f"Resposta final obtida na iteração {iteration + 1}")
                return {
                    "resposta": resposta_llm,
                    "tool_logs": tool_logs
                }

            # Há uma ou mais chamadas de ferramenta — executar todas
            logger.info(f"LLM solicitou {len(calls)} ferramenta(s) na iteração {iteration + 1}")

            # Adiciona a resposta do assistente (com os JSONs) ao histórico
            messages.append({
                "role": "assistant",
                "content": resposta_llm
            })

            # Executa cada ferramenta e coleta os resultados
            resultados_texto = []
            for idx, call in enumerate(calls, 1):
                nome = call["tool_call"]
                argumentos = call["arguments"]

                logger.info(f"Executando ferramenta {idx}/{len(calls)}: {nome}({argumentos})")
                resultado = executar_ferramenta(nome, argumentos)

                # Log da ferramenta (requisito do trabalho)
                tool_log = {
                    "ferramenta": nome,
                    "entrada": argumentos,
                    "saida": resultado
                }
                tool_logs.append(tool_log)
                logger.info(f"Resultado de {nome}: {resultado[:150]}...")

                resultados_texto.append(f"[Ferramenta {idx}: {nome}]\n{resultado}")

            # Envia todos os resultados de volta ao LLM
            todos_resultados = "\n\n".join(resultados_texto)
            messages.append({
                "role": "user",
                "content": (
                    f"Resultados das ferramentas executadas:\n\n{todos_resultados}\n\n"
                    f"Com base nesses resultados, você pode:\n"
                    f"- Chamar mais ferramentas se precisar de mais informações (retorne os JSONs)\n"
                    f"- Ou responder ao usuário de forma natural e informativa em português (sem JSON)"
                )
            })

        # Se chegou aqui, atingiu o limite de iterações
        logger.warning(f"Limite de {MAX_TOOL_ITERATIONS} iterações atingido!")
        return {
            "resposta": "Desculpe, não consegui completar o processamento. Tente reformular sua pergunta.",
            "tool_logs": tool_logs
        }
