import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import os

# Configuração da página
st.set_page_config(
    page_title="Gestão de Qualificação - UNEMAT",
    page_icon="🎓",
    layout="wide"
)

# Estilização CSS personalizada com cores da UNEMAT
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; color: #00274c; }
    .status-em-dia { background-color: #2e7d32; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-atrasado-relat { background-color: #ef6c00; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-atrasado-diploma { background-color: #c62828; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-prorrogado { background-color: #fbc02d; color: black; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .status-cobranca { background-color: #b71c1c; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Inicialização e Conexão do Banco de Dados SQLite
DB_NAME = "qualificacao_unemat.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabela de Usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            matricula TEXT PRIMARY KEY,
            senha TEXT NOT NULL,
            nome TEXT NOT NULL,
            perfil TEXT DEFAULT 'operador'
        )
    ''')
    # Usuário Padrão Admin (SDP)
    c.execute('''
        INSERT OR IGNORE INTO usuarios (matricula, senha, nome, perfil)
        VALUES ('SDP - Controle de Qualificação', 'Supersdp@', 'SDP Admin', 'admin')
    ''')
    
    # Tabela de Servidores Afastados
    c.execute('''
        CREATE TABLE IF NOT EXISTS servidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            matricula TEXT NOT NULL,
            protocolo TEXT,
            nivel TEXT,
            data_inicio DATE,
            data_fim DATE,
            relatorios_entregues INTEGER DEFAULT 0,
            email TEXT,
            pasta TEXT,
            status TEXT,
            prorrogado TEXT DEFAULT 'Não',
            cobrado TEXT DEFAULT 'Não',
            data_cobranca DATE,
            resposta_servidor TEXT,
            processo_cobranca TEXT,
            observacoes TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Lógica de Autenticação
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["usuario"] = None
    st.session_state["perfil"] = None

