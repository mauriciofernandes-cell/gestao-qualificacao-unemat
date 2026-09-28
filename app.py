import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import os

# 1. Configuração da página
st.set_page_config(
    page_title="Gestão de Qualificação - UNEMAT",
    page_icon="🎓",
    layout="wide"
)

# 2. Estilização CSS personalizada com cores da UNEMAT
st.markdown("""
<style>
    .main-header { 
        font-size: 2.2rem; 
        font-weight: bold; 
        color: #003366; 
        text-align: center; 
        margin-bottom: 10px; 
    }
    .sub-header { 
        font-size: 1.3rem; 
        color: #555555; 
        text-align: center; 
        margin-bottom: 25px; 
    }
    .status-em-dia { 
        background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; 
    }
    .status-atrasado-relatorio { 
        background-color: #dc3545; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; 
    }
    .status-atrasado-diploma { 
        background-color: #fd7e14; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; 
    }
    .status-prorrogado { 
        background-color: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; 
    }
    .status-cobranca { 
        background-color: #6c757d; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; 
    }
</style>
""", unsafe_allow_html=True)

# 3. Inicialização e Correção de Esquema no Banco de Dados SQLite
DB_NAME = "qualificacao_unemat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de servidores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT UNIQUE,
            nome TEXT,
            curso TEXT,
            nivel TEXT,
            data_inicio DATE,
            data_previsao_termino DATE,
            status TEXT
        )
    ''')
    
    # Tabela de usuários com tratamento de erro de compatibilidade
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE,
                senha TEXT
            )
        ''')
        cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES ('admin', '1234')")
    except sqlite3.OperationalError:
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        cursor.execute('''
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE,
                senha TEXT
            )
        ''')
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES ('admin', '1234')")
        
    conn.commit()
    conn.close()

init_db()

# 4. Estado de sessão para controle de autenticação
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 5. Exibição da Logo da UNEMAT
logo_path = "image_f2383c.png"
if os.path.exists(logo_path):
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.image(logo_path, use_container_width=True)

# 6. Tela de Login
if not st.session_state['logged_in']:
    st.markdown("<div class='main-header'>Gestão de Qualificação</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Acesso Restrito - PRAD / SDP</div>", unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        with st.form("login_form"):
            usuario = st.text_input("Matrícula / Usuário")
            senha = st.text_input("Senha de Acesso", type="password")
            btn_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_entrar:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    st.session_state['logged_in'] = True
                    st.success("Acesso concedido com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# 7. Painel Principal (Após Login)
else:
    st.sidebar.title("Navegação")
    opcao = st.sidebar.radio("Selecione uma opção", ["Dashboard", "Cadastrar Servidor", "Gerenciar Registros"])
    
    if st.sidebar.button("Sair / Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.markdown("<div class='main-header'>Gestão de Afastamento para Qualificação</div>", unsafe_allow_html=True)
    
    if opcao == "Dashboard":
        st.subheader("Painel Geral de Acompanhamento")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Servidores", len(df))
            c2.metric("Em Dia", len(df[df['status'] == 'Em dia']))
            c3.metric("Atrasados", len(df[df['status'].str.contains('Atrasado', na=False)]))
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum registro cadastrado no momento.")

    elif opcao == "Cadastrar Servidor":
        st.subheader("Cadastrar Novo Servidor em Afastamento")
        with st.form("cadastrar_form"):
            matricula = st.text_input("Matrícula")
            nome = st.text_input("Nome Completo")
            curso = st.text_input("Curso / Programa")
            nivel = st.selectbox("Nível", ["Mestrado", "Doutorado", "Pós-Doutorado", "Especialização"])
            data_inicio = st.date_input("Data de Início", date.today())
            data_previsao = st.date_input("Previsão de Término", date.today())
            status = st.selectbox("Status Inicial", ["Em dia", "Atrasado Relatório", "Atrasado Diploma", "Prorrogado"])
            
            btn_salvar = st.form_submit_button("Salvar Cadastro")
            
            if btn_salvar:
                if matricula and nome:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO servidores (matricula, nome, curso, nivel, data_inicio, data_previsao_termino, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (matricula, nome, curso, nivel, data_inicio, data_previsao, status))
                        conn.commit()
                        conn.close()
                        st.success("Servidor cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Já existe um servidor com essa matrícula.")
                else:
                    st.warning("Por favor, preencha a matrícula e o nome.")

    elif opcao == "Gerenciar Registros":
        st.subheader("Registros Cadastrados")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum registro encontrado.")
