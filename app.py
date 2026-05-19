import streamlit as st
import pandas as pd
from datetime import datetime
import io
import folium
from streamlit_folium import st_folium

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
    
    # Formatação automática: Floats com 2 casas, Inteiros sem casas
    format_dict = {}
    for col in subset.columns:
        # Colunas específicas com formatação especial
        if col == '% Tempo Equipa':
            format_dict[col] = '{:.1f}%'
        elif col in ['Mins/Golo', 'min/golo']:
            format_dict[col] = '{:.2f}'
        # Colunas que são inteiros na prática (Golos, Jogos, Idade, etc)
        elif col in ['Idade', 'J', 'GM', 'T', 'SU', 'M', 'A', 'AA', 'V', 'Equipa_ID', 'Jogador_ID', 'Jogos', 'Golos', 'Titular', 'Suplente Utilizado', 'Mins']:
            format_dict[col] = '{:.0f}'
        # Outros números decimais
        elif pd.api.types.is_float_dtype(subset[col]):
            format_dict[col] = '{:.2f}'
        
    col_config = {}
    if 'Perfil Jogador' in subset.columns:
        col_config["Perfil Jogador"] = st.column_config.LinkColumn("Perfil Jogador", display_text="Ver Perfil")
    if 'Relatório' in subset.columns:
        col_config["Relatório"] = st.column_config.LinkColumn("Relatório", display_text="Ver Relatório")
    
    st.dataframe(subset.style.format(format_dict, na_rep='-'), use_container_width=True, hide_index=True, column_config=col_config)
    
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
st.set_page_config(page_title="Improve Sports: Scouting", layout="wide", page_icon="⚽")

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

col_logo, col_title = st.columns([1, 10])
with col_logo:
    import os
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
with col_title:
    st.title("Improve Sports: Scouting")

@st.cache_data
def load_data():
    import sqlite3
    import os
    
    db_path = 'scouting.db'
    df = None
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query("SELECT * FROM scouting_data", conn)
            conn.close()
            
            # Restaurar nomes originais para compatibilidade da App
            renames = {}
            if 'Posicao' in df.columns:
                renames['Posicao'] = 'Posição'
            if 'Data_Nascimento' in df.columns:
                renames['Data_Nascimento'] = 'Data Nascimento'
            if renames:
                df = df.rename(columns=renames)
                
            # O processamento numérico e de cálculos continua abaixo
        except Exception as e:
            st.error(f"Erro ao ler BD SQLite: {e}")
            df = None
            
    # Fallback para Excel
    if df is None or df.empty:
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

    # Adicionar Hiperligação ZeroZero e Pedidos de Relatório
    if 'Jogador_ID' in df.columns:
        df['Perfil Jogador'] = df['Jogador_ID'].apply(lambda x: f"https://www.zerozero.pt/jogador.php?id={int(x)}" if pd.notna(x) and str(x).replace('.0','').isdigit() else None)

    import urllib.parse
    def generate_form_link(row):
        nome = str(row.get('Jogador', ''))
        equipa = str(row.get('Equipa', ''))
        texto_preenchido = f"{nome} [{equipa}]" if equipa else nome
        return f"https://docs.google.com/forms/d/e/1FAIpQLSf40zlpzNzoNvDMl53XIfVvXxKDVRIcOXEoFHaMivzpC4Z2aQ/viewform?usp=pp_url&entry.1156344699={urllib.parse.quote(texto_preenchido)}"
        
    df['Relatório'] = df.apply(generate_form_link, axis=1)

    return df

df_raw = load_data()

if df_raw.empty:
    st.error("Nenhum ficheiro encontado (Competicao_Todas.xlsx). Corra o scrapper primeiro.")