def login():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("image_f2383c.png", width=280) if os.path.exists("image_f2383c.png") else None
        st.markdown("<h2 style='text-align: center; color: #00274c;'>Gestão de Qualificação</h2>", unsafe_allow_html=True)
        st.subheader("Acesso Restrito - PRAD / SDP")
        
        matricula_input = st.text_input("Matrícula / Usuário")
        senha_input = st.text_input("Senha de Acesso", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT matricula, nome, perfil FROM usuarios WHERE matricula=? AND senha=?", (matricula_input, senha_input))
            user = c.fetchone()
            conn.close()
            
            if user:
                st.session_state["logged_in"] = True
                st.session_state["usuario"] = user[1]
                st.session_state["perfil"] = user[2]
                st.success("Acesso autorizado!")
                st.rerun()
            else:
                st.error("Matrícula ou senha incorretos.")

if not st.session_state["logged_in"]:
    login()
    st.stop()

# Layout Principal da Aplicação
st.sidebar.image("image_f2383c.png", use_column_width=True) if os.path.exists("image_f2383c.png") else None
st.sidebar.title("Navegação")
st.sidebar.write(f"**Usuário:** {st.session_state['usuario']}")

menu = st.sidebar.radio("Selecione o Módulo", [
    "Painel de Acompanhamento",
    "Cadastrar / Editar Servidor",
    "Gestão de Cobranças",
    "Cadastrar Usuários (Admin)",
    "Sair"
])

if menu == "Sair":
    st.session_state["logged_in"] = False
    st.rerun()

# Função para calcular Status Automático de acordo com IN 001/2018
def calcular_status_sugerido(data_inicio, data_fim, relatorios_entregues, cobrado):
    hoje = date.today()
    if not data_inicio or not data_fim:
        return "Em Dia"
    
    # Calcular semestres transcorridos
    meses_decorridos = (hoje.year - data_inicio.year) * 12 + (hoje.month - data_inicio.month)
    semestres_esperados = max(1, meses_decorridos // 6)
    
    if cobrado == "Sim":
        return "Em Cobrança / Processo"
    
    # Verifica atraso no diploma (1 ano após data_fim)
    if hoje > data_fim:
        dias_pos_fim = (hoje - data_fim).days
        if dias_pos_fim > 365:
            return "Atrasado com Diploma"
    
    # Verifica relatório semestral
    if relatorios_entregues < semestres_esperados and hoje <= data_fim:
        return "Atrasado com Relatório Semestral"
        
    return "Em Dia"

# MÓDULO 1: PAINEL DE ACOMPANHAMENTO
if menu == "Painel de Acompanhamento":
    st.markdown("<h2 class='main-header'>Acompanhamento Semestral de Qualificação - UNEMAT</h2>", unsafe_allow_html=True)
    
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM servidores", conn)
    conn.close()
    
    # Filtros por Período e Status
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_status = st.multiselect("Filtrar por Status", options=df["status"].unique() if not df.empty else [], default=[])
    with col_f2:
        dt_inicio_filtro = st.date_input("Início do Afastamento a partir de", value=date(2018, 1, 1))
    with col_f3:
        dt_fim_filtro = st.date_input("Fim do Afastamento até", value=date(2030, 12, 31))
        
    if not df.empty:
        df['data_inicio'] = pd.to_datetime(df['data_inicio']).dt.date
        df['data_fim'] = pd.to_datetime(df['data_fim']).dt.date
        
        # Aplicação dos Filtros
        df_filtered = df[(df['data_inicio'] >= dt_inicio_filtro) & (df['data_fim'] <= dt_fim_filtro)]
        if filtro_status:
            df_filtered = df_filtered[df_filtered['status'].isin(filtro_status)]
            
        # Indicadores Sintéticos
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total de Servidores", len(df_filtered))
        c2.metric("Em Dia", len(df_filtered[df_filtered['status'] == "Em Dia"]))
        c3.metric("Atrasados (Relatório)", len(df_filtered[df_filtered['status'] == "Atrasado com Relatório Semestral"]))
        c4.metric("Atrasados (Diploma)", len(df_filtered[df_filtered['status'] == "Atrasado com Diploma"]))
        c5.metric("Em Cobrança", len(df_filtered[df_filtered['status'] == "Em Cobrança / Processo"]))
        
        st.markdown("---")
        
        # Função para destacar linhas com cores
        def color_status(val):
            if val == 'Em Dia' or val == 'Finalizado':
                return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif val == 'Atrasado com Relatório Semestral':
                return 'background-color: #ffeba2; color: #856404; font-weight: bold;'
            elif val == 'Atrasado com Diploma':
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            elif val == 'Prorrogado':
                return 'background-color: #e2e3e5; color: #383d41; font-weight: bold;'
            elif val == 'Em Cobrança / Processo':
                return 'background-color: #f5c6cb; color: #721c24; font-weight: bold;'
            return ''

        styled_df = df_filtered.style.map(color_status, subset=['status'])
        st.dataframe(styled_df, use_container_width=True)
        
        # Exportar relatório
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("Baixar Planilha Filtrada (CSV)", data=csv, file_name="relatorio_qualificacao_unemat.csv", mime="text/csv")
    else:
        st.info("Nenhum registro encontrado no banco de dados.")

# MÓDULO 2: CADASTRAR / EDITAR SERVIDOR
elif menu == "Cadastrar / Editar Servidor":
    st.subheader("Cadastro e Atualização de Servidor Afastado")
    
    conn = get_connection()
    df_serv = pd.read_sql_query("SELECT id, nome, matricula FROM servidores", conn)
    
    opcao_acao = st.radio("Ação", ["Novo Cadastro", "Editar Cadastro Existente"])
    
    servidor_edit = None
    if opcao_acao == "Editar Cadastro Existente" and not df_serv.empty:
        servidor_sel = st.selectbox("Selecione o Servidor", df_serv["id"].astype(str) + " - " + df_serv["nome"] + " (" + df_serv["matricula"] + ")")
        serv_id = int(servidor_sel.split(" - ")[0])
        servidor_edit = pd.read_sql_query("SELECT * FROM servidores WHERE id=?", conn, params=(serv_id,)).iloc[0]

    with st.form("form_servidor"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("NOME COMPLETO", value=servidor_edit["nome"] if servidor_edit is not None else "")
            matricula = st.text_input("MATRÍCULA", value=servidor_edit["matricula"] if servidor_edit is not None else "")
            protocolo = st.text_input("PROTOCOLO / PROCESSO", value=servidor_edit["protocolo"] if servidor_edit is not None else "")
            nivel = st.selectbox("NÍVEL", ["MESTRADO", "DOUTORADO", "PÓS-DOUTORADO", "ESPECIALIZAÇÃO"], index=0)
            email = st.text_input("ENDEREÇO ELETRÔNICO (E-mail)", value=servidor_edit["email"] if servidor_edit is not None else "")
            pasta = st.text_input("PASTA / LOCALIZAÇÃO FISCAL", value=servidor_edit["pasta"] if servidor_edit is not None else "ARQUIVO PESSOAL")

        with col2:
            dt_inc = pd.to_datetime(servidor_edit["data_inicio"]).date() if servidor_edit is not None and servidor_edit["data_inicio"] else date.today()
            dt_fim = pd.to_datetime(servidor_edit["data_fim"]).date() if servidor_edit is not None and servidor_edit["data_fim"] else date.today()
            
            data_inicio = st.date_input("DATA INÍCIO DO AFASTAMENTO", value=dt_inc)
            data_fim = st.date_input("DATA FIM DO AFASTAMENTO", value=dt_fim)
            relat_entregues = st.number_input("NÚMERO DE RELATÓRIOS ENTREGUES", min_value=0, step=1, value=int(servidor_edit["relatorios_entregues"]) if servidor_edit is not None else 0)
            
            prorrogado = st.selectbox("AFASTAMENTO PRORROGADO?", ["Não", "Sim"], index=0 if servidor_edit is None or servidor_edit["prorrogado"]=="Não" else 1)
            
            status_opcoes = [
                "Em Dia",
                "Atrasado com Relatório Semestral",
                "Atrasado com Diploma",
                "Prorrogado",
                "Em Cobrança / Processo",
                "Finalizado"
            ]
            
            status = st.selectbox("STATUS ATUAL DO SERVIDOR", status_opcoes)

        observacoes = st.text_area("Observações Adicionais", value=servidor_edit["observacoes"] if servidor_edit is not None else "")

        btn_salvar = st.form_submit_button("Salvar Dados do Servidor")
        
        if btn_salvar:
            c = conn.cursor()
            if opcao_acao == "Novo Cadastro":
                c.execute('''
                    INSERT INTO servidores (nome, matricula, protocolo, nivel, data_inicio, data_fim, relatorios_entregues, email, pasta, status, prorrogado, observacoes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nome, matricula, protocolo, nivel, str(data_inicio), str(data_fim), relat_entregues, email, pasta, status, prorrogado, observacoes))
                st.success("Servidor cadastrado com sucesso!")
            else:
                c.execute('''
                    UPDATE servidores SET nome=?, matricula=?, protocolo=?, nivel=?, data_inicio=?, data_fim=?, relatorios_entregues=?, email=?, pasta=?, status=?, prorrogado=?, observacoes=?
                    WHERE id=?
                ''', (nome, matricula, protocolo, nivel, str(data_inicio), str(data_fim), relat_entregues, email, pasta, status, prorrogado, observacoes, serv_id))
                st.success("Cadastro atualizado com sucesso!")
            conn.commit()
            st.rerun()
    conn.close()

# MÓDULO 3: GESTÃO DE COBRANÇAS E NOTIFICAÇÕES (IN 001/2018)
elif menu == "Gestão de Cobranças":
    st.subheader("Registro de Cobranças e Processos Administrativos")
    
    conn = get_connection()
    df_cobranca = pd.read_sql_query("SELECT id, nome, matricula, status, cobrado, data_cobranca, resposta_servidor, processo_cobranca FROM servidores", conn)
    
    if not df_cobranca.empty:
        serv_sel = st.selectbox("Selecione o Servidor para Notificar/Cobrar", df_cobranca["id"].astype(str) + " - " + df_cobranca["nome"])
        serv_id = int(serv_sel.split(" - ")[0])
        serv_data = df_cobranca[df_cobranca["id"] == serv_id].iloc[0]
        
        with st.form("form_cobranca"):
            cobrado = st.selectbox("COBRANÇA REALIZADA?", ["Sim", "Não"], index=0 if serv_data["cobrado"]=="Sim" else 1)
            data_cob = pd.to_datetime(serv_data["data_cobranca"]).date() if serv_data["data_cobranca"] else date.today()
            data_cobranca = st.date_input("DATA DA NOTIFICAÇÃO / COBRANÇA", value=data_cob)
            resposta_servidor = st.text_area("RESPOSTA DO SERVIDOR (Prazo de 15 dias corridos conforme IN 001/2018)", value=serv_data["resposta_servidor"] or "")
            processo_cobranca = st.text_input("NÚMERO DO PROCESSO DE COBRANÇA / RESSARCIMENTO", value=serv_data["processo_cobranca"] or "")
            
            if st.form_submit_button("Atualizar Cobrança"):
                c = conn.cursor()
                c.execute('''
                    UPDATE servidores SET cobrado=?, data_cobranca=?, resposta_servidor=?, processo_cobranca=?, status=? WHERE id=?
                ''', (cobrado, str(data_cobranca), resposta_servidor, processo_cobranca, "Em Cobrança / Processo" if cobrado=="Sim" else serv_data["status"], serv_id))
                conn.commit()
                st.success("Dados de cobrança salvos com sucesso!")
                st.rerun()
    conn.close()

# MÓDULO 4: CADASTRAR USUÁRIOS (ADMIN)
elif menu == "Cadastrar Usuários (Admin)":
    if st.session_state["perfil"] != "admin":
        st.warning("Apenas administradores podem cadastrar novos usuários de acesso.")
    else:
        st.subheader("Cadastro de Matrículas Autorizadas para Acesso")
        with st.form("form_user"):
            nova_matricula = st.text_input("Número da Matrícula / Usuário")
            nova_senha = st.text_input("Senha", type="password")
            nome_usuario = st.text_input("Nome do Servidor do Setor")
            perfil = st.selectbox("Perfil de Acesso", ["operador", "admin"])
            
            if st.form_submit_button("Cadastrar Usuário"):
                conn = get_connection()
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO usuarios (matricula, senha, nome, perfil) VALUES (?, ?, ?, ?)",
                              (nova_matricula, nova_senha, nome_usuario, perfil))
                    conn.commit()
                    st.success("Usuário cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao cadastrar: Matrícula já existe.")
                conn.close()
