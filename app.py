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
</style>
""", unsafe_allow_html=True)

# 3. Inicialização do Banco de Dados SQLite
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
            data_inicio TEXT,
            data_previsao_termino TEXT,
            status TEXT
        )
    ''')
    
    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT
        )
    ''')
    
    # Cadastra as credenciais permitidas
    cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha) VALUES (1, 'admin', '1234')")
    cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha) VALUES (2, 'SDP - Controle de Qualificação.', 'Supersdp@')")
    cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha) VALUES (3, 'sdp', 'Supersdp@')")
        
    conn.commit()
    conn.close()

init_db()

# 4. Controle de sessão de login
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
    opcao = st.sidebar.radio(
        "Selecione uma opção", 
        ["Dashboard", "📥 Importar Planilha", "➕ Cadastrar Servidor", "📋 Gerenciar Registros"]
    )
    
    if st.sidebar.button("Sair / Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.markdown("<div class='main-header'>Gestão de Afastamento para Qualificação</div>", unsafe_allow_html=True)
    
    # DASHBOARD
    if opcao == "Dashboard":
        st.subheader("📊 Painel Geral de Acompanhamento")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT matricula, nome, curso, nivel, data_inicio, data_previsao_termino, status FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Servidores", len(df))
            c2.metric("Em Dia", len(df[df['status'].str.lower() == 'em dia']))
            c3.metric("Atrasados / Atenção", len(df[df['status'].str.contains('Atrasado|Cobrança', case=False, na=False)]))
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum registro cadastrado no momento. Use a opção '📥 Importar Planilha' no menu para carregar seus dados existentes.")

    # IMPORTAR PLANILHA
    elif opcao == "📥 Importar Planilha":
        st.subheader("📥 Importar Dados de Planilha (Excel ou CSV)")
        st.write("Faça o upload da sua planilha para carregar todos os registros anteriores de uma só vez.")
        
        uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx) ou CSV (.csv)", type=["xlsx", "xls", "csv"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_import = pd.read_csv(uploaded_file)
                else:
                    df_import = pd.read_excel(uploaded_file)
                
                st.write("Preview dos dados encontrados na planilha:")
                st.dataframe(df_import.head(10), use_container_width=True)
                
                st.info("Certifique-se de que sua planilha contenha as colunas correspondentes ou mapeie abaixo:")
                
                colunas_disponiveis = list(df_import.columns)
                col_mat = st.selectbox("Coluna para Matrícula", colunas_disponiveis, index=0)
                col_nom = st.selectbox("Coluna para Nome Completo", colunas_disponiveis, index=min(1, len(colunas_disponiveis)-1))
                col_cur = st.selectbox("Coluna para Curso", colunas_disponiveis, index=min(2, len(colunas_disponiveis)-1))
                col_niv = st.selectbox("Coluna para Nível", colunas_disponiveis, index=min(3, len(colunas_disponiveis)-1))
                col_ini = st.selectbox("Coluna para Data Início", colunas_disponiveis, index=min(4, len(colunas_disponiveis)-1))
                col_fim = st.selectbox("Coluna para Previsão Término", colunas_disponiveis, index=min(5, len(colunas_disponiveis)-1))
                col_sta = st.selectbox("Coluna para Status", colunas_disponiveis, index=min(6, len(colunas_disponiveis)-1))
                
                if st.button("Confirmar e Importar Registros para o Banco de Dados", type="primary"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    
                    sucesso = 0
                    duplicados = 0
                    
                    for _, row in df_import.iterrows():
                        try:
                            cursor.execute("""
                                INSERT INTO servidores (matricula, nome, curso, nivel, data_inicio, data_previsao_termino, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                str(row[col_mat]),
                                str(row[col_nom]),
                                str(row[col_cur]),
                                str(row[col_niv]),
                                str(row[col_ini]),
                                str(row[col_fim]),
                                str(row[col_sta])
                            ))
                            sucesso += 1
                        except sqlite3.IntegrityError:
                            duplicados += 1
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Importação concluída! {sucesso} registros inseridos com sucesso.")
                    if duplicados > 0:
                        st.warning(f"{duplicados} registros foram ignorados pois a matrícula já existia no sistema.")
            except Exception as e:
                st.error(f"Erro ao ler a planilha: {e}")

    # CADASTRAR NOVO SERVIDOR
    elif opcao == "➕ Cadastrar Servidor":
        st.subheader("➕ Cadastrar Novo Servidor em Afastamento")
        with st.form("cadastrar_form"):
            matricula = st.text_input("Matrícula")
            nome = st.text_input("Nome Completo")
            curso = st.text_input("Curso / Programa")
            nivel = st.selectbox("Nível", ["Mestrado", "Doutorado", "Pós-Doutorado", "Especialização"])
            data_inicio = st.date_input("Data de Início", date.today())
            data_previsao = st.date_input("Previsão de Término", date.today())
            status = st.selectbox("Status Inicial", ["Em dia", "Atrasado Relatório", "Atrasado Diploma", "Prorrogado"])
            
            btn_salvar = st.form_submit_button("Salvar Cadastro", use_container_width=True)
            
            if btn_salvar:
                if matricula and nome:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO servidores (matricula, nome, curso, nivel, data_inicio, data_previsao_termino, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (matricula, nome, curso, nivel, str(data_inicio), str(data_previsao), status))
                        conn.commit()
                        conn.close()
                        st.success("Servidor cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Já existe um servidor cadastrado com essa matrícula.")
                else:
                    st.warning("Por favor, preencha a matrícula e o nome.")

    # GERENCIAR REGISTROS
    elif opcao == "📋 Gerenciar Registros":
        st.subheader("📋 Registros Cadastrados")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT id, matricula, nome, curso, nivel, data_inicio, data_previsao_termino, status FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            # Botão de Exportação
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Registros em CSV",
                data=csv_data,
                file_name="servidores_afastados_unemat.csv",
                mime="text/csv"
            )
        else:
            st.info("Nenhum registro encontrado no sistema.")
