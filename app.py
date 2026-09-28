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

# 3. Inicialização e Ajuste Automático do Banco de Dados SQLite
DB_NAME = "qualificacao_unemat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de servidores unificada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT,
            nome TEXT,
            tipo_servidor TEXT DEFAULT 'Docente',
            curso TEXT,
            nivel TEXT,
            data_inicio TEXT,
            data_previsao_termino TEXT,
            status TEXT
        )
    ''')
    
    # Atualização de coluna tipo_servidor caso a tabela tenha sido criada em versão anterior
    cursor.execute("PRAGMA table_info(servidores)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    if 'tipo_servidor' not in colunas_existentes:
        cursor.execute("ALTER TABLE servidores ADD COLUMN tipo_servidor TEXT DEFAULT 'Docente'")
    
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

# Função de Inteligência para categorizar o Status dos Relatórios e Diplomas
def categorizar_status_inteligente(status_val):
    s = str(status_val).lower().strip()
    
    termos_atrasado = [
        'atrasad', 'pendent', 'cobranç', 'cobranc', 'notific', 'devedor', 
        'falta', 'devoluç', 'devoluc', 'sem relató', 'sem diploma', 'não entregou', 
        'nao entregou', 'suspens', 'processo de devolução', 'processo de devolucao'
    ]
    
    termos_concluido = [
        'entregue', 'em dia', 'concluid', 'concluíd', 'finalizad', 'ok', 
        'deferid', 'regular', 'diploma entregue', 'certificado entregue', 
        'relatórios entregues', 'relatorios entregues', 'relatório final entregue', 'relatorio final entregue'
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
        ["Dashboard Unificado", "📥 Importar Planilhas", "➕ Cadastrar Servidor", "📋 Gerenciar Registros"]
    )
    
    if st.sidebar.button("Sair / Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.markdown("<div class='main-header'>Gestão de Afastamento para Qualificação</div>", unsafe_allow_html=True)
    
    # ---------------- DASHBOARD UNIFICADO ----------------
    if opcao == "Dashboard Unificado":
        st.subheader("📊 Painel Geral de Acompanhamento (Docentes & Técnicos)")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
                
            # Aplicar categorização inteligente de status
            df['Categoria_Status'] = df['status'].apply(categorizar_status_inteligente)
            
            total_servidores = len(df)
            total_em_dia = len(df[df['Categoria_Status'] == 'Em Dia / Concluído'])
            df_atrasados = df[df['Categoria_Status'] == 'Atrasado / Pendente']
            total_atrasados = len(df_atrasados)
            
            # Subdivisão de atrasados por categoria de servidor
            docentes_atrasados = len(df_atrasados[df_atrasados['tipo_servidor'] == 'Docente'])
            tecnicos_atrasados = len(df_atrasados[df_atrasados['tipo_servidor'] == 'Técnico (PTES)'])
            
            # Métricas em Cartões
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Servidores", total_servidores)
            c2.metric("✅ Em Dia / Concluídos", total_em_dia)
            c3.metric("⚠️ Total de Atrasados", total_atrasados)
            c4.metric("👨‍🏫 Docentes / 👨‍💼 Técnicos Atrasados", f"{docentes_atrasados} / {tecnicos_atrasados}")
            
            st.divider()
            
            # Abas de Visualização
            aba1, aba2 = st.tabs(["🚨 RELATÓRIO DE ATRASADOS E PENDENTES", "🌐 VISÃO GERAL DE TODOS OS REGISTROS"])
            
            with aba1:
                st.warning(f"Exibindo **{len(df_atrasados)}** servidores com relatórios, diplomas ou processos pendentes/atrasados.")
                
                col_at_1, col_at_2 = st.columns([2, 2])
                with col_at_1:
                    filtro_tipo_atraso = st.selectbox("Filtrar por Tipo de Servidor:", ["Todos", "Docente", "Técnico (PTES)"])
                with col_at_2:
                    busca_atraso = st.text_input("🔍 Pesquisar em Atrasados:", placeholder="Nome, Matrícula ou Detalhe do Status...")
                
                df_atrasos_exibir = df_atrasados.copy()
                if filtro_tipo_atraso != "Todos":
                    df_atrasos_exibir = df_atrasos_exibir[df_atrasos_exibir['tipo_servidor'] == filtro_tipo_atraso]
                    
                if busca_atraso:
                    ba = busca_atraso.lower()
                    mask = (
                        df_atrasos_exibir['nome'].astype(str).str.lower().str.contains(ba) |
                        df_atrasos_exibir['matricula'].astype(str).str.lower().str.contains(ba) |
                        df_atrasos_exibir['curso'].astype(str).str.lower().str.contains(ba) |
                        df_atrasos_exibir['status'].astype(str).str.lower().str.contains(ba)
                    )
                    df_atrasos_exibir = df_atrasos_exibir[mask]
                
                st.dataframe(df_atrasos_exibir.drop(columns=['Categoria_Status']), use_container_width=True)
                
                # Botão para baixar relatório específico de atrasados
                csv_atrasados = df_atrasos_exibir.drop(columns=['Categoria_Status']).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Relatório de Atrasados em CSV/Excel",
                    data=csv_atrasados,
                    file_name="servidores_atrasados_unemat.csv",
                    mime="text/csv",
                    type="primary"
                )

            with aba2:
                col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
                with col_f1:
                    filtro_categoria = st.radio(
                        "Status:",
                        ["Exibir Todos", "⚠️ Atrasados/Pendentes", "✅ Em Dia/Concluídos"],
                        horizontal=True
                    )
                with col_f2:
                    filtro_tipo_geral = st.selectbox("Tipo de Servidor:", ["Todos", "Docente", "Técnico (PTES)"], key="f_tipo_geral")
                with col_f3:
                    busca_geral = st.text_input("🔍 Pesquisa Geral:", placeholder="Nome, Matrícula, Curso...", key="f_busca_geral")
                
                df_exibicao = df.copy()
                
                if filtro_categoria == "⚠️ Atrasados/Pendentes":
                    df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Atrasado / Pendente']
                elif filtro_categoria == "✅ Em Dia/Concluídos":
                    df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Em Dia / Concluído']
                    
                if filtro_tipo_geral != "Todos":
                    df_exibicao = df_exibicao[df_exibicao['tipo_servidor'] == filtro_tipo_geral]
                    
                if busca_geral:
                    bg = busca_geral.lower()
                    mask = (
                        df_exibicao['nome'].astype(str).str.lower().str.contains(bg) |
                        df_exibicao['matricula'].astype(str).str.lower().str.contains(bg) |
                        df_exibicao['curso'].astype(str).str.lower().str.contains(bg) |
                        df_exibicao['status'].astype(str).str.lower().str.contains(bg)
                    )
                    df_exibicao = df_exibicao[mask]
                    
                st.write(f"Mostrando **{len(df_exibicao)}** registro(s):")
                st.dataframe(df_exibicao.drop(columns=['Categoria_Status']), use_container_width=True)
            
        else:
            st.info("Nenhum registro cadastrado no momento. Acesse '📥 Importar Planilhas' para carregar seus dados de Docentes e Técnicos.")

    # ---------------- IMPORTAR PLANILHAS ----------------
    elif opcao == "📥 Importar Planilhas":
        st.subheader("📥 Importação e Unificação de Planilhas (Docentes & Técnicos)")
        st.write("Você pode importar a planilha de Docentes e depois a de Técnicos. O sistema unificará os dados automaticamente.")
        
        col_imp_1, col_imp_2 = st.columns([1, 1])
        with col_imp_1:
            tipo_planilha = st.selectbox("Selecione o Tipo dos Servidores desta Planilha:", ["Docente", "Técnico (PTES)"])
        with col_imp_2:
            modo_importacao = st.radio(
                "Ação de Importação:",
                ["➕ Adicionar e Unificar com a base existente", "⚠️ Limpar base e importar apenas esta planilha"],
                index=0
            )
            
        uploaded_file = st.file_uploader("Selecione a planilha Excel (.xlsx) ou CSV (.csv)", type=["xlsx", "xls", "csv"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_import = pd.read_csv(uploaded_file)
                else:
                    df_import = pd.read_excel(uploaded_file)
                
                st.write("Prévia dos dados da planilha selecionada:")
                st.dataframe(df_import.head(8), use_container_width=True)
                
                st.info("Confirme a correspondência das colunas:")
                colunas_disponiveis = list(df_import.columns)
                
                c_mat = st.selectbox("Matrícula", colunas_disponiveis, index=0)
                c_nom = st.selectbox("Nome Completo", colunas_disponiveis, index=min(1, len(colunas_disponiveis)-1))
                c_cur = st.selectbox("Curso / Programa", colunas_disponiveis, index=min(2, len(colunas_disponiveis)-1))
                c_niv = st.selectbox("Nível (Mestrado/Doutorado...)", colunas_disponiveis, index=min(3, len(colunas_disponiveis)-1))
                c_ini = st.selectbox("Data de Início", colunas_disponiveis, index=min(4, len(colunas_disponiveis)-1))
                c_fim = st.selectbox("Previsão de Término", colunas_disponiveis, index=min(5, len(colunas_disponiveis)-1))
                c_sta = st.selectbox("Status / Observação", colunas_disponiveis, index=min(6, len(colunas_disponiveis)-1))
                
                if st.button("Confirmar Importação e Unificar Registros", type="primary"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    
                    if "Limpar base" in modo_importacao:
                        cursor.execute("DELETE FROM servidores")
                        
                    sucesso = 0
                    for _, row in df_import.iterrows():
                        cursor.execute("""
                            INSERT INTO servidores (matricula, nome, tipo_servidor, curso, nivel, data_inicio, data_previsao_termino, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(row[c_mat]),
                            str(row[c_nom]),
                            tipo_planilha,
                            str(row[c_cur]),
                            str(row[c_niv]),
                            str(row[c_ini]),
                            str(row[c_fim]),
                            str(row[c_sta])
                        ))
                        sucesso += 1
                        
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Sucesso! {sucesso} registros do tipo **{tipo_planilha}** foram unificados ao banco de dados.")
            except Exception as e:
                st.error(f"Erro ao importar planilha: {e}")

    # ---------------- CADASTRAR NOVO SERVIDOR ----------------
    elif opcao == "➕ Cadastrar Servidor":
        st.subheader("➕ Cadastrar Novo Servidor em Afastamento")
        with st.form("cadastrar_form"):
            col_cad_1, col_cad_2 = st.columns(2)
            with col_cad_1:
                matricula = st.text_input("Matrícula")
                nome = st.text_input("Nome Completo")
                tipo_servidor = st.selectbox("Tipo de Servidor", ["Docente", "Técnico (PTES)"])
                curso = st.text_input("Curso / Programa")
            with col_cad_2:
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
                        INSERT INTO servidores (matricula, nome, tipo_servidor, curso, nivel, data_inicio, data_previsao_termino, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (matricula, nome, tipo_servidor, curso, nivel, str(data_inicio), str(data_previsao), status))
                    conn.commit()
                    conn.close()
                    st.success(f"Servidor **{nome}** ({tipo_servidor}) cadastrado com sucesso!")
                else:
                    st.warning("Por favor, preencha a matrícula e o nome.")

    # ---------------- GERENCIAR REGISTROS ----------------
    elif opcao == "📋 Gerenciar Registros":
        st.subheader("📋 Gerenciamento Unificado de Registros")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Base de Dados Completa (CSV)",
                data=csv_data,
                file_name="base_unificada_qualificacao_unemat.csv",
                mime="text/csv"
            )
        else:
            st.info("Nenhum registro encontrado no sistema.")
