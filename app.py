import streamlit as st
import pandas as pd
from datetime import datetime

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

st.title("🛡️ Scouting Pro - Liga Distrital & Nacional")

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

    # Conversões numéricas robustas
    for col in ['T', 'SU', 'M', 'A', 'AA', 'V', 'GM', 'J']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calcular Mins/Golo
    if 'M' in df.columns and 'GM' in df.columns:
        df['Mins/Golo'] = df['M'] / df['GM']
        df['Mins/Golo'] = df['Mins/Golo'].replace([float('inf'), float('-inf')], 0).fillna(0).round(1)
        
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
                return float(row['Idade'])
            data = row.get('Data Nascimento')
            if pd.isna(data): return None
            try:
                if '-' in str(data):
                    partes = str(data).split('-')
                    if len(partes[0]) == 4:
                        nasc = datetime.strptime(str(data), '%Y-%m-%d')
                    else:
                        nasc = datetime.strptime(str(data), '%d-%m-%Y')
                    hoje = datetime.today()
                    return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
            except:
                pass
            return None
        df['Idade'] = df.apply(force_calc_age, axis=1)

    # Garantir apenas 1 entrada por jogador (a mais relevante / atual com mais jogos)
    if 'Jogador' in df.columns and 'J' in df.columns:
        df = df.sort_values(by=['J', 'M'], ascending=[False, False]).drop_duplicates(subset=['Jogador'], keep='first')

    return df

df = load_data()

if df.empty:
    st.error("Nenhum ficheiro encontado (Competicao_Todas_Nova.xlsx ou Competicao_Todas.xlsx). Corra o scrapper V2 primeiro.")
else:
    # --- FILTROS LATERAIS ---
    st.sidebar.header("🔍 Filtros de Scouting")
    
    # Categorização das Ligas
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
        
    divisoes = st.sidebar.multiselect("Divisão", options=df['Divisao'].dropna().unique())
    if divisoes:
        df = df[df['Divisao'].isin(divisoes)]
        
    equipas = st.sidebar.multiselect("Equipa", options=df['Equipa'].dropna().unique())
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
    t1, t2, t3, t4, t5 = st.tabs(["🔥 Top Marcadores", "⚡ Eficiência (Mins/Golo)", "📋 Plantel Completo", "⏱️ Destaques U23 (Minutos)", "⚽ Destaques U23 (Golos)"])
    
    with t1:
        st.subheader("Maiores Goleadores")
        top_scorers = df.sort_values('GM', ascending=False).head(15)
        # Mostrar colunas principais
        cols_show = ['Jogador', 'Equipa', 'Divisao', 'Idade', 'Posição', 'J', 'M', 'GM', 'Mins/Golo', '% Tempo Equipa']
        cols_show = [c for c in cols_show if c in top_scorers.columns]
        st.dataframe(top_scorers[cols_show].style.format({'% Tempo Equipa': '{:.1f}%'}, na_rep='-'), use_container_width=True)
        
    with t2:
        st.subheader("Melhor Rácio de Minutos por Golo (Mín. 2 Golos)")
        df_efic = df[df['GM'] >= 2].sort_values('Mins/Golo', ascending=True).head(15)
        cols_show = ['Jogador', 'Equipa', 'Divisao', 'Idade', 'Posição', 'J', 'M', 'GM', 'Mins/Golo', '% Tempo Equipa']
        cols_show = [c for c in cols_show if c in df_efic.columns]
        st.dataframe(df_efic[cols_show].style.format({'% Tempo Equipa': '{:.1f}%'}, na_rep='-'), use_container_width=True)
        
    with t3:
        st.subheader("Base de Dados Filtrada")
        if len(df) > 1000:
            st.warning(f"Exibindo 1000 / {len(df)} registos em formato de tabela (para poupar memória). Refine na barra lateral.")
            st.dataframe(df.head(1000), use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

    with t4:
        st.subheader("Destaques U23 - Mais Minutos por Liga")
        if df['Idade'].notna().sum() > 0:
            df_u23 = df[df['Idade'] < 23]
            if not df_u23.empty:
                # Top 3 jogadores com mais minutos por divisão
                top_mins_u23 = df_u23.sort_values(['Divisao', 'M'], ascending=[True, False]).groupby('Divisao').head(3)
                cols_show = ['Divisao', 'Jogador', 'Equipa', 'Idade', 'Posição', 'J', 'M', 'GM', '% Tempo Equipa']
                cols_show = [c for c in cols_show if c in top_mins_u23.columns]
                st.dataframe(top_mins_u23[cols_show].style.format({'% Tempo Equipa': '{:.1f}%'}, na_rep='-'), use_container_width=True)
            else:
                st.info("Nenhum jogador U23 encontrado nos dados atuais.")
        else:
            st.warning("Dados de idade não disponíveis para filtrar U23.")

    with t5:
        st.subheader("Destaques U23 - Mais Golos por Liga")
        if df['Idade'].notna().sum() > 0:
            df_u23 = df[df['Idade'] < 23]
            if not df_u23.empty:
                # Top 3 jogadores com mais golos por divisão
                top_gols_u23 = df_u23.sort_values(['Divisao', 'GM'], ascending=[True, False]).groupby('Divisao').head(3)
                cols_show = ['Divisao', 'Jogador', 'Equipa', 'Idade', 'Posição', 'J', 'M', 'GM', 'Mins/Golo']
                cols_show = [c for c in cols_show if c in top_gols_u23.columns]
                st.dataframe(top_gols_u23[cols_show], use_container_width=True)
            else:
                st.info("Nenhum jogador U23 encontrado nos dados atuais.")
        else:
            st.warning("Dados de idade não disponíveis para filtrar U23.")

