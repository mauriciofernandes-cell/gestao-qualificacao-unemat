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

# 2. Estilização CSS personalizada
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
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #003366;
    }
</style>
""", unsafe_allow_html=True)

# 3. Inicialização e Ajuste do Banco de Dados SQLite
DB_NAME = "qualificacao_unemat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de servidores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT,
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
    
    # Usuários permitidos
    usuarios_padrao = [
        (1, 'controle', 'Supersdp@'),
        (2, 'sdp - controle', 'Supersdp@'),
        (3, 'sdp', 'Supersdp@'),
        (4, 'admin', '1234')
    ]
    for uid, u, s in usuarios_padrao:
        cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha) VALUES (?, ?, ?)", (uid, u, s))
        
    conn.commit()
    conn.close()

init_db()

# Função auxiliar para categorizar status de forma inteligente
def categorizar_status_inteligente(status_val):
    s = str(status_val).lower().strip()
    
    # Palavras-chave indicando Atraso / Pendência / Cobrança
    termos_atrasado = [
        'atrasad', 'pendent', 'cobranç', 'cobranc', 'notific', 'devedor', 
        'falta', 'devoluç', 'devoluc', 'sem relató', 'sem diploma', 'não entregou', 'nao entregou'
    ]
    
    # Palavras-chave indicando Concluído / Em dia
    termos_concluido = [
        'entregue', 'em dia', 'concluid', 'concluíd', 'finalizad', 'ok', 'deferid', 'regular', 'diploma entregue', 'certificado entregue'
    ]
    
    for kw in termos_atrasado:
        if kw in s:
            return 'Atrasado / Pendente'
            
    for kw in termos_concluido:
        if kw in s:
            return 'Em Dia / Concluído'
            
    return 'Outros / Em Acompanhamento'

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
            usuario_input = st.text_input("Matrícula / Usuário")
            senha_input = st.text_input("Senha de Acesso", type="password")
            btn_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_entrar:
                u_clean = usuario_input.strip().lower()
                s_clean = senha_input.strip()
                
                usuarios_validos_sdp = ["controle", "sdp - controle", "sdp - controle de qualificação.", "sdp", "sdpcontrole"]
                
                if (u_clean in usuarios_validos_sdp and s_clean == "Supersdp@") or (u_clean == "admin" and s_clean == "1234"):
                    st.session_state['logged_in'] = True
                    st.success("Acesso concedido com sucesso!")
                    st.rerun()
                else:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM usuarios WHERE LOWER(usuario)=? AND senha=?", (u_clean, s_clean))
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
    
    # ---------------- DASHBOARD ----------------
    if opcao == "Dashboard":
        st.subheader("📊 Painel Geral de Acompanhamento")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
                
            # Aplicação do algoritmo de categorização flexível
            df['Categoria_Status'] = df['status'].apply(categorizar_status_inteligente)
            
            total_servidores = len(df)
            total_em_dia = len(df[df['Categoria_Status'] == 'Em Dia / Concluído'])
            total_atrasados = len(df[df['Categoria_Status'] == 'Atrasado / Pendente'])
            total_outros = len(df[df['Categoria_Status'] == 'Outros / Em Acompanhamento'])
            
            # Exibição das Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Servidores", total_servidores)
            c2.metric("✅ Em Dia / Concluídos", total_em_dia)
            c3.metric("⚠️ Atrasados / Pendentes", total_atrasados)
            c4.metric("ℹ️ Outros / Acompanhamento", total_outros)
            
            st.divider()
            
            # Filtros e Pesquisa
            col_f1, col_f2 = st.columns([2, 2])
            with col_f1:
                filtro_categoria = st.radio(
                    "Filtrar Registros por Categoria:",
                    ["Exibir Todos", "⚠️ Atrasados e Pendentes", "✅ Em Dia e Concluídos", "ℹ️ Outros"],
                    horizontal=True
                )
            with col_f2:
                busca_texto = st.text_input("🔍 Pesquisar por Nome, Matrícula, Curso ou Status:", placeholder="Ex: Pendente, Devolução, Diploma...")
            
            # Filtragem dos dados
            df_exibicao = df.copy()
            
            if filtro_categoria == "⚠️ Atrasados e Pendentes":
                df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Atrasado / Pendente']
            elif filtro_categoria == "✅ Em Dia e Concluídos":
                df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Em Dia / Concluído']
            elif filtro_categoria == "ℹ️ Outros":
                df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Outros / Em Acompanhamento']
                
            if busca_texto:
                bt = busca_texto.lower()
                mask = (
                    df_exibicao['nome'].astype(str).str.lower().str.contains(bt) |
                    df_exibicao['matricula'].astype(str).str.lower().str.contains(bt) |
                    df_exibicao['curso'].astype(str).str.lower().str.contains(bt) |
                    df_exibicao['nivel'].astype(str).str.lower().str.contains(bt) |
                    df_exibicao['status'].astype(str).str.lower().str.contains(bt)
                )
                df_exibicao = df_exibicao[mask]
                
            st.write(f"Mostrando **{len(df_exibicao)}** registro(s):")
            st.dataframe(df_exibicao.drop(columns=['Categoria_Status']), use_container_width=True)
            
        else:
            st.info("Nenhum registro cadastrado no momento. Acesse '📥 Importar Planilha' no menu lateral para enviar seus dados.")

    # ---------------- IMPORTAR PLANILHA ----------------
    elif opcao == "📥 Importar Planilha":
        st.subheader("📥 Importar Dados de Planilha (Excel ou CSV)")
        st.write("Envie sua planilha para atualizar a base do sistema.")
        
        substituir_tudo = st.checkbox("⚠️ Substituir todos os registros existentes no banco de dados antes de importar", value=False)
        
        uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx) ou CSV (.csv)", type=["xlsx", "xls", "csv"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_import = pd.read_csv(uploaded_file)
                else:
                    df_import = pd.read_excel(uploaded_file)
                
                st.write("Prévia dos dados encontrados na planilha:")
                st.dataframe(df_import.head(10), use_container_width=True)
                
                st.info("Selecione qual coluna da sua planilha corresponde a cada campo do sistema:")
                
                colunas_disponiveis = list(df_import.columns)
                col_mat = st.selectbox("Coluna para Matrícula", colunas_disponiveis, index=0)
                col_nom = st.selectbox("Coluna para Nome Completo", colunas_disponiveis, index=min(1, len(colunas_disponiveis)-1))
                col_cur = st.selectbox("Coluna para Curso / Programa", colunas_disponiveis, index=min(2, len(colunas_disponiveis)-1))
                col_niv = st.selectbox("Coluna para Nível (Mestrado/Doutorado...)", colunas_disponiveis, index=min(3, len(colunas_disponiveis)-1))
                col_ini = st.selectbox("Coluna para Data Início", colunas_disponiveis, index=min(4, len(colunas_disponiveis)-1))
                col_fim = st.selectbox("Coluna para Previsão Término", colunas_disponiveis, index=min(5, len(colunas_disponiveis)-1))
                col_sta = st.selectbox("Coluna para Status / Observação", colunas_disponiveis, index=min(6, len(colunas_disponiveis)-1))
                
                if st.button("Confirmar e Importar Registros", type="primary"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    
                    if substituir_tudo:
                        cursor.execute("DELETE FROM servidores")
                    
                    sucesso = 0
                    
                    for _, row in df_import.iterrows():
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
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Importação concluída com sucesso! {sucesso} registro(s) inseridos.")
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")

    # ---------------- CADASTRAR NOVO SERVIDOR ----------------
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
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO servidores (matricula, nome, curso, nivel, data_inicio, data_previsao_termino, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (matricula, nome, curso, nivel, str(data_inicio), str(data_previsao), status))
                    conn.commit()
                    conn.close()
                    st.success("Servidor cadastrado com sucesso!")
                else:
                    st.warning("Por favor, preencha a matrícula e o nome.")

    # ---------------- GERENCIAR REGISTROS ----------------
    elif opcao == "📋 Gerenciar Registros":
        st.subheader("📋 Registros Cadastrados")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            st.dataframe(df, use_container_width=True)
            
            # Exportação de dados
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Registros em CSV",
                data=csv_data,
                file_name="servidores_afastados_unemat.csv",
                mime="text/csv"
            )
        else:
            st.info("Nenhum registro encontrado no sistema.")
