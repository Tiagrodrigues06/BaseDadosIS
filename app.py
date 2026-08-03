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

    main_tab1, main_tab2, main_tab3 = st.tabs(["🌍 Visão Geral (Mapa)", "🔎 Scouting", "🛒 Mercado & Transferências"])
    
    with main_tab1:
        st.subheader("Panorama de Recrutamento")
        st.markdown("Mapa interativo de clubes baseados nos filtros selecionados.")
        
        import os
        if os.path.exists("Dim_Clubes_Geo.xlsx"):
            df_geo = pd.read_excel("Dim_Clubes_Geo.xlsx")
            df_geo = df_geo.dropna(subset=['lat', 'lon'])
            
            # Relatórios Disponíveis (Regras de Negócio)
            ligas_todos = ['CP_SerieA', 'CP_SerieB', 'CP_SerieC', 'CP_SerieD', 'Liga3_SerieA', 'Liga3_SerieB']
            ligas_300 = ['Aveiro', 'Lisboa', 'Porto', 'Sub23-SerieNorte', 'Sub23-SerieSul', 'LigaRev_SerieNorte', 'LigaRev_SerieSul']
            
            df_rel_todos = df[df['Divisao'].isin(ligas_todos)]
            df_rel_300 = df[(df['Divisao'].isin(ligas_300)) & (df['M'] >= 300)]
            
            import pandas as pd
            df_rel = pd.concat([df_rel_todos, df_rel_300])
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
            # Ordem especifica do utilizador
            exact_order = ['Jogador', 'Equipa', 'Divisao', 'Idade', 'J', 'M', 'GM', 'T', 'SU', 'Mins/Golo', 'Clube_Anterior', 'Tipo_Transferencia', 'Perfil Jogador', 'Relatório']
            # Adicionar outras colunas que possam existir (opcional, mas o utilizador pediu esta ordem exata)
            # Vamos usar apenas as que ele pediu explicitamente + Relatorio (para não perder o Forms)
            final_cols = [c for c in exact_order if c in df.columns]
            
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
                
    with main_tab3:
        st.subheader("Balanço de Mercado e Transferências Nacional")
        st.markdown("Análise de recrutamento: de onde vêm os jogadores dos clubes e como reforçaram o plantel.")
        
        import sqlite3
        import os
        
        df_mercado = pd.DataFrame()
        tem_dados_mercado = False
        
        # Tentar carregar tabela independente primeiro
        db_path_mercado = None
        for p in ['scouting.db', 'BaseDadosIS/scouting.db', 'Dados_Competicoes/scouting.db']:
            if os.path.exists(p):
                db_path_mercado = p
                break
                
        if db_path_mercado:
            try:
                conn = sqlite3.connect(db_path_mercado)
                df_mercado = pd.read_sql_query("SELECT * FROM mercado_data", conn)
                conn.close()
                tem_dados_mercado = not df_mercado.empty
            except Exception as e:
                st.error(f"Erro ao carregar mercado_data: {e}")
        
        # Se não existir tabela independente, tenta a base principal
        if not tem_dados_mercado and 'Clube_Anterior' in df.columns:
            df_mercado = df.copy()
            tem_dados_mercado = True
        
        if tem_dados_mercado:
            # Excluir equipas do Brasil e França da análise
            df_mercado = df_mercado[~df_mercado['Divisao'].isin(['Copinha', 'National1'])]
            equipa_to_divisao = {}
            if db_path_mercado:
                try:
                    conn_map = sqlite3.connect(db_path_mercado)
                    df_mapa = pd.read_sql_query("SELECT Equipa, Divisao FROM map_clubes_divisao", conn_map)
                    equipa_to_divisao = dict(zip(df_mapa['Equipa'], df_mapa['Divisao']))
                    conn_map.close()
                except Exception:
                    pass
            
            # Fallback para os dados atuais se a tabela falhar
            if not equipa_to_divisao:
                equipa_to_divisao = dict(zip(df_mercado['Equipa'], df_mercado['Divisao']))
            else:
                # Garantir que as do df_mercado atual também existem (caso falte alguma na bd global)
                for eq, div in zip(df_mercado['Equipa'], df_mercado['Divisao']):
                    if eq not in equipa_to_divisao:
                        equipa_to_divisao[eq] = div
            
            # ===== NOVO: CORREÇÕES MANUAIS DE DIVISÃO =====
            correcoes_manuais = {
                "SC Covilhã": "Liga 3",
                "Belenenses": "Liga 3", 
                "FC Felgueiras": "Segunda Liga",
                "FC Felgueiras 1932": "Segunda Liga",
                "UDR Santa Maria": "Distritais",
                "Guarda FC": "Campeonato Portugal",
                "Benf. Castelo Branco": "Campeonato Portugal",
                "Bragança": "Campeonato Portugal",
                "CD Gouveia": "Distritais",
                "O Elvas": "Campeonato Portugal",
                "Caldas SC": "Liga 3",
                "FC Alverca": "Segunda Liga",
                "Torreense": "Segunda Liga",
                "Tirsense": "Campeonato Portugal",
                "Ovarense": "Campeonato Portugal",
                "Amora FC": "Campeonato Portugal",
                "Vianense": "Campeonato Portugal",
                "Estoril Praia": "Primeira Liga",
                "USC Paredes": "Campeonato Portugal",
                "Fut. Benfica": "Distritais",
                "Est. Amadora": "Primeira Liga",
                "UD Leiria": "Segunda Liga",
                "1º Dezembro": "Liga 3",
                "Académica": "Liga 3"
            }
            equipa_to_divisao.update(correcoes_manuais)
            # ===============================================

            
            if 'Divisão Anterior' not in df_mercado.columns:
                def get_div_anterior(row):
                    clube_ant = str(row.get('Clube_Anterior', 'Manutenção'))
                    if pd.isna(clube_ant) or clube_ant == "Manutenção" or clube_ant == "Desconhecido":
                        return clube_ant
                        
                    # Equipas B/C ou sub 19 coloca formacao
                    clube_upper = clube_ant.upper()
                    if any(term in clube_upper for term in [" [B]", " B ", " [C]", " C ", "SUB", "JUN", "S19", "S23", "S17", "B]"]):
                        return "Formação"
                        
                    if clube_ant in equipa_to_divisao:
                        return equipa_to_divisao[clube_ant]
                        
                    return f"Estrangeiro (Not Found: '{clube_ant}')"
                
                df_mercado['Divisão Anterior'] = df_mercado.apply(get_div_anterior, axis=1)
            
            def ranking_divisao(div):
                if pd.isna(div) or div == "Desconhecido" or div == "Manutenção": return 99
                div_str = str(div)
                if "Primeira Liga" in div_str: return 1
                if "Segunda Liga" in div_str: return 2
                if "Estrangeiro" in div_str: return 1
                if "Liga 3" in div_str or "Liga3" in div_str: return 3
                if "CP_" in div_str: return 4
                if "Formação" in div_str or "Sub23" in div_str or "LigaRev" in div_str or "sub19" in div_str: return 6 # Formação
                return 5 # Distritais
                
            def categorizar_transf(row):
                if row['Clube_Anterior'] == "Manutenção": return "Mantido no Plantel"
                if row['Divisão Anterior'] == "Formação": return "Formação"
                if row['Divisão Anterior'] == "Estrangeiro": return "Estrangeiro"
                if row['Divisão Anterior'] == "Primeira Liga": return "Primeira Liga"
                if row['Divisão Anterior'] == "Segunda Liga": return "Segunda Liga"
                
                div_oficial_atual = equipa_to_divisao.get(row['Equipa'], row['Divisao'])
                rank_atual = ranking_divisao(div_oficial_atual)
                rank_ant = ranking_divisao(row['Divisão Anterior'])
                
                if rank_ant < rank_atual: return "Veio de Divisão Superior"
                if rank_ant > rank_atual: return "Veio de Divisão Inferior"
                return "Mesma Divisão"
            
            df_mercado['Origem_Analise'] = df_mercado.apply(categorizar_transf, axis=1)
            
            # =======================================================
            # 🎛️ FILTROS GLOBAIS DO MERCADO
            # =======================================================
            st.markdown("### 🎛️ Filtros Globais do Mercado")
            st.markdown("*(Estes filtros aplicam-se aos Gráficos, à Lista de Transferências e aos Destaques em simultâneo)*")
            
            # Mover a função normalizar_nome_liga cá para cima
            def normalizar_nome_liga(nome):
                if nome == 'Manutenção': return 'Ficou no Plantel'
                if pd.isna(nome): return 'Desconhecido'
                nome_str = str(nome).lower()
                if 'desconhecido' in nome_str: return 'Desconhecido'
                if 'primeira liga' in nome_str: return 'Primeira Liga'
                if 'segunda liga' in nome_str: return 'Segunda Liga'
                if 'formação' in nome_str or 'sub 19' in nome_str or 'sub19' in nome_str or 'juni' in nome_str or 'sub 23' in nome_str or 'sub23' in nome_str or 'ligarev' in nome_str: return 'Formação'
                if 'estrangeiro' in nome_str or 'outras ligas' in nome_str: return 'Estrangeiro'
                if 'cp_' in nome_str or 'cp ' in nome_str or 'campeonato' in nome_str: return 'Campeonato Portugal'
                if 'liga 3' in nome_str or 'liga3' in nome_str: return 'Liga 3'
                return 'Distritais'
                
            df_mercado['Divisão Simplificada'] = df_mercado['Divisão Anterior'].apply(normalizar_nome_liga)
            
            col_g1, col_g2, col_g3 = st.columns(3)
            with col_g1:
                gl_liga = st.multiselect("Liga Atual", options=sorted(df_mercado['Divisao'].dropna().unique()), default=[])
            with col_g2:
                if gl_liga:
                    clubes_possiveis = sorted(df_mercado[df_mercado['Divisao'].isin(gl_liga)]['Equipa'].dropna().unique())
                else:
                    clubes_possiveis = sorted(df_mercado['Equipa'].dropna().unique())
                gl_equipa = st.multiselect("Clube Atual", options=clubes_possiveis, default=[])
            with col_g3:
                gl_origem = st.multiselect("Origem (Liga/Divisão)", options=sorted(df_mercado['Divisão Simplificada'].unique().tolist()), default=[])
            
            col_g4, col_g5 = st.columns(2)
            with col_g4:
                if 'Formacao_Topo' in df_mercado.columns:
                    opcoes_formacao = [str(x) for x in df_mercado['Formacao_Topo'].dropna().unique() if str(x) != 'Não']
                    gl_formacao = st.multiselect("Passagem Formação Topo", options=sorted(opcoes_formacao), default=[])
                else:
                    gl_formacao = []
            with col_g5:
                if 'Internacional' in df_mercado.columns:
                    gl_internacional = st.multiselect("Historial Internacional", options=["Sim", "Não"], default=[])
                else:
                    gl_internacional = []
                    
            # APLICAR FILTROS GLOBAIS
            df_filtrado = df_mercado.copy()
            
            if gl_liga:
                df_filtrado = df_filtrado[df_filtrado['Divisao'].isin(gl_liga)]
            if gl_equipa:
                df_filtrado = df_filtrado[df_filtrado['Equipa'].isin(gl_equipa)]
            if gl_origem:
                df_filtrado = df_filtrado[df_filtrado['Divisão Simplificada'].isin(gl_origem)]
            if gl_formacao:
                df_filtrado = df_filtrado[df_filtrado['Formacao_Topo'].isin(gl_formacao)]
            if gl_internacional:
                if "Sim" in gl_internacional and "Não" not in gl_internacional:
                    df_filtrado = df_filtrado[df_filtrado['Internacional'] != 'Não']
                elif "Não" in gl_internacional and "Sim" not in gl_internacional:
                    df_filtrado = df_filtrado[df_filtrado['Internacional'] == 'Não']
                    
            st.markdown("---")
            
            # =======================================================
            # 📊 GRÁFICOS DE ORIGEM (COM CONTEXTO)
            # =======================================================
            st.markdown("### 📊 Gráficos de Origem (Contexto da Liga)")
            
            import plotly.express as px
            import pandas as pd
            
            dfs_to_plot = []
            
            # GRUPO 1: A Seleção
            if not df_filtrado.empty:
                df1 = df_filtrado.copy()
                if gl_equipa:
                    nome_grupo1 = "Clube(s) Selecionado(s)"
                elif gl_liga:
                    nome_grupo1 = "Liga(s) Selecionada(s)"
                else:
                    nome_grupo1 = "Média Nacional"
                    
                dfs_to_plot.append((nome_grupo1, df1))
            
            # GRUPO 2: O Contexto
            if gl_equipa:
                # Contexto são as Ligas dos clubes selecionados
                ligas_contexto = df_mercado[df_mercado['Equipa'].isin(gl_equipa)]['Divisao'].dropna().unique()
                df2 = df_mercado[df_mercado['Divisao'].isin(ligas_contexto)]
                dfs_to_plot.append(("Média da Liga", df2))
            elif gl_liga:
                # Contexto é o país todo
                df2 = df_mercado.copy()
                dfs_to_plot.append(("Média Nacional", df2))
            
            c_fig1, c_fig2 = st.columns(2)
            
            with c_fig1:
                st.markdown("**Origem Global do Plantel**")
                all_pie_data = []
                for nome_grupo, df_g in dfs_to_plot:
                    if not df_g.empty:
                        d = df_g['Origem_Analise'].value_counts(normalize=True).reset_index()
                        d.columns = ['Categoria', 'Percentagem']
                        d['Percentagem'] = d['Percentagem'] * 100
                        d['Grupo'] = nome_grupo
                        all_pie_data.append(d)
                
                if all_pie_data:
                    final_pie_data = pd.concat(all_pie_data)
                    fig1 = px.bar(final_pie_data, x='Percentagem', y='Categoria', color='Grupo', barmode='group', orientation='h',
                                  color_discrete_sequence=['#38bdf8', '#64748b'])
                    fig1.update_layout(
                        yaxis={'categoryorder':'total ascending'}, 
                        xaxis_title="Percentagem (%)",
                        yaxis_title="",
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)', 
                        font_color='white',
                        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        hoverlabel=dict(font_size=16)
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.warning("Sem dados para gerar gráfico.")
                    
            with c_fig2:
                st.markdown("**Origem por Liga / Divisão**")
                all_div_data = []
                for nome_grupo, df_g in dfs_to_plot:
                    if not df_g.empty:
                        d = df_g['Divisão Anterior'].value_counts(normalize=True).reset_index()
                        d.columns = ['Divisão', 'Percentagem']
                        d['Percentagem'] = d['Percentagem'] * 100
                        d['Divisão'] = d['Divisão'].apply(normalizar_nome_liga)
                        d = d.groupby('Divisão', as_index=False)['Percentagem'].sum()
                        d['Grupo'] = nome_grupo
                        all_div_data.append(d)
                
                if all_div_data:
                    final_div_data = pd.concat(all_div_data)
                    fig2 = px.bar(final_div_data, x='Percentagem', y='Divisão', color='Grupo', barmode='group', orientation='h',
                                  color_discrete_sequence=['#38bdf8', '#64748b'])
                    fig2.update_layout(
                        yaxis={'categoryorder':'total ascending'}, 
                        xaxis_title="Percentagem (%)",
                        yaxis_title="",
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)', 
                        font_color='white',
                        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        hoverlabel=dict(font_size=16)
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.warning("Sem dados para gerar gráfico.")
            
            # =======================================================
            # 📋 LISTA DE TRANSFERÊNCIAS
            # =======================================================
            st.markdown("### 📋 Lista de Transferências")
            if not df_filtrado.empty:
                cols_transf = ['Jogador', 'Equipa', 'Divisao', 'Clube_Anterior', 'Divisão Anterior', 'Tipo_Transferencia', 'Origem_Analise', 'Perfil Jogador']
                # Filtrar apenas as colunas que existem no dataframe
                cols_transf_validas = [col for col in cols_transf if col in df_filtrado.columns]
                df_transf_display = df_filtrado[cols_transf_validas].sort_values(by=['Clube_Anterior'])
                display_paginated_df(df_transf_display, "mercado_db", "transferencias.xlsx")
            else:
                st.warning("Sem dados de transferências para os filtros selecionados.")
                
            st.markdown("---")
            
            # =======================================================
            # 🌟 DESTAQUES DE TRANSFERÊNCIAS
            # =======================================================
            st.markdown("### 🌟 Destaques de Transferências")
            st.markdown("Jogadores (até 24 anos) transferidos com historial Internacional ou Formação em clubes da 1ª/2ª Liga.")
            
            if 'Internacional' in df_mercado.columns:
                destaques = df_filtrado.copy()
                
                # Filtrar apenas quem tem internacional ou formação (excluir os 'Não')
                destaques = destaques[(destaques['Internacional'] != 'Não') | (destaques['Formacao_Topo'] != 'Não')]
                
                if not destaques.empty:
                    # Selecionar e ordenar as colunas para apresentar
                    cols_destaque = ['Jogador', 'Equipa', 'Idade', 'Clube_Anterior', 'Internacional', 'Formacao_Topo', 'Perfil Jogador']
                    cols_dest_validas = [col for col in cols_destaque if col in destaques.columns]
                    destaques = destaques[cols_dest_validas].sort_values(by=['Equipa', 'Jogador'])
                    display_paginated_df(destaques, "destaques_db", "destaques.xlsx")
                else:
                    st.info("Nenhum jogador de destaque encontrado para os filtros selecionados.")
            else:
                st.info("Os dados de histórico ainda não foram extraídos. Corre a nova versão do bot!")
        else:
            st.info("Ainda não há dados de Clube Anterior na base de dados. Por favor, corre o atualizar_scouting.bat para recolher esta informação!")
