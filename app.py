import streamlit as st
import pandas as pd
from datetime import datetime
import io

# Helper para exportar Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='ScoutingData')
    return output.getvalue()

# Helper para Paginação e Exportação
def display_paginated_df(df, key, filename="scouting_export.xlsx"):
    if key not in st.session_state:
        st.session_state[key] = 50
    
    subset = df.head(st.session_state[key])
    
    # Formatação condicional se colunas existirem
    format_dict = {}
    if '% Tempo Equipa' in subset.columns:
        format_dict['% Tempo Equipa'] = '{:.1f}%'
    if 'Mins/Golo' in subset.columns:
        format_dict['Mins/Golo'] = '{:.2f}'
    
    if format_dict:
        st.dataframe(subset.style.format(format_dict, na_rep='-'), use_container_width=True)
    else:
        st.dataframe(subset, use_container_width=True)
    
    c1, c2 = st.columns([1, 1])
    with c1:
        if len(df) > st.session_state[key]:
            if st.button(f"📥 Carregar mais 50 ({len(df) - st.session_state[key]} restantes)", key=f"btn_{key}"):
                st.session_state[key] += 50
                st.rerun()
    with c2:
        st.download_button(
            label="📊 Extrair como XLSX",
            data=to_excel(df),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_{key}"
        )

# Configuração da Página para Look Premium
st.set_page_config(page_title="Scouting Pro Dashboard", layout="wide", page_icon="⚽")

