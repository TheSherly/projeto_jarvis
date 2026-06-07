"""
tools.py — Implementação das ferramentas do Jarvis Acadêmico.

Cada ferramenta é uma função Python que executa a ação correspondente
e retorna o resultado formatado como string para envio ao LLM.

Todas as chamadas são logadas com: ferramenta, entrada e saída.
"""

import json
import logging
from src import database, rag_core, llm_client

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


def adicionar_agenda(descricao_evento: str, data: str, tipo_evento: str = "outro") -> str:
    """
    Adiciona um novo evento na agenda acadêmica.

    Args:
        descricao_evento: Descrição do evento (ex: "Prova de Cálculo").
        data: Data e hora do evento (YYYY-MM-DD ou YYYY-MM-DD HH:MM).
        tipo_evento: Tipo do evento (aula, prova, trabalho, reuniao, outro). Padrão: "outro".

    Returns:
        Mensagem de confirmação.
    """
    logger.info(f"[TOOL] adicionar_agenda | entrada: descricao='{descricao_evento}', data='{data}', tipo='{tipo_evento}'")

    try:
        evento_id = database.adicionar_evento(descricao_evento, data, tipo_evento)
        resultado = f"Evento adicionado com sucesso! ID: {evento_id}, Descrição: '{descricao_evento}', Data: {data}, Tipo: {tipo_evento}"

        logger.info(f"[TOOL] adicionar_agenda | saída: evento_id={evento_id}")
        return resultado

    except Exception as e:
        erro = f"Erro ao adicionar evento na agenda: {e}"
        logger.error(f"[TOOL] adicionar_agenda | erro: {erro}")
        return erro


def gerar_questionario(tema: str, num_questoes: int = 5) -> str:
    """
    Gera um questionário de múltipla escolha baseado nos materiais de estudo.

    Busca conteúdo relevante via RAG e envia ao LLM para gerar questões
    estruturadas em formato JSON.

    Args:
        tema: Tema ou tópico para gerar as questões.
        num_questoes: Número de questões a gerar (padrão: 5).

    Returns:
        String JSON com as questões geradas.
    """
    logger.info(f"[TOOL] gerar_questionario | entrada: tema='{tema}', num_questoes={num_questoes}")

    try:
        # Busca conteúdo relevante nos materiais
        resultados = rag_core.buscar(tema, n_results=5)

        if not resultados:
            return json.dumps({"erro": "Nenhum material encontrado sobre este tema."}, ensure_ascii=False)

        # Monta o contexto com os trechos encontrados
        contexto = "\n\n".join([f"[Fonte: {r['fonte']}]\n{r['texto']}" for r in resultados])

        # Identifica os conteúdos/fontes únicos para categorização
        fontes = list(set(r["fonte"] for r in resultados))

        prompt_quiz = f"""Com base no conteúdo acadêmico abaixo, gere exatamente {num_questoes} questões de múltipla escolha.

CONTEÚDO:
{contexto}

RETORNE APENAS um JSON válido no formato abaixo, sem texto antes ou depois:
{{
  "questoes": [
    {{
      "id": 1,
      "conteudo": "Nome do conteúdo/tópico da questão",
      "pergunta": "Texto da pergunta?",
      "alternativas": [
        {{"letra": "A", "texto": "Alternativa A"}},
        {{"letra": "B", "texto": "Alternativa B"}},
        {{"letra": "C", "texto": "Alternativa C"}},
        {{"letra": "D", "texto": "Alternativa D"}}
      ],
      "resposta_correta": "A",
      "explicacao": "Explicação detalhada de por que esta é a resposta correta."
    }}
  ]
}}

REGRAS:
- Gere exatamente {num_questoes} questões
- Cada questão deve ter exatamente 4 alternativas (A, B, C, D)
- As questões devem ser baseadas APENAS no conteúdo fornecido
- O campo "conteudo" deve indicar o tópico específico da questão
- A explicação deve ser clara e educativa
- Varie a posição da resposta correta entre as alternativas
- As fontes disponíveis são: {', '.join(fontes)}
- Retorne SOMENTE o JSON, sem texto adicional"""

        messages = [
            {"role": "system", "content": "Você é um gerador de questões acadêmicas. Retorne APENAS JSON válido."},
            {"role": "user", "content": prompt_quiz}
        ]

        resposta = llm_client.chat(messages=messages)

        # Tenta extrair o JSON da resposta
        resposta_limpa = resposta.strip()
        # Remove blocos de código markdown se presentes
        if "```" in resposta_limpa:
            import re
            json_match = re.search(r'```(?:json)?\s*(.+?)\s*```', resposta_limpa, re.DOTALL)
            if json_match:
                resposta_limpa = json_match.group(1)

        # Valida que é JSON válido
        dados = json.loads(resposta_limpa)
        resultado = json.dumps(dados, ensure_ascii=False)

        logger.info(f"[TOOL] gerar_questionario | saída: {len(dados.get('questoes', []))} questão(ões)")
        return resultado

    except json.JSONDecodeError as e:
        logger.error(f"[TOOL] gerar_questionario | erro JSON: {e}")
        return json.dumps({"erro": f"Erro ao parsear questionário gerado: {e}"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[TOOL] gerar_questionario | erro: {e}")
        return json.dumps({"erro": f"Erro ao gerar questionário: {e}"}, ensure_ascii=False)


# Mapeamento nome → função para o agente executar
TOOL_MAP = {
    "consultar_agenda": consultar_agenda,
    "adicionar_agenda": adicionar_agenda,
    "listar_tarefas": listar_tarefas,
    "adicionar_tarefa": adicionar_tarefa,
    "concluir_tarefa": concluir_tarefa,
    "buscar_material_rag": buscar_material_rag,
    "gerar_questionario": gerar_questionario,
}


def executar_ferramenta(nome: str, argumentos: dict) -> str:
    """
    Executa uma ferramenta pelo nome com os argumentos fornecidos.

    Realiza coerção de tipos para garantir que argumentos numéricos
    sejam convertidos corretamente (o LLM pode enviar como string).

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

    # Coerção de tipos — o LLM pode enviar números como strings
    args = dict(argumentos)

    # Converte tarefa_id para int se presente
    if "tarefa_id" in args and args["tarefa_id"] is not None:
        try:
            args["tarefa_id"] = int(args["tarefa_id"])
        except (ValueError, TypeError):
            return f"Erro: tarefa_id '{args['tarefa_id']}' não é um número válido."

    # Converte agenda_id para int se presente
    if "agenda_id" in args and args["agenda_id"] is not None:
        try:
            args["agenda_id"] = int(args["agenda_id"])
        except (ValueError, TypeError):
            args["agenda_id"] = None

    # Trata status vazio como None (sem filtro)
    if "status" in args and not args["status"]:
        args["status"] = None

    # Define tipo_evento padrão como "outro" se não informado
    if "tipo_evento" in args and not args["tipo_evento"]:
        args["tipo_evento"] = "outro"

    # Converte num_questoes para int se presente
    if "num_questoes" in args and args["num_questoes"] is not None:
        try:
            args["num_questoes"] = int(args["num_questoes"])
        except (ValueError, TypeError):
            args["num_questoes"] = 5

    func = TOOL_MAP[nome]
    return func(**args)

