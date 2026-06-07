"""
app.py — Interface gráfica do Jarvis Acadêmico com Streamlit.

Implementa:
- Chat interativo com histórico de mensagens
- Sidebar com status do RAG e ações rápidas
- Exibição de logs de tool calling em expanders
- Modo Questionário interativo com múltipla escolha e resumo final
"""

import streamlit as st
import logging
import sys
import os
import json

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main_agent import JarvisAgent
from src import database, rag_core
from src.tools import gerar_questionario

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis.log"),
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuração da página
# =============================================================================
st.set_page_config(
    page_title="JARVIS Acadêmico",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CSS customizado
# =============================================================================
st.markdown("""
<style>
    /* Ocultar o menu (3 pontos) e o botão de deploy */
    #MainMenu { visibility: hidden; }
    .stAppDeployButton { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }

    /* Zera o tamanho da fonte do texto original para fazê-lo sumir */
    div[data-testid="InputInstructions"] > span {
        font-size: 0 !important;
    }
    div[data-testid="InputInstructions"] > span::after {
        content: "" !important;
        font-size: 11px !important;
        color: #a3a8b4 !important;
        font-style: italic;
    }
    /* Esconder steppers do number_input */
    [data-testid="stNumberInputStepUp"],
    [data-testid="stNumberInputStepDown"] {
        display: none !important;
    }

    /* Importa fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Header estilizado */
    .jarvis-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
    }
    .jarvis-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
    .jarvis-header p { margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9; }

    /* Cards da sidebar */
    .status-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem; border-radius: 10px; margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .status-card h4 { margin: 0 0 0.5rem 0; color: #333; }
    .status-card p { margin: 0; color: #555; font-size: 0.9rem; }

    /* Tool log estilizado */
    .tool-log {
        background: #1e1e2e; color: #cdd6f4; padding: 0.8rem;
        border-radius: 8px; font-family: 'Courier New', monospace;
        font-size: 0.85rem; margin: 0.5rem 0; border-left: 3px solid #89b4fa;
    }
    .tool-name { color: #89b4fa; font-weight: bold; }
    .tool-input { color: #a6e3a1; }
    .tool-output { color: #f9e2af; }

    .stChatMessage { border-radius: 12px !important; }

    .stButton > button {
        border-radius: 8px; font-weight: 500; transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* ========== ESTILOS DO QUESTIONÁRIO ========== */
    .quiz-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
        color: white; text-align: center;
    }
    .quiz-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .quiz-header p { margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9; }

    .quiz-question-card {
        background: #ffffff; padding: 1.5rem; border-radius: 12px;
        margin-bottom: 1rem; border: 2px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .quiz-question-num {
        color: #667eea; font-weight: 700; font-size: 0.9rem;
        text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;
    }
    .quiz-question-text {
        font-size: 1.1rem; font-weight: 500; color: #1a1a2e;
        margin-bottom: 1rem; line-height: 1.5;
    }

    /* Botões de alternativa */
    .alt-btn {
        display: block; width: 100%; padding: 0.8rem 1rem;
        margin: 0.4rem 0; border-radius: 10px; border: 2px solid #d0d0d0;
        background: #fafafa; text-align: left; font-size: 0.95rem;
        cursor: pointer; transition: all 0.2s ease; color: #333;
    }
    .alt-btn:hover { border-color: #667eea; background: #f0f0ff; }

    .alt-correct {
        border-color: #2ecc71 !important; background: #e8f8f0 !important;
        color: #1a7a42 !important; font-weight: 600;
    }
    .alt-wrong {
        border-color: #e74c3c !important; background: #fde8e8 !important;
        color: #a93226 !important;
    }
    .alt-neutral-after {
        border-color: #d0d0d0; background: #f5f5f5;
        color: #999; cursor: default;
    }

    .explicacao-box {
        padding: 1rem; border-radius: 8px; margin-top: 0.8rem;
        font-size: 0.9rem; line-height: 1.5;
    }
    .explicacao-correct {
        background: #e8f8f0; border-left: 4px solid #2ecc71; color: #1a5c32;
    }
    .explicacao-wrong {
        background: #fde8e8; border-left: 4px solid #e74c3c; color: #922b21;
    }

    /* Resumo final */
    .resultado-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem; border-radius: 12px; color: white;
        text-align: center; margin-bottom: 1.5rem;
    }
    .resultado-header h1 { margin: 0; font-size: 2rem; }
    .resultado-header .score { font-size: 3rem; font-weight: 700; margin: 0.5rem 0; }

    .stat-card {
        padding: 1.2rem; border-radius: 10px; text-align: center;
        margin-bottom: 0.8rem;
    }
    .stat-card-green {
        background: linear-gradient(135deg, #d4efdf 0%, #a9dfbf 100%);
        border: 2px solid #2ecc71;
    }
    .stat-card-red {
        background: linear-gradient(135deg, #fadbd8 0%, #f1948a 100%);
        border: 2px solid #e74c3c;
    }
    .stat-card h3 { margin: 0; font-size: 2rem; }
    .stat-card p { margin: 0.3rem 0 0 0; font-size: 0.9rem; color: #555; }

    .topic-row {
        padding: 0.6rem 1rem; border-radius: 8px; margin: 0.3rem 0;
        display: flex; justify-content: space-between; align-items: center;
    }
    .topic-good { background: #e8f8f0; border-left: 4px solid #2ecc71; }
    .topic-bad { background: #fde8e8; border-left: 4px solid #e74c3c; }
    .topic-mid { background: #fef9e7; border-left: 4px solid #f39c12; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Inicialização do estado da sessão
# =============================================================================
if "agent" not in st.session_state:
    with st.spinner("🚀 Inicializando JARVIS Acadêmico..."):
        st.session_state.agent = JarvisAgent()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tool_logs_history" not in st.session_state:
    st.session_state.tool_logs_history = []

# Estado do questionário
if "quiz_mode" not in st.session_state:
    st.session_state.quiz_mode = None  # None, "quiz", "resultado"

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None

if "quiz_respostas" not in st.session_state:
    st.session_state.quiz_respostas = {}  # {questao_id: letra_escolhida}


def iniciar_questionario(tema: str, num_questoes: int):
    """Gera o questionário e entra no modo quiz."""
    resultado_json = gerar_questionario(tema, num_questoes)
    dados = json.loads(resultado_json)

    if "erro" in dados:
        st.error(f"❌ {dados['erro']}")
        return

    st.session_state.quiz_data = dados
    st.session_state.quiz_respostas = {}
    st.session_state.quiz_mode = "quiz"


def finalizar_questionario():
    """Volta ao modo chat."""
    st.session_state.quiz_mode = None
    st.session_state.quiz_data = None
    st.session_state.quiz_respostas = {}


# =============================================================================
# Sidebar (sempre visível)
# =============================================================================
with st.sidebar:
    st.markdown("## 🎓 JARVIS Acadêmico")
    st.markdown("---")

    # Ações rápidas — Agenda
    st.markdown("### 📅 Adicionar Evento")
    with st.form("form_evento", clear_on_submit=True):
        desc_evento = st.text_input("Descrição do evento", placeholder="Ex: Aula de IA")
        data_evento = st.date_input("Data")
        hora_evento = st.time_input("Hora")
        tipo_evento = st.selectbox("Tipo", ["aula", "prova", "trabalho", "reuniao", "outro"])
        submit_evento = st.form_submit_button("➕ Adicionar Evento")
        if submit_evento and desc_evento.strip():
            data_hora = f"{data_evento} {hora_evento.strftime('%H:%M')}"
            database.adicionar_evento(desc_evento, data_hora, tipo_evento)
            st.success(f"Evento '{desc_evento}' adicionado!")
            st.rerun()

    st.markdown("---")

    # Ações rápidas — Tarefas
    st.markdown("### ✅ Adicionar Tarefa Rápida")
    with st.form("form_tarefa", clear_on_submit=True):
        desc_tarefa = st.text_input("Descrição da tarefa", placeholder="Ex: Estudar cap. 5")
        id_agenda = st.number_input("ID da agenda(Opcional)", min_value=0, step=1, value=None, placeholder="Ex: 5")
        submit_tarefa = st.form_submit_button("➕ Adicionar Tarefa")
        if submit_tarefa and desc_tarefa.strip():
            if id_agenda is not None:
                id_agenda = int(id_agenda)
            database.adicionar_tarefa(desc_tarefa, id_agenda)
            st.success(f"Tarefa '{desc_tarefa}' adicionada!")
            st.rerun()

    st.markdown("---")

    # Botão para limpar chat
    if st.button("🗑️ Limpar Conversa", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tool_logs_history = []
        st.rerun()

    st.markdown("---")

    # Status do RAG
    st.markdown("### 📚 Status do RAG")
    try:
        rag_status = rag_core.get_status()
        st.markdown(f"""
        <div class="status-card">
            <h4>📊 Materiais Indexados</h4>
            <p><strong>Chunks:</strong> {rag_status['total_chunks']}</p>
            <p><strong>Modelo:</strong> {rag_status['modelo_embeddings']}</p>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.warning("RAG não inicializado.")


# =============================================================================
# ROTEAMENTO: Quiz ou Chat
# =============================================================================

if st.session_state.quiz_mode == "quiz" and st.session_state.quiz_data:
    # =========================================================================
    # TELA DE QUESTIONÁRIO
    # =========================================================================
    questoes = st.session_state.quiz_data.get("questoes", [])

    st.markdown(f"""
    <div class="quiz-header">
        <h1>📝 Questionário Interativo</h1>
        <p>{len(questoes)} questões • Clique na alternativa para responder</p>
    </div>
    """, unsafe_allow_html=True)

    todas_respondidas = True

    for q in questoes:
        qid = q["id"]
        respondida = qid in st.session_state.quiz_respostas
        resposta_user = st.session_state.quiz_respostas.get(qid)
        correta = q["resposta_correta"]
        acertou = resposta_user == correta if respondida else None

        if not respondida:
            todas_respondidas = False

        # Card da questão
        conteudo_tag = f"<span style='color:#888;font-size:0.85rem;'>📘 {q.get('conteudo', 'Geral')}</span>"
        st.markdown(f"""
        <div class="quiz-question-card">
            <div class="quiz-question-num">Questão {qid} de {len(questoes)}</div>
            {conteudo_tag}
            <div class="quiz-question-text">{q['pergunta']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Alternativas
        for alt in q["alternativas"]:
            letra = alt["letra"]
            texto_alt = f"{letra}) {alt['texto']}"

            if respondida:
                # Já respondeu — mostra feedback visual
                if letra == correta:
                    st.markdown(f'<div class="alt-btn alt-correct">✅ {texto_alt}</div>', unsafe_allow_html=True)
                elif letra == resposta_user:
                    st.markdown(f'<div class="alt-btn alt-wrong">❌ {texto_alt}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="alt-btn alt-neutral-after">{texto_alt}</div>', unsafe_allow_html=True)
            else:
                # Ainda não respondeu — botão clicável
                if st.button(texto_alt, key=f"q{qid}_{letra}", use_container_width=True):
                    st.session_state.quiz_respostas[qid] = letra
                    st.rerun()

        # Explicação (só aparece após responder)
        if respondida:
            classe = "explicacao-correct" if acertou else "explicacao-wrong"
            icone = "✅" if acertou else "❌"
            titulo = "Correto!" if acertou else f"Incorreto — A resposta correta é {correta}"
            st.markdown(f"""
            <div class="explicacao-box {classe}">
                <strong>{icone} {titulo}</strong><br>
                {q.get('explicacao', '')}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

    # Botão de finalizar (só aparece quando todas respondidas)
    if todas_respondidas:
        st.markdown("")
        if st.button("📊 Ver Resultados", use_container_width=True, type="primary"):
            st.session_state.quiz_mode = "resultado"
            st.rerun()


elif st.session_state.quiz_mode == "resultado" and st.session_state.quiz_data:
    # =========================================================================
    # TELA DE RESULTADOS
    # =========================================================================
    questoes = st.session_state.quiz_data.get("questoes", [])
    respostas = st.session_state.quiz_respostas
    total = len(questoes)

    # Calcula estatísticas
    acertos = sum(1 for q in questoes if respostas.get(q["id"]) == q["resposta_correta"])
    erros = total - acertos
    percentual = (acertos / total * 100) if total > 0 else 0

    # Header do resultado
    emoji_resultado = "🏆" if percentual >= 80 else "👍" if percentual >= 60 else "📚"
    st.markdown(f"""
    <div class="resultado-header">
        <h1>{emoji_resultado} Resultado do Questionário</h1>
        <div class="score">{acertos}/{total}</div>
        <p>{percentual:.0f}% de aproveitamento</p>
    </div>
    """, unsafe_allow_html=True)

    # Cards de acertos e erros
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stat-card stat-card-green">
            <h3>✅ {acertos}</h3>
            <p>Acertos</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card stat-card-red">
            <h3>❌ {erros}</h3>
            <p>Erros</p>
        </div>
        """, unsafe_allow_html=True)

    # Desempenho por conteúdo
    st.markdown("### 📊 Desempenho por Conteúdo")
    conteudo_stats = {}
    for q in questoes:
        conteudo = q.get("conteudo", "Geral")
        if conteudo not in conteudo_stats:
            conteudo_stats[conteudo] = {"acertos": 0, "total": 0}
        conteudo_stats[conteudo]["total"] += 1
        if respostas.get(q["id"]) == q["resposta_correta"]:
            conteudo_stats[conteudo]["acertos"] += 1

    for conteudo, stats in conteudo_stats.items():
        pct = (stats["acertos"] / stats["total"] * 100) if stats["total"] > 0 else 0
        classe = "topic-good" if pct >= 70 else "topic-bad" if pct < 50 else "topic-mid"
        icone = "✅" if pct >= 70 else "❌" if pct < 50 else "⚠️"
        st.markdown(f"""
        <div class="topic-row {classe}">
            <span>{icone} <strong>{conteudo}</strong></span>
            <span>{stats['acertos']}/{stats['total']} ({pct:.0f}%)</span>
        </div>
        """, unsafe_allow_html=True)

    # Conteúdos que precisam de mais estudo
    conteudos_fracos = [c for c, s in conteudo_stats.items()
                        if (s["acertos"] / s["total"] * 100) < 70]
    if conteudos_fracos:
        st.markdown("### 📚 Conteúdos para Revisar")
        st.warning(
            "Com base no seu desempenho, recomendamos revisar os seguintes conteúdos:\n\n"
            + "\n".join([f"- **{c}** ({conteudo_stats[c]['acertos']}/{conteudo_stats[c]['total']} acertos)" for c in conteudos_fracos])
        )
    else:
        st.success("🎉 Excelente! Você demonstrou bom domínio em todos os conteúdos!")

    # Botão de finalizar
    st.markdown("")
    if st.button("🏠 Finalizar Questionário e Voltar ao Chat", use_container_width=True, type="primary"):
        finalizar_questionario()
        st.rerun()


else:
    # =========================================================================
    # TELA PRINCIPAL — CHAT
    # =========================================================================

    # Header
    st.markdown("""
    <div class="jarvis-header">
        <h1>🤖 JARVIS Acadêmico</h1>
        <p>Seu assistente pessoal para organização e estudos universitários</p>
    </div>
    """, unsafe_allow_html=True)

    # Exibir histórico de mensagens
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="🎓" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

            # Exibir logs de ferramentas (se houver)
            if msg["role"] == "assistant" and i < len(st.session_state.tool_logs_history):
                logs = st.session_state.tool_logs_history[i]
                if logs:
                    with st.expander(f"🔧 Ferramentas utilizadas ({len(logs)})", expanded=False):
                        for log in logs:
                            st.markdown(f"""
                            <div class="tool-log">
                                <span class="tool-name">🔧 {log['ferramenta']}</span><br>
                                <span class="tool-input">📥 Entrada: {log['entrada']}</span><br>
                                <span class="tool-output">📤 Saída: {log['saida'][:200]}{'...' if len(log['saida']) > 200 else ''}</span>
                            </div>
                            """, unsafe_allow_html=True)

    # Formulário de geração de questionário
    with st.expander("📝 Gerar Questionário", expanded=False):
        with st.form("form_quiz", clear_on_submit=False):
            quiz_tema = st.text_input(
                "Tema do questionário",
                placeholder="Ex: Redes Neurais, Governança de TI, Sistemas Distribuídos..."
            )
            quiz_num = st.slider("Número de questões", min_value=3, max_value=10, value=5)
            quiz_submit = st.form_submit_button("🚀 Gerar Questionário", use_container_width=True)

            if quiz_submit and quiz_tema.strip():
                with st.spinner("🤖 Gerando questões baseadas nos materiais de estudo..."):
                    iniciar_questionario(quiz_tema.strip(), quiz_num)
                if st.session_state.quiz_mode == "quiz":
                    st.rerun()

    # Input do usuário (chat normal)
    if prompt := st.chat_input("Digite sua mensagem para o JARVIS..."):
        # Adiciona mensagem do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.tool_logs_history.append([])  # Placeholder para logs do user

        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Processa a mensagem com o agente
        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("🤔 Pensando..."):
                # Monta histórico para o agente (sem system, apenas user/assistant)
                historico = []
                for msg in st.session_state.messages[:-1]:  # Exclui mensagem atual
                    historico.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

                resultado = st.session_state.agent.processar_mensagem(prompt, historico)

            resposta = resultado["resposta"]
            tool_logs = resultado["tool_logs"]

            st.markdown(resposta)

            # Exibir logs de ferramentas
            if tool_logs:
                with st.expander(f"🔧 Ferramentas utilizadas ({len(tool_logs)})", expanded=False):
                    for log in tool_logs:
                        st.markdown(f"""
                        <div class="tool-log">
                            <span class="tool-name">🔧 {log['ferramenta']}</span><br>
                            <span class="tool-input">📥 Entrada: {log['entrada']}</span><br>
                            <span class="tool-output">📤 Saída: {log['saida'][:200]}{'...' if len(log['saida']) > 200 else ''}</span>
                        </div>
                        """, unsafe_allow_html=True)

        # Salva resposta e logs no histórico
        st.session_state.messages.append({"role": "assistant", "content": resposta})
        st.session_state.tool_logs_history.append(tool_logs)