# CSS Avançado
st.markdown("""
    <style>
        .main {
            background-color: #0f172a;
            color: #f8fafc;
        }
        h1, h2, h3 {
            color: #38bdf8;
            font-family: 'Inter', sans-serif;
        }
        .metric-card {
            background: rgba(30, 41, 59, 0.7);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            text-align: center;
            border-left: 4px solid #38bdf8;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(56, 189, 248, 0.4);
        }
        .stDataFrame {
            background-color: #1e293b;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Improve Sports - Scouting Pro")

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("Competicao_Todas.xlsx")
    except FileNotFoundError:
        return pd.DataFrame()
            
    # Normalize column names for Player
    col_jogador = 'Jogador' if 'Jogador' in df.columns else ('Unnamed: 2' if 'Unnamed: 2' in df.columns else None)
    if col_jogador and col_jogador != 'Jogador':
        df = df.rename(columns={col_jogador: 'Jogador'})

    # Dropar colunas irrelevantes
    if 'Unnamed: 13' in df.columns:
        df = df.drop(columns=['Unnamed: 13'])

    # Conversões numéricas robustas
    for col in ['T', 'SU', 'M', 'A', 'AA', 'V', 'GM', 'J']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calcular Mins/Golo
    if 'M' in df.columns and 'GM' in df.columns:
        df['Mins/Golo'] = df['M'] / df['GM']
        df['Mins/Golo'] = df['Mins/Golo'].replace([float('inf'), float('-inf')], 0).fillna(0).round(2)
        
    # Calcular % Tempo Equipa
    if 'M' in df.columns and 'J' in df.columns and 'Equipa' in df.columns:
        max_jogos = df.groupby('Equipa')['J'].transform('max')
        df['% Tempo Equipa'] = (df['M'] / (max_jogos * 90)) * 100
        df['% Tempo Equipa'] = df['% Tempo Equipa'].replace([float('inf'), float('-inf')], 0).fillna(0).round(1)

    if 'Idade' not in df.columns:
        df['Idade'] = None
        
    # Calcular ou converter Idade a partir de Data Nascimento
    if 'Idade' in df.columns or 'Data Nascimento' in df.columns:
        def force_calc_age(row):
            if pd.notna(row.get('Idade')):
                try: return float(row['Idade'])
                except: pass
            data = row.get('Data Nascimento')
            if pd.isna(data): return None
            try:
                data_str = str(data).split(' ')[0] # Remover tempo se existir
                if '-' in data_str:
                    partes = data_str.split('-')
                    if len(partes[0]) == 4:
                        nasc = datetime.strptime(data_str, '%Y-%m-%d')
                    else:
                        nasc = datetime.strptime(data_str, '%d-%m-%Y')
                elif '/' in data_str:
                    partes = data_str.split('/')
                    if len(partes[2]) == 4:
                        nasc = datetime.strptime(data_str, '%d/%m/%Y')
                    else:
                        nasc = datetime.strptime(data_str, '%Y/%m/%d')
                else:
                    return None
                hoje = datetime.today()
                return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
            except:
                pass
            return None
        df['Idade'] = df.apply(force_calc_age, axis=1)
        df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce').astype('Int64')

    # Garantir apenas 1 entrada por jogador (a mais relevante / atual com mais jogos)
    if 'Jogador' in df.columns and 'J' in df.columns:
        df = df.sort_values(by=['J', 'M'], ascending=[False, False]).drop_duplicates(subset=['Jogador'], keep='first')

    return df

df_raw = load_data()

if df_raw.empty:
    st.error("Nenhum ficheiro encontado (Competicao_Todas.xlsx). Corra o scrapper primeiro.")
else:
    df = df_raw.copy()
    
    # --- FILTROS LATERAIS ---
    st.sidebar.header("🔍 Filtros Scouting")
    
    categorias_map = {
        "Liga Nacional": ["CP_SerieA", "CP_SerieB", "CP_SerieC", "CP_SerieD", "Liga3_SerieA", "Liga3_SerieB"],
        "1ª Divisão Distrital": ["Braga", "Leiria", "Coimbra", "Vila_Real", "Algarve", "Aveiro", "Castelo_Branco", "Porto", "Lisboa", "Viseu", "Setubal", "Santarem", "Braganca", "Beja", "Evora", "Viana_Castelo", "Guarda", "Portalegre", "Madeira", "Acores"],
        "2ª Divisão Distrital": ["II_Lisboa_Serie1", "II_Lisboa_Serie2", "II_Porto_Serie1", "II_Porto_Serie2", "II_Porto_Serie3", "II_Algarve", "II_Aveiro", "II_Beja", "II_Braga_SerieA", "II_Braga_SerieB", "II_Braga_SerieC", "II_Coimbra", "II_Evora", "II_Guarda", "II_Leiria", "II_Santarem", "II_Setubal", "II_Viana_Castelo", "II_Viseu"],
        "Ligas Formação": ["Sub23-SerieNorte", "Sub23-SerieSul", "I_sub19_SerieNorte", "I_sub19_SerieSul", "II_sub19-SerieA", "II_sub19-SerieB", "II_sub19-SerieC", "II_sub19-SerieD"],
        "Estrangeiro": ["National_I", "Copinha"]
    }
    
    inv_map = {div: cat for cat, divs in categorias_map.items() for div in divs}
    df['Categoria'] = df['Divisao'].map(inv_map).fillna("Outro")
    
    categorias_selecionadas = st.sidebar.multiselect("Categoria de Liga", options=["Liga Nacional", "1ª Divisão Distrital", "2ª Divisão Distrital", "Ligas Formação", "Estrangeiro", "Outro"])
    if categorias_selecionadas:
        df = df[df['Categoria'].isin(categorias_selecionadas)]
        
    divisoes = st.sidebar.multiselect("Divisão", options=sorted(df['Divisao'].dropna().unique()))
    if divisoes:
        df = df[df['Divisao'].isin(divisoes)]
        
    equipas = st.sidebar.multiselect("Equipa", options=sorted(df['Equipa'].dropna().unique()))
    if equipas:
        df = df[df['Equipa'].isin(equipas)]
        
    posicoes = st.sidebar.multiselect("Posição", options=df['Posição'].dropna().unique())
    if posicoes:
        df = df[df['Posição'].isin(posicoes)]
        
    if df['Idade'].notna().sum() > 0:
        idade_min = int(df['Idade'].min(skipna=True))
        idade_max = int(df['Idade'].max(skipna=True))
        idades = st.sidebar.slider("Idade do Jogador", idade_min, idade_max, (idade_min, idade_max))
        df = df[(df['Idade'].isna()) | ((df['Idade'] >= idades[0]) & (df['Idade'] <= idades[1]))]

    min_jogos = st.sidebar.slider("Mínimo de Jogos (J)", 0, 50, 5)
    df = df[df['J'] >= min_jogos]

    # --- DESTAQUES GLOBAIS ---
    st.markdown("### 🏆 Destaques")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><h4>Total Jogadores</h4><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
    with c2:
        top_gols = df['GM'].max()
        st.markdown(f"<div class='metric-card'><h4>Máximo Golos</h4><h2>{int(top_gols)}</h2></div>", unsafe_allow_html=True)
    with c3:
        media_idade = df['Idade'].mean()
        idade_txt = f"{media_idade:.1f}" if pd.notna(media_idade) else "N/A"
        st.markdown(f"<div class='metric-card'><h4>Média Idades</h4><h2>{idade_txt}</h2></div>", unsafe_allow_html=True)
    with c4:
        total_gols = df['GM'].sum()
        st.markdown(f"<div class='metric-card'><h4>Golos Totais (Filtro)</h4><h2>{int(total_gols)}</h2></div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # --- ABAS DE ANÁLISE ---
    t1, t2, t3, t4, t5 = st.tabs(["🔥 Top Marcadores", "⚡ Eficiência", "📋 Plantel Completo", "⏱️ U23 (Minutos)", "⚽ U23 (Golos)"])
    
    with t1:
        st.subheader("Maiores Goleadores")
        top_scorers = df.sort_values('GM', ascending=False)
        cols_show = ['Jogador', 'Equipa', 'Divisao', 'Idade', 'Altura', 'Posição', 'J', 'GM', 'Mins/Golo']
        cols_show = [c for c in cols_show if c in top_scorers.columns]
        display_paginated_df(top_scorers[cols_show], "top_scorers", "top_marcadores.xlsx")
        
    with t2:
        st.subheader("Melhor Rácio de Minutos por Golo (Mín. 2 Golos)")
        df_efic = df[df['GM'] >= 2].sort_values('Mins/Golo', ascending=True)
        cols_show = ['Jogador', 'Equipa', 'Divisao', 'Idade', 'Altura', 'Posição', 'J', 'M', 'GM', 'Mins/Golo']
        cols_show = [c for c in cols_show if c in df_efic.columns]
        display_paginated_df(df_efic[cols_show], "efficiency", "eficiencia.xlsx")
        
    with t3:
        st.subheader("Base de Dados Completa")
        display_paginated_df(df, "full_db", "base_dados_completa.xlsx")

    with t4:
        st.subheader("Destaques U23 - Mais Minutos por Liga (Top 10)")
        if df['Idade'].notna().sum() > 0:
            df_u23 = df[df['Idade'] < 23]
            if not df_u23.empty:
                top_mins_u23 = df_u23.sort_values(['Divisao', 'M'], ascending=[True, False]).groupby('Divisao').head(10)
                cols_show = ['Divisao', 'Jogador', 'Equipa', 'Idade', 'Altura', 'Posição', 'J', 'M', '% Tempo Equipa']
                cols_show = [c for c in cols_show if c in top_mins_u23.columns]
                display_paginated_df(top_mins_u23[cols_show], "u23_mins", "u23_minutos.xlsx")
            else:
                st.info("Nenhum jogador U23 encontrado.")
        else:
            st.warning("Dados de idade não disponíveis.")

    with t5:
        st.subheader("Destaques U23 - Mais Golos por Liga (Top 10)")
        if df['Idade'].notna().sum() > 0:
            df_u23 = df[df['Idade'] < 23]
            if not df_u23.empty:
                top_gols_u23 = df_u23.sort_values(['Divisao', 'GM'], ascending=[True, False]).groupby('Divisao').head(10)
                cols_show = ['Divisao', 'Jogador', 'Equipa', 'Idade', 'Altura', 'Posição', 'J', 'GM', 'Mins/Golo']
                cols_show = [c for c in cols_show if c in top_gols_u23.columns]
                display_paginated_df(top_gols_u23[cols_show], "u23_gols", "u23_golos.xlsx")
            else:
                st.info("Nenhum jogador U23 encontrado.")
        else:
            st.warning("Dados de idade não disponíveis.")
