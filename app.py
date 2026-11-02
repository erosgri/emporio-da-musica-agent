from __future__ import annotations

import logging

import streamlit as st

from emporio_agent.agent import AgentError, EmporioAgent
from emporio_agent.bootstrap import Application, build_application
from emporio_agent.config import get_settings

st.set_page_config(
    page_title="Empório da Música",
    page_icon="🎵",
    layout="centered",
)


@st.cache_resource(show_spinner="Preparando catálogo e políticas...")
def load_application() -> Application:
    return build_application()


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

st.title("🎵 Empório da Música")
st.caption("Sua música começa aqui.")

with st.sidebar:
    st.subheader("Configuração")
    supplied_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value="",
        help="Usada somente durante esta sessão. Prefira configurar OPENAI_API_KEY no .env.",
    )
    if st.button("Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown(
        "O assistente consulta o catálogo e o manual da loja. "
        "Ele não realiza compras, cancelamentos ou reembolsos."
    )

api_key = settings.openai_api_key or supplied_key.strip() or None
if not api_key:
    st.info("Configure `OPENAI_API_KEY` no arquivo `.env` ou informe a chave na barra lateral.")
    st.stop()

try:
    application = load_application()
    runtime_settings = application.settings.model_copy(update={"openai_api_key": api_key})
    agent = EmporioAgent(runtime_settings, application.tools)
except Exception:
    logging.exception("Falha ao inicializar a aplicação")
    st.error("Não foi possível preparar o catálogo e as políticas.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Olá! Eu sou o assistente da Empório da Música. "
            "Posso ajudar com instrumentos, pedidos e políticas da loja. Como posso ajudar?"
        )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Digite sua mensagem"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando..."):
            try:
                response = agent.chat(prompt, st.session_state.messages[:-1])
                answer = response.answer
            except AgentError as error:
                answer = str(error)
            except Exception:
                logging.exception("Falha durante atendimento")
                answer = "Tive um problema ao consultar os dados. Tente novamente em instantes."
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