else:
    df = df_raw.copy()
    
    # --- FILTROS LATERAIS ---
    st.sidebar.header("🔍 Filtros Scouting")
    
    # Filtro de Nome do Jogador com Dropdown
    df['Nome_Dropdown'] = df['Jogador'] + " (" + df['Equipa'] + ")"
    jogadores_selecionados = st.sidebar.multiselect("Procurar Jogador", options=sorted(df['Nome_Dropdown'].dropna().unique()))
    if jogadores_selecionados:
        df = df[df['Nome_Dropdown'].isin(jogadores_selecionados)]
    
    categorias_map = {
        "Liga Nacional": ["CP_SerieA", "CP_SerieB", "CP_SerieC", "CP_SerieD", "Liga3_SerieA", "Liga3_SerieB"],
        "1ª Divisão Distrital": ["Braga", "Leiria", "Coimbra", "Vila_Real", "Algarve", "Aveiro", "Castelo_Branco", "Porto", "Lisboa", "Viseu", "Setubal", "Santarem", "Braganca", "Beja", "Evora", "Viana_Castelo", "Guarda", "Portalegre", "Madeira", "Acores"],
        "2ª Divisão Distrital": ["II_Lisboa_Serie1", "II_Lisboa_Serie2", "II_Porto_Serie1", "II_Porto_Serie2", "II_Porto_Serie3", "II_Algarve", "II_Aveiro", "II_Beja", "II_Braga_SerieA", "II_Braga_SerieB", "II_Braga_SerieC", "II_Coimbra", "II_Evora", "II_Guarda", "II_Leiria", "II_Santarem", "II_Setubal", "II_Viana_Castelo", "II_Viseu"],
        "Ligas Formação": ["LigaRev_SerieNorte", "LigaRev_SerieSul", "Sub23-SerieNorte", "Sub23-SerieSul", "I_sub19_SerieNorte", "I_sub19_SerieSul", "II_sub19-SerieA", "II_sub19-SerieB", "II_sub19-SerieC", "II_sub19-SerieD"],
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
        if idade_min == idade_max:
            st.sidebar.info(f"Idade única filtrada: {idade_min} anos")
        else:
            idades = st.sidebar.slider("Idade do Jogador", idade_min, idade_max, (idade_min, idade_max))
            df = df[(df['Idade'].isna()) | ((df['Idade'] >= idades[0]) & (df['Idade'] <= idades[1]))]

    min_jogos = st.sidebar.slider("Mínimo de Jogos (J)", 0, 50, 5)
    df = df[df['J'] >= min_jogos]

    main_tab1, main_tab2 = st.tabs(["🌍 Visão Geral (Mapa)", "🔎 Scouting"])
    
    with main_tab1:
        st.subheader("Panorama de Recrutamento")
        st.markdown("Mapa interativo de clubes baseados nos filtros selecionados.")
        
        import os
        if os.path.exists("Dim_Clubes_Geo.xlsx"):
            df_geo = pd.read_excel("Dim_Clubes_Geo.xlsx")
            df_geo = df_geo.dropna(subset=['lat', 'lon'])
            
            # Definir ligas alvo para relatórios
            ligas_alvo = [
                'CP_SerieA', 'CP_SerieB', 'CP_SerieC', 'CP_SerieD', 
                'Liga3_SerieA', 'Liga3_SerieB', 
                'Aveiro', 'II_Aveiro', 'Lisboa', 'II_Lisboa_Serie1', 'II_Lisboa_Serie2', 
                'Porto', 'II_Porto_Serie1', 'II_Porto_Serie2', 'II_Porto_Serie3', 
                'Sub23-SerieNorte', 'Sub23-SerieSul', 'LigaRev_SerieNorte', 'LigaRev_SerieSul'
            ]
            df_rel = df[(df['Divisao'].isin(ligas_alvo)) & (df['M'] >= 300)]
            rel_counts = df_rel.groupby('Equipa').size().reset_index(name='Relatórios Disponíveis')
            
            df_counts = df.groupby('Equipa').size().reset_index(name='Jogadores Observados')
            df_counts = pd.merge(df_counts, rel_counts, on='Equipa', how='left').fillna({'Relatórios Disponíveis': 0})
            
            df_map = pd.merge(df_counts, df_geo, on='Equipa', how='inner')
            
            if not df_map.empty:
                m = folium.Map(location=[39.3999, -8.2245], zoom_start=6, tiles="CartoDB positron")
                
                for idx, row in df_map.iterrows():
                    count = row['Jogadores Observados']
                    rels = int(row['Relatórios Disponíveis'])
                    
                    if count >= 10: 
                        color = "green"
                        rad = 8
                    elif count >= 3: 
                        color = "orange"
                        rad = 6
                    else: 
                        color = "red"
                        rad = 5
                        
                    folium.CircleMarker(
                        location=[row['lat'], row['lon']],
                        radius=rad,
                        popup=f"<b>{row['Equipa']}</b><br>Jogadores Observados: {count}<br>Relatórios Disponíveis: {rels}",
                        tooltip=f"{row['Equipa']} ({count} jogadores, {rels} relatórios)",
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.7
                    ).add_to(m)
                    
                st_folium(m, width=1200, height=600, returned_objects=[])
            else:
                st.info("Nenhuma equipa no filtro atual possui dados de geolocalização.")
        else:
            st.warning("Ficheiro Dim_Clubes_Geo.xlsx não encontrado. Execute o script de geolocalização primeiro.")

    with main_tab2:
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
            cols_show = ['Jogador', 'Equipa', 'Divisao', 'Idade', 'Posição', 'J', 'GM', 'Mins/Golo', 'Perfil Jogador', 'Relatório']
            cols_show = [c for c in cols_show if c in top_scorers.columns]
            df_display = top_scorers[cols_show].rename(columns={
                'J': 'Jogos',
                'GM': 'Golos',
                'Mins/Golo': 'min/golo',
                'T': 'Titular',
                'SU': 'Suplente Utilizado',
                'M': 'Mins'
            })
            display_paginated_df(df_display, "top_scorers", "top_marcadores.xlsx")
            
        with t2:
            st.subheader("Melhor Rácio de Minutos por Golo (Mín. 2 Golos)")
            df_efic = df[df['GM'] >= 2].sort_values('Mins/Golo', ascending=True)
            cols_show = ['Jogador', 'Equipa', 'Divisao', 'Idade', 'Posição', 'J', 'M', 'GM', 'Mins/Golo', 'Perfil Jogador', 'Relatório']
            cols_show = [c for c in cols_show if c in df_efic.columns]
            df_display = df_efic[cols_show].rename(columns={
                'J': 'Jogos',
                'GM': 'Golos',
                'Mins/Golo': 'min/golo',
                'T': 'Titular',
                'SU': 'Suplente Utilizado',
                'M': 'Mins'
            })
            display_paginated_df(df_display, "efficiency", "eficiencia.xlsx")
            
        with t3:
            st.subheader("Base de Dados Completa")
            # Comentar colunas A, AA, V e Altura
            cols_hide = ['Equipa_ID', 'Jogador_ID', 'Nome_Dropdown', 'Categoria', 'A', 'AA', 'V', 'Altura']
            cols_show = [c for c in df.columns if c not in cols_hide]
            
            # Reordenar: Data Nascimento, min/golo, % tempo equipa. E retirar Perfil Jogador do Plantel Completo.
            base_cols = ['Jogador', 'Equipa', 'Divisao', 'Posição', 'Data Nascimento', 'Idade', 'Mins/Golo', '% Tempo Equipa', 'J', 'M', 'GM', 'T', 'SU']
            remaining = [c for c in cols_show if c not in base_cols and c not in ['Perfil Jogador', 'Relatório']]
            # Ocultamos Perfil Jogador no Plantel Completo
            final_cols = base_cols + remaining + ['Relatório']
            final_cols = [c for c in final_cols if c in df.columns]
            
            df_display = df[final_cols].rename(columns={
                'J': 'Jogos',
                'GM': 'Golos',
                'Mins/Golo': 'min/golo',
                'T': 'Titular',
                'SU': 'Suplente Utilizado',
                'M': 'Mins'
            })
            
            display_paginated_df(df_display, "full_db", "base_dados_completa.xlsx")

        with t4:
            st.subheader("Destaques U23 - Mais Minutos por Liga (Top 10)")
            if df['Idade'].notna().sum() > 0:
                df_u23 = df[df['Idade'] < 23]
                if not df_u23.empty:
                    top_mins_u23 = df_u23.sort_values(['Divisao', 'M'], ascending=[True, False]).groupby('Divisao').head(10)
                    cols_show = ['Divisao', 'Jogador', 'Equipa', 'Idade', 'Posição', 'J', 'M', '% Tempo Equipa', 'Perfil Jogador', 'Relatório']
                    cols_show = [c for c in cols_show if c in top_mins_u23.columns]
                    df_display = top_mins_u23[cols_show].rename(columns={
                'J': 'Jogos',
                'GM': 'Golos',
                'Mins/Golo': 'min/golo',
                'T': 'Titular',
                'SU': 'Suplente Utilizado',
                'M': 'Mins'
            })
                    display_paginated_df(df_display, "u23_mins", "u23_minutos.xlsx")
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
                    cols_show = ['Divisao', 'Jogador', 'Equipa', 'Idade', 'Posição', 'J', 'GM', 'Mins/Golo', 'Perfil Jogador', 'Relatório']
                    cols_show = [c for c in cols_show if c in top_gols_u23.columns]
                    df_display = top_gols_u23[cols_show].rename(columns={
                'J': 'Jogos',
                'GM': 'Golos',
                'Mins/Golo': 'min/golo',
                'T': 'Titular',
                'SU': 'Suplente Utilizado',
                'M': 'Mins'
            })
                    display_paginated_df(df_display, "u23_gols", "u23_golos.xlsx")
                else:
                    st.info("Nenhum jogador U23 encontrado.")
            else:
                st.warning("Dados de idade não disponíveis.")
