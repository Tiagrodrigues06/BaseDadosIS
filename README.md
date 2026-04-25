# Scouting Pro - Streamlit Deploy

Esta pasta contém o mínimo essencial para publicar a aplicação gratuitamente no Streamlit Cloud.

### Como Publicar:
1. Cria um repositório gratuito no GitHub (por exemplo, "scouting-pro-app").
2. Faz o upload dos 3 ficheiros desta pasta para a raiz desse repositório:
   - `app.py`
   - `Competicao_Todas.xlsx`
   - `requirements.txt`
3. Acede a [https://share.streamlit.io/](https://share.streamlit.io/) e faz login com a tua conta do GitHub.
4. Clica no botão "New app" no canto superior direito.
5. Seleciona o repositório que criaste e certifica-te que o `Main file path` está como `app.py`.
6. Clica em "Deploy!" e a tua aplicação ficará pública.

### Dica:
Sempre que atualizares a base de dados `Competicao_Todas.xlsx` correndo o teu Scraper localmente, só precisas de arrastar e largar o ficheiro novo para dentro do teu repositório do GitHub (Replace). O Streamlit atualizará a app automaticamente em poucos minutos!
