"""
tools.py — Implementação das 5 ferramentas obrigatórias do Jarvis Acadêmico.

Cada ferramenta é uma função Python que executa a ação correspondente
e retorna o resultado formatado como string para envio ao LLM.

Todas as chamadas são logadas com: ferramenta, entrada e saída.
"""

import json
import logging
from src import database, rag_core

logger = logging.getLogger(__name__)


def consultar_agenda(data_inicio: str, data_fim: str) -> str:
    """
    Consulta eventos da agenda acadêmica em um intervalo de datas.

    Args:
        data_inicio: Data de início (YYYY-MM-DD).
        data_fim: Data de fim (YYYY-MM-DD).

    Returns:
        String formatada com os eventos encontrados.
    """
    logger.info(f"[TOOL] consultar_agenda | entrada: data_inicio='{data_inicio}', data_fim='{data_fim}'")

    try:
        eventos = database.consultar_agenda(data_inicio, data_fim)

        if not eventos:
            resultado = f"Nenhum evento encontrado na agenda entre {data_inicio} e {data_fim}."
        else:
            linhas = [f"Eventos encontrados ({len(eventos)}):"]
            for e in eventos:
                linhas.append(f"- [{e['tipo_evento'].upper()}] {e['descricao_evento']} — {e['data']} (ID: {e['id']})")
            resultado = "\n".join(linhas)

        logger.info(f"[TOOL] consultar_agenda | saída: {len(eventos)} evento(s)")
        return resultado

    except Exception as e:
        erro = f"Erro ao consultar agenda: {e}"
        logger.error(f"[TOOL] consultar_agenda | erro: {erro}")
        return erro


def listar_tarefas(status: str = None) -> str:
    """
    Lista tarefas, opcionalmente filtradas por status.

    Args:
        status: 'pendente', 'concluida' ou None para todas.

    Returns:
        String formatada com as tarefas.
    """
    logger.info(f"[TOOL] listar_tarefas | entrada: status='{status}'")

    try:
        tarefas = database.listar_tarefas(status)

        if not tarefas:
            filtro = f" com status '{status}'" if status else ""
            resultado = f"Nenhuma tarefa encontrada{filtro}."
        else:
            linhas = [f"Tarefas ({len(tarefas)}):"]
            for t in tarefas:
                status_icon = "✅" if t["status"] == "concluida" else "⏳"
                vinculo = f" (vinculada a: {t['descricao_evento']})" if t.get("descricao_evento") else ""
                linhas.append(f"- {status_icon} [ID {t['id']}] {t['descricao']} — Status: {t['status']}{vinculo}")
            resultado = "\n".join(linhas)

        logger.info(f"[TOOL] listar_tarefas | saída: {len(tarefas)} tarefa(s)")
        return resultado

    except Exception as e:
        erro = f"Erro ao listar tarefas: {e}"
        logger.error(f"[TOOL] listar_tarefas | erro: {erro}")
        return erro


def adicionar_tarefa(descricao: str, agenda_id: int = None) -> str:
    """
    Adiciona uma nova tarefa.

    Args:
        descricao: Descrição da tarefa.
        agenda_id: ID do evento da agenda vinculado (opcional).

    Returns:
        Mensagem de confirmação.
    """
    logger.info(f"[TOOL] adicionar_tarefa | entrada: descricao='{descricao}', agenda_id={agenda_id}")

    try:
        tarefa_id = database.adicionar_tarefa(descricao, agenda_id)
        resultado = f"Tarefa adicionada com sucesso! ID: {tarefa_id}, Descrição: '{descricao}'"

        logger.info(f"[TOOL] adicionar_tarefa | saída: tarefa_id={tarefa_id}")
        return resultado

    except Exception as e:
        erro = f"Erro ao adicionar tarefa: {e}"
        logger.error(f"[TOOL] adicionar_tarefa | erro: {erro}")
        return erro


def concluir_tarefa(tarefa_id: int) -> str:
    """
    Marca uma tarefa como concluída.

    Args:
        tarefa_id: ID da tarefa.

    Returns:
        Mensagem de confirmação ou erro.
    """
    logger.info(f"[TOOL] concluir_tarefa | entrada: tarefa_id={tarefa_id}")

    try:
        sucesso = database.concluir_tarefa(tarefa_id)

        if sucesso:
            resultado = f"Tarefa {tarefa_id} marcada como concluída com sucesso! ✅"
        else:
            resultado = f"Tarefa com ID {tarefa_id} não encontrada. Verifique o ID e tente novamente."

        logger.info(f"[TOOL] concluir_tarefa | saída: sucesso={sucesso}")
        return resultado

    except Exception as e:
        erro = f"Erro ao concluir tarefa: {e}"
        logger.error(f"[TOOL] concluir_tarefa | erro: {erro}")
        return erro


def buscar_material_rag(query: str) -> str:
    """
    Busca informações nos materiais de estudo indexados via RAG.

    Args:
        query: Pergunta ou tópico a ser buscado.

    Returns:
        Trechos relevantes encontrados nos materiais.
    """
    logger.info(f"[TOOL] buscar_material_rag | entrada: query='{query}'")

    try:
        resultados = rag_core.buscar(query, n_results=3)

        if not resultados:
            resultado = "Nenhum material relevante encontrado nos documentos indexados. Certifique-se de que há documentos na pasta data/."
        else:
            linhas = [f"Trechos relevantes encontrados ({len(resultados)}):"]
            for i, r in enumerate(resultados, 1):
                linhas.append(f"\n--- Trecho {i} (Fonte: {r['fonte']}) ---")
                linhas.append(r["texto"])
            resultado = "\n".join(linhas)

        logger.info(f"[TOOL] buscar_material_rag | saída: {len(resultados)} trecho(s)")
        return resultado

    except Exception as e:
        erro = f"Erro ao buscar material: {e}"
        logger.error(f"[TOOL] buscar_material_rag | erro: {erro}")
        return erro


# Mapeamento nome → função para o agente executar
TOOL_MAP = {
    "consultar_agenda": consultar_agenda,
    "listar_tarefas": listar_tarefas,
    "adicionar_tarefa": adicionar_tarefa,
    "concluir_tarefa": concluir_tarefa,
    "buscar_material_rag": buscar_material_rag,
}


def executar_ferramenta(nome: str, argumentos: dict) -> str:
    """
    Executa uma ferramenta pelo nome com os argumentos fornecidos.

    Args:
        nome: Nome da ferramenta.
        argumentos: Dicionário com os argumentos.

    Returns:
        Resultado da execução como string.
    """
    if nome not in TOOL_MAP:
        erro = f"Ferramenta '{nome}' não encontrada. Ferramentas disponíveis: {list(TOOL_MAP.keys())}"
        logger.error(erro)
        return erro

    func = TOOL_MAP[nome]
    return func(**argumentos)
