"""
database.py — Camada de persistência com SQLite.

Gerencia as tabelas 'agenda' e 'tarefas' do Jarvis Acadêmico.
Todas as operações são logadas para rastreabilidade.
"""

import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Caminho do banco de dados (raiz do projeto)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis_academico.db")


def get_connection():
    """Cria e retorna uma conexão com o banco SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Retorna dicts em vez de tuples
    conn.execute("PRAGMA foreign_keys = ON")  # Habilita chaves estrangeiras
    return conn


def init_db():
    """
    Cria as tabelas 'agenda' e 'tarefas' caso não existam.
    Deve ser chamada na inicialização do sistema.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao_evento TEXT NOT NULL,
            data TEXT NOT NULL,
            tipo_evento TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            agenda_id INTEGER,
            FOREIGN KEY (agenda_id) REFERENCES agenda(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Banco de dados inicializado com sucesso.")


# =============================================================================
# CRUD — Agenda
# =============================================================================

def adicionar_evento(descricao_evento: str, data: str, tipo_evento: str) -> int:
    """
    Adiciona um evento na agenda.

    Args:
        descricao_evento: Descrição do evento (ex: "Aula de IA")
        data: Data no formato ISO (YYYY-MM-DD ou YYYY-MM-DD HH:MM)
        tipo_evento: Tipo do evento (aula, prova, trabalho, reuniao, etc.)

    Returns:
        ID do evento criado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO agenda (descricao_evento, data, tipo_evento) VALUES (?, ?, ?)",
        (descricao_evento, data, tipo_evento)
    )
    conn.commit()
    evento_id = cursor.lastrowid
    conn.close()
    logger.info(f"Evento adicionado: id={evento_id}, desc='{descricao_evento}', data='{data}', tipo='{tipo_evento}'")
    return evento_id


def consultar_agenda(data_inicio: str = None, data_fim: str = None) -> list[dict]:
    """
    Consulta eventos da agenda filtrados por intervalo de datas.

    Args:
        data_inicio: Data de início do filtro (YYYY-MM-DD). Se None, sem limite inferior.
        data_fim: Data de fim do filtro (YYYY-MM-DD). Se None, sem limite superior.

    Returns:
        Lista de dicionários com os eventos encontrados.
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id, descricao_evento, data, tipo_evento FROM agenda"
    params = []
    conditions = []

    if data_inicio:
        conditions.append("data >= ?")
        params.append(data_inicio)
    if data_fim:
        conditions.append("data <= ?")
        params.append(data_fim + " 23:59:59")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY data ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    resultados = [dict(row) for row in rows]
    logger.info(f"Consulta agenda: inicio='{data_inicio}', fim='{data_fim}' → {len(resultados)} evento(s)")
    return resultados


def listar_todos_eventos() -> list[dict]:
    """Retorna todos os eventos da agenda ordenados por data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, descricao_evento, data, tipo_evento FROM agenda ORDER BY data ASC")
    rows = cursor.fetchall()
    conn.close()
    resultados = [dict(row) for row in rows]
    logger.info(f"Listagem completa da agenda: {len(resultados)} evento(s)")
    return resultados


# =============================================================================
# CRUD — Tarefas
# =============================================================================

def adicionar_tarefa(descricao: str, agenda_id: int = None) -> int:
    """
    Adiciona uma tarefa.

    Args:
        descricao: Descrição da tarefa.
        agenda_id: ID do evento da agenda associado (opcional).

    Returns:
        ID da tarefa criada.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tarefas (descricao, status, agenda_id) VALUES (?, 'pendente', ?)",
        (descricao, agenda_id)
    )
    conn.commit()
    tarefa_id = cursor.lastrowid
    conn.close()
    logger.info(f"Tarefa adicionada: id={tarefa_id}, desc='{descricao}', agenda_id={agenda_id}")
    return tarefa_id


def listar_tarefas(status: str = None) -> list[dict]:
    """
    Lista tarefas, opcionalmente filtradas por status.

    Args:
        status: Filtro de status ('pendente', 'concluida'). Se None, retorna todas.

    Returns:
        Lista de dicionários com as tarefas.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute(
            "SELECT t.id, t.descricao, t.status, t.agenda_id, a.descricao_evento "
            "FROM tarefas t LEFT JOIN agenda a ON t.agenda_id = a.id "
            "WHERE t.status = ? ORDER BY t.id ASC",
            (status,)
        )
    else:
        cursor.execute(
            "SELECT t.id, t.descricao, t.status, t.agenda_id, a.descricao_evento "
            "FROM tarefas t LEFT JOIN agenda a ON t.agenda_id = a.id "
            "ORDER BY t.id ASC"
        )

    rows = cursor.fetchall()
    conn.close()

    resultados = [dict(row) for row in rows]
    logger.info(f"Listagem tarefas (status='{status}'): {len(resultados)} tarefa(s)")
    return resultados


def concluir_tarefa(tarefa_id: int) -> bool:
    """
    Marca uma tarefa como concluída.

    Args:
        tarefa_id: ID da tarefa a ser concluída.

    Returns:
        True se a tarefa foi encontrada e atualizada, False caso contrário.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tarefas SET status = 'concluida' WHERE id = ?",
        (tarefa_id,)
    )
    conn.commit()
    atualizado = cursor.rowcount > 0
    conn.close()

    if atualizado:
        logger.info(f"Tarefa {tarefa_id} concluída com sucesso.")
    else:
        logger.warning(f"Tarefa {tarefa_id} não encontrada.")

    return atualizado


# =============================================================================
# Dados de exemplo para demonstração
# =============================================================================

def popular_dados_exemplo():
    """Popula o banco com dados de exemplo se estiver vazio."""
    conn = get_connection()
    cursor = conn.cursor()

    # Verifica se já existem dados
    cursor.execute("SELECT COUNT(*) FROM agenda")
    if cursor.fetchone()[0] > 0:
        conn.close()
        logger.info("Banco já possui dados, pulando população de exemplo.")
        return

    # Eventos de exemplo
    eventos = [
        ("Aula de Inteligência Artificial", "2026-05-16 08:00", "aula"),
        ("Aula de Banco de Dados", "2026-05-16 10:00", "aula"),
        ("Prova de Inteligência Artificial", "2026-05-20 08:00", "prova"),
        ("Entrega do Trabalho de IA", "2026-05-22 23:59", "trabalho"),
        ("Aula de Estrutura de Dados", "2026-05-19 14:00", "aula"),
        ("Reunião do grupo de IA", "2026-05-17 15:00", "reuniao"),
        ("Aula de Inteligência Artificial", "2026-05-19 08:00", "aula"),
        ("Aula de Banco de Dados", "2026-05-19 10:00", "aula"),
    ]

    for desc, data, tipo in eventos:
        cursor.execute(
            "INSERT INTO agenda (descricao_evento, data, tipo_evento) VALUES (?, ?, ?)",
            (desc, data, tipo)
        )

    # Tarefas de exemplo
    tarefas = [
        ("Estudar capítulo 5 de IA - Redes Neurais", None),
        ("Fazer exercícios de SQL", None),
        ("Implementar RAG do trabalho de IA", 4),  # Vinculada ao trabalho de IA
        ("Revisar slides de embeddings", None),
    ]

    for desc, agenda_id in tarefas:
        cursor.execute(
            "INSERT INTO tarefas (descricao, status, agenda_id) VALUES (?, 'pendente', ?)",
            (desc, agenda_id)
        )

    conn.commit()
    conn.close()
    logger.info("Dados de exemplo populados com sucesso.")
