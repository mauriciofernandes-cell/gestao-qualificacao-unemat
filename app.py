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

def init_db(force_recreate=False):
    conn = sqlite3.connect(DB_NAME, timeout=20)
    cursor = conn.cursor()
    
    if force_recreate:
        cursor.execute("DROP TABLE IF EXISTS servidores")
        cursor.execute("DROP TABLE IF EXISTS usuarios")
    
    cursor.execute("""
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
    """)
    
    try:
        cursor.execute("SELECT id, usuario, senha FROM usuarios LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("DROP TABLE IF EXISTS usuarios")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT
        )
    """)
    
    usuarios_padrao = [
        (1, 'controle', 'Supersdp@'),
        (2, 'sdp - controle', 'Supersdp@'),
        (3, 'sdp - controle de qualificação.', 'Supersdp@'),
        (4, 'sdp', 'Supersdp@'),
        (5, 'admin', '1234')
    ]
    for uid, u, s in usuarios_padrao:
        cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha) VALUES (?, ?, ?)", (uid, u, s))
        
    conn.commit()
    conn.close()

init_db()

# Categorização inteligente de status
def categorizar_status_inteligente(status_val):
    s = str(status_val).lower().strip()
    if status_val is None or pd.isna(status_val) or s in ['nan', 'none', '']:
        return 'Outros / Em Acompanhamento'
        
    termos_devolucao = [
        'devoluç', 'devoluc', 'cobranç', 'cobranc', 'processo de devolu', 
        'desconto', 'ressarcimento', 'restituição', 'restituicao', 'jurídic', 'juridic', 'tomada de conta'
    ]
    for kw in termos_devolucao:
        if kw in s:
            return 'Processo de Devolução'

    termos_atrasado = [
        'atrasad', 'pendent', 'notific', 'devedor', 'falta', 
        'sem relató', 'sem diploma', 'não entregou', 'nao entregou', 
        'suspens', 'prazo vencid', 'vencid'
    ]
    for kw in termos_atrasado:
        if kw in s:
            return 'Atrasado / Pendente'
            
    termos_concluido = [
        'entregue', 'em dia', 'concluid', 'concluíd', 'finalizad', 'ok', 
        'deferid', 'regular', 'diploma entregue', 'certificado entregue', 
        'relatórios entregues', 'relatorios entregues', 'relatório final entregue', 'relatorio final entregue'
    ]
    for kw in termos_concluido:
        if kw in s:
            return 'Em Dia / Concluído'
            
    return 'Outros / Em Acompanhamento'

# Função para leitura inteligente de CSV (suporta ponto e vírgula de planilhas brasileiras) ou Excel
def ler_arquivo_upload(uploaded_file):
    fname = uploaded_file.name.lower()
    dict_sheets = {}
    
    if fname.endswith('.csv'):
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8-sig')
        except Exception:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding='latin1')
            except Exception:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=',', encoding='latin1')
        dict_sheets['Planilha1'] = df
    else:
        dict_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        
    return dict_sheets

# Função para localizar a linha de cabeçalho real na planilha
def localizar_cabecalho_e_dados(df_raw):
    header_idx = 0
    found_header = False
    
    keywords = ['nome', 'servidor', 'docente', 'tecnico', 'técnico', 'interessado', 'matr', 'mat', 'curso', 'programa', 'status', 'situaç', 'situac', 'nivel', 'nível', 'inicio', 'início', 'termino', 'término', 'previs']
    
    cols_str = " ".join([str(c).lower() for c in df_raw.columns])
    if sum(1 for k in keywords if k in cols_str) >= 2:
        found_header = True
        df_data = df_raw.copy()
    else:
        for idx in range(min(15, len(df_raw))):
            row_vals = [str(v).lower().strip() for v in df_raw.iloc[idx].values if pd.notna(v)]
            matches = sum(1 for k in keywords if any(k in cell for cell in row_vals))
            if matches >= 2:
                header_idx = idx
                found_header = True
                break
                
        if found_header and header_idx >= 0:
            new_cols = [str(val).strip() if (pd.notna(val) and str(val).strip() != '') else f"col_{i}" for i, val in enumerate(df_raw.iloc[header_idx].values)]
            df_data = df_raw.iloc[header_idx + 1:].copy()
            df_data.columns = new_cols
        else:
            df_data = df_raw.copy()
            
    return df_data

# 4. Controle de sessão de login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 5. Logotipo UNEMAT
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
                    conn = sqlite3.connect(DB_NAME, timeout=20)
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

# 7. Painel Principal
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
        conn = sqlite3.connect(DB_NAME, timeout=20)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
                
            df = df[~df['nome'].astype(str).str.lower().isin(['nan', 'none', '', 'null'])]
            df['Categoria_Status'] = df['status'].apply(categorizar_status_inteligente)
            
            total_servidores = len(df)
            total_em_dia = len(df[df['Categoria_Status'] == 'Em Dia / Concluído'])
            df_devolucao = df[df['Categoria_Status'] == 'Processo de Devolução']
            total_devolucao = len(df_devolucao)
            df_atrasados = df[df['Categoria_Status'] == 'Atrasado / Pendente']
            total_atrasados = len(df_atrasados)
            total_outros = len(df[df['Categoria_Status'] == 'Outros / Em Acompanhamento'])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Servidores", total_servidores)
            c2.metric("✅ Em Dia / Concluídos", total_em_dia)
            c3.metric("⚠️ Atrasados (Relatório/Diploma)", total_atrasados)
            c4.metric("🔴 Processo de Devolução", total_devolucao)
            
            st.divider()
            
            aba_dev, aba_atraso, aba_em_dia, aba_geral = st.tabs([
                "🔴 PROCESSO DE DEVOLUÇÃO", 
                "⚠️ ATRASADOS E PENDENTES", 
                "✅ EM DIA E CONCLUÍDOS", 
                "🌐 VISÃO GERAL DE TODOS OS REGISTROS"
            ])
            
            with aba_dev:
                st.error(f"Exibindo **{len(df_devolucao)}** servidores em **Processo de Devolução / Cobrança de Valores**.")
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

            with aba_em_dia:
                df_em_dia = df[df['Categoria_Status'] == 'Em Dia / Concluído']
                st.info(f"Exibindo **{len(df_em_dia)}** servidores **Em Dia / Concluídos**.")
                st.dataframe(df_em_dia.drop(columns=['Categoria_Status']), use_container_width=True)

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
            st.info("Nenhum registro encontrado no banco de dados. Acesse '📥 Importar Planilhas' para carregar os dados.")

    # ---------------- IMPORTAR PLANILHAS ----------------
    elif opcao == "📥 Importar Planilhas":
        st.subheader("📥 Importação da Planilha Unificada")
        st.write("Selecione a sua planilha (.xlsx, .xls ou .csv). O sistema mostrará as colunas identificadas para você confirmar.")
        
        limpar_base = st.checkbox("⚠️ Recriar banco de dados e apagar registros anteriores antes de importar", value=True)
        
        uploaded_files = st.file_uploader(
            "Selecione o arquivo da planilha (.xlsx, .xls, .csv)", 
            type=["xlsx", "xls", "csv"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"**{len(uploaded_files)}** arquivo(s) selecionado(s).")
            
            for file_idx, f in enumerate(uploaded_files):
                st.markdown(f"### 📄 Arquivo: `{f.name}`")
                
                dict_sheets = ler_arquivo_upload(f)
                
                for sheet_name, df_raw in dict_sheets.items():
                    if df_raw is None or df_raw.empty:
                        continue
                        
                    st.markdown(f"#### Aba: **{sheet_name}** ({len(df_raw)} linhas brutas)")
                    
                    df_data = localizar_cabecalho_e_dados(df_raw)
                    col_options = [str(c) for c in df_data.columns]
                    cols_lower = [str(c).lower().strip() for c in col_options]
                    
                    # Sugestões automáticas de mapeamento
                    def sugerir_col(keywords, default_idx):
                        for kw in keywords:
                            for idx, col_l in enumerate(cols_lower):
                                if kw in col_l:
                                    return col_options[idx]
                        return col_options[min(default_idx, len(col_options)-1)]
                    
                    idx_mat = col_options.index(sugerir_col(['matr', 'mat'], 0))
                    idx_nom = col_options.index(sugerir_col(['nome', 'servidor', 'docente', 'tecnico', 'interessado', 'pess'], min(1, len(col_options)-1)))
                    idx_cur = col_options.index(sugerir_col(['curso', 'programa', 'área', 'area'], min(2, len(col_options)-1)))
                    idx_niv = col_options.index(sugerir_col(['nivel', 'nível', 'grau', 'titul'], min(3, len(col_options)-1)))
                    idx_ini = col_options.index(sugerir_col(['inicio', 'início', 'afast', 'saida'], min(4, len(col_options)-1)))
                    idx_fim = col_options.index(sugerir_col(['termino', 'término', 'previs', 'retorno'], min(5, len(col_options)-1)))
                    idx_sta = col_options.index(sugerir_col(['status', 'situac', 'situaç', 'obs', 'parecer'], min(6, len(col_options)-1)))
                    
                    st.write("Confirme ou ajuste o mapeamento das colunas da sua planilha:")
                    
                    mc1, mc2, mc3 = st.columns(3)
                    with mc1:
                        sel_mat = st.selectbox("Matrícula:", col_options, index=idx_mat, key=f"mat_{file_idx}_{sheet_name}")
                        sel_nom = st.selectbox("Nome Completo:", col_options, index=idx_nom, key=f"nom_{file_idx}_{sheet_name}")
                        sel_cur = st.selectbox("Curso / Programa:", col_options, index=idx_cur, key=f"cur_{file_idx}_{sheet_name}")
                    with mc2:
                        sel_niv = st.selectbox("Nível (Mestrado/Doutorado):", col_options, index=idx_niv, key=f"niv_{file_idx}_{sheet_name}")
                        sel_ini = st.selectbox("Data de Início:", col_options, index=idx_ini, key=f"ini_{file_idx}_{sheet_name}")
                        sel_fim = st.selectbox("Previsão de Término:", col_options, index=idx_fim, key=f"fim_{file_idx}_{sheet_name}")
                    with mc3:
                        sel_sta = st.selectbox("Status / Situação / Obs:", col_options, index=idx_sta, key=f"sta_{file_idx}_{sheet_name}")
                        
                        fname_lower = f.name.lower()
                        default_tipo = "Técnico (PTES)" if ("tecnico" in fname_lower or "ptes" in fname_lower) else "Docente"
                        sel_tipo = st.selectbox("Tipo de Servidor:", ["Docente", "Técnico (PTES)"], index=0 if default_tipo=="Docente" else 1, key=f"tip_{file_idx}_{sheet_name}")
                    
                    # Gerar pré-visualização extraída
                    df_preview = pd.DataFrame({
                        'matricula': df_data[sel_mat].astype(str).str.strip(),
                        'nome': df_data[sel_nom].astype(str).str.strip(),
                        'tipo_servidor': sel_tipo,
                        'curso': df_data[sel_cur].astype(str).str.strip(),
                        'nivel': df_data[sel_niv].astype(str).str.strip(),
                        'data_inicio': df_data[sel_ini].astype(str).str.strip(),
                        'data_previsao_termino': df_data[sel_fim].astype(str).str.strip(),
                        'status': df_data[sel_sta].astype(str).str.strip()
                    })
                    
                    # Remover linhas em branco / títulos residuais
                    df_preview = df_preview[~df_preview['nome'].str.lower().isin(['nan', 'none', '', 'null', 'nome', 'nome completo', 'servidor', 'nome do servidor'])]
                    
                    st.info(f"👁️ **Pré-visualização:** {len(df_preview)} registros válidos encontrados nesta aba:")
                    st.dataframe(df_preview.head(10), use_container_width=True)
                    
                    if st.button(f"🚀 Importar {len(df_preview)} Registros para o Banco de Dados", type="primary", key=f"btn_imp_{file_idx}_{sheet_name}"):
                        init_db(force_recreate=limpar_base)
                        
                        conn = sqlite3.connect(DB_NAME, timeout=20)
                        cursor = conn.cursor()
                        
                        inserted_count = 0
                        for _, row in df_preview.iterrows():
                            cursor.execute("""
                                INSERT INTO servidores (matricula, nome, tipo_servidor, curso, nivel, data_inicio, data_previsao_termino, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                str(row['matricula']),
                                str(row['nome']),
                                str(row['tipo_servidor']),
                                str(row['curso']),
                                str(row['nivel']),
                                str(row['data_inicio']),
                                str(row['data_previsao_termino']),
                                str(row['status'])
                            ))
                            inserted_count += 1
                            
                        conn.commit()
                        conn.close()
                        
                        st.success(f"🎉 Importação efetuada com sucesso! **{inserted_count}** servidores gravados no banco de dados!")
                        st.info("Redirecionando para o Dashboard...")
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
                    conn = sqlite3.connect(DB_NAME, timeout=20)
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
        conn = sqlite3.connect(DB_NAME, timeout=20)
        df = pd.read_sql_query("SELECT * FROM servidores", conn)
        conn.close()
        
        if not df.empty:
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            df = df[~df['nome'].astype(str).str.lower().isin(['nan', 'none', '', 'null'])]
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
