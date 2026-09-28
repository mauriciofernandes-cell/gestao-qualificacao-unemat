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
            tipo_servidor TEXT DEFAULT 'Docente',
            curso TEXT,
            nivel TEXT,
            data_inicio TEXT,
            data_previsao_termino TEXT,
            status TEXT
        )
    ''')
    
    # Garantir coluna tipo_servidor
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

# Função de Categorização de Status
def categorizar_status_inteligente(status_val):
    s = str(status_val).lower().strip()
    
    if status_val is None or pd.isna(status_val) or s in ['nan', 'none', '']:
        return 'Outros / Em Acompanhamento'
        
    # 1. PROCESSO DE DEVOLUÇÃO (Prioridade Máxima)
    termos_devolucao = [
        'devoluç', 'devoluc', 'cobranç', 'cobranc', 'processo de devolu', 
        'desconto', 'ressarcimento', 'restituição', 'restituicao', 'jurídic', 'juridic', 'tomada de conta'
    ]
    for kw in termos_devolucao:
        if kw in s:
            return 'Processo de Devolução'

    # 2. ATRASADOS / PENDENTES (Relatórios ou Diplomas)
    termos_atrasado = [
        'atrasad', 'pendent', 'notific', 'devedor', 'falta', 
        'sem relató', 'sem diploma', 'não entregou', 'nao entregou', 
        'suspens', 'prazo vencid', 'vencid'
    ]
    for kw in termos_atrasado:
        if kw in s:
            return 'Atrasado / Pendente'
            
    # 3. EM DIA / CONCLUÍDO
    termos_concluido = [
        'entregue', 'em dia', 'concluid', 'concluíd', 'finalizad', 'ok', 
        'deferid', 'regular', 'diploma entregue', 'certificado entregue', 
        'relatórios entregues', 'relatorios entregues', 'relatório final entregue', 'relatorio final entregue'
    ]
    for kw in termos_concluido:
        if kw in s:
            return 'Em Dia / Concluído'
            
    return 'Outros / Em Acompanhamento'

# Função para filtrar linhas inválidas / títulos no meio da planilha
def limpar_dataframe_importado(df):
    df_clean = df.dropna(how='all').copy()
    
    def linha_invalida(row):
        val_nome = str(row.get('nome', '')).strip().lower()
        val_mat = str(row.get('matricula', '')).strip().lower()
        
        # Se nome for 'nan', vazio ou palavras de cabeçalho da planilha
        if val_nome in ['nan', 'none', '', 'nome', 'nome completo', 'servidor']:
            return True
        if val_mat in ['nan', 'none', '', 'matrícula', 'matricula', 'relatório', 'relatorio']:
            if val_nome in ['nan', 'none', '']:
                return True
        return False

    indices_invalidos = [idx for idx, row in df_clean.iterrows() if linha_invalida(row)]
    df_clean = df_clean.drop(index=indices_invalidos).reset_index(drop=True)
    return df_clean

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
                
            # Limpeza automática de linhas residuais de nan do banco
            df = df[~df['nome'].astype(str).str.lower().isin(['nan', 'none', ''])]
            
            # Aplicar categorização de status
            df['Categoria_Status'] = df['status'].apply(categorizar_status_inteligente)
            
            total_servidores = len(df)
            total_em_dia = len(df[df['Categoria_Status'] == 'Em Dia / Concluído'])
            df_devolucao = df[df['Categoria_Status'] == 'Processo de Devolução']
            total_devolucao = len(df_devolucao)
            df_atrasados = df[df['Categoria_Status'] == 'Atrasado / Pendente']
            total_atrasados = len(df_atrasados)
            total_outros = len(df[df['Categoria_Status'] == 'Outros / Em Acompanhamento'])
            
            # Métricas em 4 Cartões
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Servidores", total_servidores)
            c2.metric("✅ Em Dia / Concluídos", total_em_dia)
            c3.metric("⚠️ Atrasados (Relatório/Diploma)", total_atrasados)
            c4.metric("🔴 Processo de Devolução", total_devolucao)
            
            st.divider()
            
            # Abas Exclusivas
            aba_dev, aba_atraso, aba_em_dia, aba_geral = st.tabs([
                "🔴 PROCESSO DE DEVOLUÇÃO", 
                "⚠️ ATRASADOS E PENDENTES", 
                "✅ EM DIA E CONCLUÍDOS", 
                "🌐 VISÃO GERAL DE TODOS OS REGISTROS"
            ])
            
            # TAB 1: PROCESSO DE DEVOLUÇÃO
            with aba_dev:
                st.error(f"Exibindo **{len(df_devolucao)}** servidores em **Processo de Devolução de Valores / Cobrança**.")
                if not df_devolucao.empty:
                    busca_dev = st.text_input("🔍 Pesquisar em Devolução:", placeholder="Nome, Matrícula, Curso...", key="b_dev")
                    df_dev_exibir = df_devolucao.copy()
                    if busca_dev:
                        bd = busca_dev.lower()
                        mask = (
                            df_dev_exibir['nome'].astype(str).str.lower().str.contains(bd) |
                            df_dev_exibir['matricula'].astype(str).str.lower().str.contains(bd) |
                            df_dev_exibir['curso'].astype(str).str.lower().str.contains(bd) |
                            df_dev_exibir['status'].astype(str).str.lower().str.contains(bd)
                        )
                        df_dev_exibir = df_dev_exibir[mask]
                    
                    st.dataframe(df_dev_exibir.drop(columns=['Categoria_Status']), use_container_width=True)
                    
                    csv_dev = df_dev_exibir.drop(columns=['Categoria_Status']).to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar Lista de Servidores em Processo de Devolução (CSV)",
                        data=csv_dev,
                        file_name="servidores_processo_devolucao_unemat.csv",
                        mime="text/csv",
                        type="primary"
                    )
                else:
                    st.success("Nenhum servidor em processo de devolução no momento.")

            # TAB 2: ATRASADOS E PENDENTES
            with aba_atraso:
                st.warning(f"Exibindo **{len(df_atrasados)}** servidores com relatórios ou diplomas **Atrasados / Pendentes**.")
                if not df_atrasados.empty:
                    busca_atr = st.text_input("🔍 Pesquisar em Atrasados:", placeholder="Nome, Matrícula, Curso...", key="b_atr")
                    df_atr_exibir = df_atrasados.copy()
                    if busca_atr:
                        ba = busca_atr.lower()
                        mask = (
                            df_atr_exibir['nome'].astype(str).str.lower().str.contains(ba) |
                            df_atr_exibir['matricula'].astype(str).str.lower().str.contains(ba) |
                            df_atr_exibir['curso'].astype(str).str.lower().str.contains(ba) |
                            df_atr_exibir['status'].astype(str).str.lower().str.contains(ba)
                        )
                        df_atr_exibir = df_atr_exibir[mask]
                        
                    st.dataframe(df_atr_exibir.drop(columns=['Categoria_Status']), use_container_width=True)
                    
                    csv_atr = df_atr_exibir.drop(columns=['Categoria_Status']).to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar Lista de Atrasados e Pendentes (CSV)",
                        data=csv_atr,
                        file_name="servidores_atrasados_relatorios_unemat.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("Nenhum servidor com relatório ou diploma atrasado.")

            # TAB 3: EM DIA E CONCLUÍDOS
            with aba_em_dia:
                df_em_dia = df[df['Categoria_Status'] == 'Em Dia / Concluído']
                st.info(f"Exibindo **{len(df_em_dia)}** servidores **Em Dia / Concluídos**.")
                st.dataframe(df_em_dia.drop(columns=['Categoria_Status']), use_container_width=True)

            # TAB 4: VISÃO GERAL
            with aba_geral:
                col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
                with col_f1:
                    filtro_cat = st.selectbox(
                        "Filtrar por Categoria:",
                        ["Todos", "🔴 Processo de Devolução", "⚠️ Atrasados/Pendentes", "✅ Em Dia/Concluídos", "ℹ️ Outros"]
                    )
                with col_f2:
                    filtro_tipo = st.selectbox("Tipo de Servidor:", ["Todos", "Docente", "Técnico (PTES)"], key="f_tipo_g")
                with col_f3:
                    busca_g = st.text_input("🔍 Pesquisa Geral:", placeholder="Nome, Matrícula, Curso...", key="f_busca_g")
                
                df_exibicao = df.copy()
                
                if filtro_cat == "🔴 Processo de Devolução":
                    df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Processo de Devolução']
                elif filtro_cat == "⚠️ Atrasados/Pendentes":
                    df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Atrasado / Pendente']
                elif filtro_cat == "✅ Em Dia/Concluídos":
                    df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Em Dia / Concluído']
                elif filtro_cat == "ℹ️ Outros":
                    df_exibicao = df_exibicao[df_exibicao['Categoria_Status'] == 'Outros / Em Acompanhamento']
                    
                if filtro_tipo != "Todos":
                    df_exibicao = df_exibicao[df_exibicao['tipo_servidor'] == filtro_tipo]
                    
                if busca_g:
                    bg = busca_g.lower()
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
            st.info("Nenhum registro encontrado. Acesse '📥 Importar Planilhas' para carregar as 4 planilhas enviadas.")

    # ---------------- IMPORTAR PLANILHAS ----------------
    elif opcao == "📥 Importar Planilhas":
        st.subheader("📥 Importar e Unificar as 4 Planilhas de uma só vez")
        st.write("Você pode selecionar e enviar **as 4 planilhas simultaneamente** (.xlsx ou .csv). O sistema fará a limpeza automática das linhas inválidas.")
        
        limpar_base = st.checkbox("⚠️ Limpar banco de dados atual antes de importar as novas planilhas", value=True)
        
        uploaded_files = st.file_uploader(
            "Selecione uma ou até as 4 planilhas (.xlsx, .xls, .csv)", 
            type=["xlsx", "xls", "csv"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"**{len(uploaded_files)}** arquivo(s) selecionado(s).")
            
            if st.button("Confirmar e Importar Todos os Arquivos", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                if limpar_base:
                    cursor.execute("DELETE FROM servidores")
                
                total_importado = 0
                
                for f in uploaded_files:
                    try:
                        if f.name.endswith('.csv'):
                            dict_dfs = {"Sheet1": pd.read_csv(f)}
                        else:
                            dict_dfs = pd.read_excel(f, sheet_name=None)
                            
                        # Determinar tipo de servidor pelo nome do arquivo
                        nome_f = f.name.lower()
                        tipo_s = "Técnico (PTES)" if ("tecnico" in nome_f or "ptes" in nome_f) else "Docente"
                        
                        for sheet_name, df_sheet in dict_dfs.items():
                            if df_sheet.empty:
                                continue
                                
                            # Identificação flexível de colunas
                            cols = {str(c).lower().strip(): c for c in df_sheet.columns}
                            
                            c_mat = next((cols[k] for k in cols if 'mat' in k), df_sheet.columns[0])
                            c_nom = next((cols[k] for k in cols if 'nome' in k or 'servidor' in k), df_sheet.columns[min(1, len(df_sheet.columns)-1)])
                            c_cur = next((cols[k] for k in cols if 'curso' in k or 'programa' in k), df_sheet.columns[min(2, len(df_sheet.columns)-1)])
                            c_niv = next((cols[k] for k in cols if 'nivel' in k or 'nível' in k), df_sheet.columns[min(3, len(df_sheet.columns)-1)])
                            c_ini = next((cols[k] for k in cols if 'inicio' in k or 'início' in k or 'afast' in k), df_sheet.columns[min(4, len(df_sheet.columns)-1)])
                            c_fim = next((cols[k] for k in cols if 'termino' in k or 'término' in k or 'previs' in k), df_sheet.columns[min(5, len(df_sheet.columns)-1)])
                            c_sta = next((cols[k] for k in cols if 'status' in k or 'situac' in k or 'situaç' in k or 'obs' in k), df_sheet.columns[min(6, len(df_sheet.columns)-1)])
                            
                            df_temp = pd.DataFrame({
                                'matricula': df_sheet[c_mat].astype(str),
                                'nome': df_sheet[c_nom].astype(str),
                                'curso': df_sheet[c_cur].astype(str),
                                'nivel': df_sheet[c_niv].astype(str),
                                'data_inicio': df_sheet[c_ini].astype(str),
                                'data_previsao_termino': df_sheet[c_fim].astype(str),
                                'status': df_sheet[c_sta].astype(str)
                            })
                            
                            # Limpeza de linhas NaNs/cabeçalho
                            df_limpo = limpar_dataframe_importado(df_temp)
                            
                            for _, row in df_limpo.iterrows():
                                cursor.execute("""
                                    INSERT INTO servidores (matricula, nome, tipo_servidor, curso, nivel, data_inicio, data_previsao_termino, status)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    str(row['matricula']),
                                    str(row['nome']),
                                    tipo_s,
                                    str(row['curso']),
                                    str(row['nivel']),
                                    str(row['data_inicio']),
                                    str(row['data_previsao_termino']),
                                    str(row['status'])
                                ))
                                total_importado += 1
                    except Exception as ex:
                        st.error(f"Erro ao ler o arquivo {f.name}: {ex}")
                
                conn.commit()
                conn.close()
                st.success(f"Importação concluída! **{total_importado}** registros válidos foram carregados e unificados com sucesso.")
                st.rerun()

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
                status = st.selectbox("Status Inicial", ["Em dia", "Atrasado Relatório", "Atrasado Diploma", "PROCESSO DE DEVOLUÇÃO", "Prorrogado"])
            
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
            # Limpeza de NaNs
            df = df[~df['nome'].astype(str).str.lower().isin(['nan', 'none', ''])]
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
