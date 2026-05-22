# JARVIS Acadêmico

> JARVIS Acadêmico é um chatbot que utiliza inteligência artificial para auxiliar estudantes em suas atividades acadêmicas. Com funcionalidades de agenda, gerenciamento de tarefas, busca de informações e suporte a estudos, o Jarvis visa facilitar a organização e o aprendizado dos usuários.

## Como executar o projeto:
Siga as instruções abaixo para rodar o projeto localmente, lembrando que é necessário ter o python e o Git instalados:

```bash
# 1. Clonar o repositório
$ git clone [https://github.com/seu-usuario/jarvis-academico.git](https://github.com/seu-usuario/jarvis-academico.git)

# 2. Entrar na pasta do projeto
$ cd jarvis-academico

# 3. Criar o ambiente virtual (venv)
$ python -m venv venv

# 4. Ativar o ambiente virtual
# No Windows:
$ venv\Scripts\activate
# No Linux ou macOS:
$ source venv/bin/activate

# 5. Instalar as dependências necessárias
$ pip install -r requirements.txt
```
🔑 Configurando as variáveis de ambiente: este projeto utiliza a API da OpenAI. Para que ele funcione, crie um arquivo chamado .env na raiz do projeto (onde está o requirements.txt) e adicione a sua chave de API:
```bash
GEMMA_BASE_URL=https://llm.liaufms.org/v1/gemma-3-12b-it
GEMMA_API_KEY=COLE SUA API KEY AQUI
```

Inicializando a aplicação: com o ambiente virtual ativado e a .env configurada, execute o comando abaixo para iniciar o Streamlit: 
```bash
$ streamlit run app.py
```

## Arquitetura do projeto (Modelo MVC):
```text
jarvis_academico/
│
├── data/                  # Pasta para o dataset com documentos de conteúdo acadêmico
├── vector_db/             # Pasta para armazenar os embeddings gerados localmente 
├── src/                   # Código-fonte principal
│   ├── app.py             # Interface do usuário (Streamlit) (View)
│   ├── database.py        # Interface com o banco de dados
│   ├── llm_client.py      # Interface com a LLM
│   ├── main_agent.py      # Lógica principal do agente (Controller)
│   ├── prompts.py         # Prompts utilizados na LLM
│   ├── rag_core.py        # Lógica de RAG
│   └── tools.py           # Ferramentas utilizadas pelo agente
├── jarvis_academico.bd    # Banco de dados SQLite para armazenamento de dados de agenda e tarefas
├── .env                   # Variáveis de ambiente
└── requirements.txt       # Dependências do projeto

```
### Tecnologias utilizadas

## Como funciona:
### Funcionalidades:
| Tool | Função |
| ---------- |  ---------------- |
| consultar_agenda  |  |
| listar_tarefas  |  |
| adicionar_tarefa   |  |
| concluir_tarefa   |  |
| buscar_material_rag  |  |
### Andamento do projeto - checklist: