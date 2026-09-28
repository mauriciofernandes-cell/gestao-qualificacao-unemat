import pandas as pd

# Let's recreate the exact spreadsheet layout shown in the screenshot:
# Row 0: "RELATÓRIO REFERENTE AO ACOMPANHAMENTO DAS AÇÕES DE QUALIFICAÇÃO DA UNEMAT..." (Title)
# Row 1: NaN / empty
# Row 2: "SERVIDORES", "MATRÍCULA", "PROTOCOLO", "CURSO/PROGRAMA", "NÍVEL", "PERÍODO DE AFASTAMENTO", "SITUAÇÃO / STATUS"
# Row 3: "João da Silva", "82426/1", "90294/2017", "Direito", "Mestrado", "03/04/2017 A 02/04/2018", "CERTIFICADO ENTREGUE"

raw_data = [
    ["RELATÓRIO REFERENTE AO ACOMPANHAMENTO DAS AÇÕES DE QUALIFICAÇÃO", None, None, None, None, None, None],
    [None, None, None, None, None, None, None],
    ["SERVIDORES", "MATRÍCULA", "PROTOCOLO", "CURSO / PROGRAMA", "NÍVEL", "PERÍODO DE AFASTAMENTO", "SITUAÇÃO / STATUS"],
    ["João da Silva", "82426/1", "90294/2017", "Direito", "Mestrado", "03/04/2017 A 02/04/2018", "CERTIFICADO ENTREGUE"],
    ["Maria Oliveira", "127796/7", "587140/2017", "Física", "Doutorado", "12/03/2018 A 01/12/2022", "CERTIFICADO ENTREGUE"]
]

df_raw = pd.DataFrame(raw_data)

def encontrar_cabecalho_real(df):
    """
    Scans the first 20 rows of a dataframe to locate the row that contains
    the actual table headers (e.g., Matrícula, Servidor/Nome, Status, Curso, etc.)
    """
    keywords = [
        'matr', 'matrícula', 'matricula', 'nome', 'servidor', 'servidores', 
        'docente', 'tecnico', 'técnico', 'interessado', 'curso', 'programa', 
        'nivel', 'nível', 'inicio', 'início', 'afastamento', 'período', 'periodo',
        'termino', 'término', 'previsão', 'previsao', 'status', 'situaç', 'situac', 'relat'
    ]
    
    best_row_idx = None
    max_matches = 0
    
    # First check existing columns if dataframe already has headers
    cols_vals = [str(c).lower().strip() for c in df.columns]
    matches_cols = sum(1 for kw in keywords if any(kw in col for col in cols_vals))
    if matches_cols >= 2:
        best_row_idx = -1 # existing columns are good
        max_matches = matches_cols

    # Scan rows 0 to min(20, len(df))
    for idx in range(min(20, len(df))):
        row_vals = [str(v).lower().strip() for v in df.iloc[idx].values if pd.notna(v)]
        matches = sum(1 for kw in keywords if any(kw in cell for cell in row_vals))
        if matches > max_matches:
            max_matches = matches
            best_row_idx = idx
            
    if best_row_idx is not None and best_row_idx >= 0:
        new_cols = [
            str(val).strip() if (pd.notna(val) and str(val).strip() != '') else f"Coluna_{i}" 
            for i, val in enumerate(df.iloc[best_row_idx].values)
        ]
        df_clean = df.iloc[best_row_idx + 1:].copy()
        df_clean.columns = new_cols
    else:
        df_clean = df.copy()
        
    return df_clean

df_fixed = encontrar_cabecalho_real(df_raw)
print("Detected Columns:", df_fixed.columns.tolist())
print(df_fixed)
