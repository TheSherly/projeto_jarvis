"""
app.py — Interface gráfica do Jarvis Acadêmico com Streamlit.

Implementa um chat interativo com:
- Histórico de mensagens persistente na sessão
- Sidebar com status do RAG e ações rápidas
- Exibição de logs de tool calling em expanders
"""

import streamlit as st
import logging
import sys
import os

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main_agent import JarvisAgent
from src import database, rag_core

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
    /* Importa fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Aplica fonte globalmente */
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
    .jarvis-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .jarvis-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
        opacity: 0.9;
    }

    /* Cards da sidebar */
    .status-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .status-card h4 {
        margin: 0 0 0.5rem 0;
        color: #333;
    }
    .status-card p {
        margin: 0;
        color: #555;
        font-size: 0.9rem;
    }

    /* Tool log estilizado */
    .tool-log {
        background: #1e1e2e;
        color: #cdd6f4;
        padding: 0.8rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        margin: 0.5rem 0;
        border-left: 3px solid #89b4fa;
    }
    .tool-name {
        color: #89b4fa;
        font-weight: bold;
    }
    .tool-input {
        color: #a6e3a1;
    }
    .tool-output {
        color: #f9e2af;
    }

    /* Estilo das mensagens de chat */
    .stChatMessage {
        border-radius: 12px !important;
    }

    /* Botões da sidebar */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
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

# =============================================================================
# Sidebar
# =============================================================================
with st.sidebar:
    st.markdown("## 🎓 JARVIS Acadêmico")
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

    st.markdown("---")

    # Ações rápidas — Agenda
    st.markdown("### 📅 Adicionar Evento")
    with st.form("form_evento", clear_on_submit=True):
        desc_evento = st.text_input("Descrição do evento", placeholder="Ex: Aula de IA")
        data_evento = st.date_input("Data")
        hora_evento = st.time_input("Hora")
        tipo_evento = st.selectbox("Tipo", ["aula", "prova", "trabalho", "reuniao", "outro"])
        submit_evento = st.form_submit_button("➕ Adicionar Evento")

        if submit_evento and desc_evento:
            data_hora = f"{data_evento} {hora_evento.strftime('%H:%M')}"
            database.adicionar_evento(desc_evento, data_hora, tipo_evento)
            st.success(f"Evento '{desc_evento}' adicionado!")
            st.rerun()

    st.markdown("---")

    # Ações rápidas — Tarefas
    st.markdown("### ✅ Adicionar Tarefa Rápida")
    with st.form("form_tarefa", clear_on_submit=True):
        desc_tarefa = st.text_input("Descrição da tarefa", placeholder="Ex: Estudar cap. 5")
        submit_tarefa = st.form_submit_button("➕ Adicionar Tarefa")

        if submit_tarefa and desc_tarefa:
            database.adicionar_tarefa(desc_tarefa)
            st.success(f"Tarefa '{desc_tarefa}' adicionada!")
            st.rerun()

    st.markdown("---")

    # Botão para limpar chat
    if st.button("🗑️ Limpar Conversa", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tool_logs_history = []
        st.rerun()

# =============================================================================
# Área principal — Chat
# =============================================================================

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

# Input do usuário
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
