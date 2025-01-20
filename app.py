import streamlit as st
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from scraper import scrape_approfondimenti
import pandas as pd
import feedparser
import pytz
import re
import requests
import json
import os
from dotenv import load_dotenv
from pathlib import Path

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Configurazione Perplexity API
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
if not PERPLEXITY_API_KEY:
    st.error("API key di Perplexity non trovata nel file .env")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# Page configuration
st.set_page_config(
    page_title="Dashboard Finanziaria",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_portfolio():
    """Carica il portfolio dal file JSON"""
    try:
        # Usa la directory .streamlit nella home directory dell'utente
        portfolio_file = Path.home() / ".streamlit" / "portfolio.json"
        portfolio_file.parent.mkdir(parents=True, exist_ok=True)
        if portfolio_file.exists():
            with open(portfolio_file, "r") as f:
                return json.load(f)
    except Exception as e:
        st.warning(f"Errore nel caricamento del portfolio: {str(e)}")
    return {}

def save_portfolio(portfolio_data):
    """Salva il portfolio nel file JSON"""
    try:
        # Usa la directory .streamlit nella home directory dell'utente
        portfolio_file = Path.home() / ".streamlit" / "portfolio.json"
        portfolio_file.parent.mkdir(parents=True, exist_ok=True)
        with open(portfolio_file, "w") as f:
            json.dump(portfolio_data, f)
    except Exception as e:
        st.warning(f"Errore nel salvataggio del portfolio: {str(e)}")

# Modifica l'inizializzazione del portfolio
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False

# Custom CSS for better readability
st.markdown("""
    <style>
    .big-font {
        font-size: 20px !important;
    }
    .stButton>button {
        height: 3em;
        padding: 0.5em 2em;
        font-size: 20px;
        margin: 1em 0;
    }
    .news-card {
        padding: 1.5em;
        border: 2px solid #ddd;
        border-radius: 8px;
        margin-bottom: 1.5em;
        background-color: #f8f9fa;
    }
    .news-source {
        color: #444;
        font-size: 0.9em;
        font-weight: bold;
    }
    .news-date {
        color: #444;
        font-size: 0.9em;
        float: right;
    }
    .stSelectbox label {
        font-size: 20px;
        color: #000000;
        font-weight: bold;
    }
    a {
        color: #1e88e5;
        text-decoration: none;
        font-size: 18px;
    }
    a:hover {
        text-decoration: underline;
    }
    /* Rimuovi padding extra e margini non necessari */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    /* Rimuovi la barra bianca */
    .css-18e3th9 {
        padding-top: 0rem;
        padding-bottom: 0rem;
    }
    /* Riduci lo spazio tra gli elementi */
    .css-1d391kg {
        padding-top: 1rem;
    }
    /* Stile per il titolo principale */
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1e88e5;
    }
    /* Stile per i filtri notizie */
    .news-filters {
        margin-bottom: 1rem;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# Stock symbols
STOCKS = {
    'Enel': 'ENEL.MI',
    'Unipolsai': 'UNI.MI',
    'Piaggio': 'PIA.MI',
    'A2A': 'A2A.MI',
    'Ascopiave': 'ASC.MI',
    'Banca Mediolanum': 'BMED.MI',
    'Generali': 'G.MI',
    'Intesa Sanpaolo': 'ISP.MI',
    'Telecom Italia': 'TIT.MI',
    'Italgas': 'IG.MI',
    'Mediobanca': 'MB.MI',
    'Snam': 'SRG.MI',
    'Terna': 'TRN.MI'
}

# Periodi disponibili per il grafico
PERIODS = {
    '📅 Ultimo Mese': '1mo',
    '📅 Ultimi 3 Mesi': '3mo',
    '📅 Ultimi 6 Mesi': '6mo',
    '📅 Ultimo Anno': '1y',
    '📅 Ultimi 2 Anni': '2y',
    '📅 Ultimi 5 Anni': '5y',
    '📅 Tutto lo Storico': 'max'
}

# News sources
NEWS_FEEDS = {
    'Soldionline': 'https://www.soldionline.it/rss/news.xml',
    'Milano Finanza': 'https://www.milanofinanza.it/rss/mercati',
    'Il Sole 24 Ore': 'https://www.ilsole24ore.com/rss/finanza-e-mercati.xml',
    'Teleborsa': 'https://www.teleborsa.it/feed/rss',
    'Investing.com': 'https://it.investing.com/rss/news.rss'
}

@st.cache_data(ttl=300)
def fetch_stock_data(symbol, period='1mo'):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        if hist.empty:
            return None
        return hist
    except Exception as e:
        st.error(f"Errore nel recupero dei dati per {symbol}: {str(e)}")
        return None

@st.cache_data(ttl=300)
def fetch_news():
    news_items = []
    
    # Fetch RSS feed news
    for source, url in NEWS_FEEDS.items():
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            feed = feedparser.parse(url, request_headers=headers)
            if not feed.entries:
                st.warning(f"Nessuna notizia disponibile da {source}")
                continue
                
            for entry in feed.entries[:10]:
                try:
                    dt = None
                    for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                        if hasattr(entry, date_field) and getattr(entry, date_field):
                            dt = datetime(*getattr(entry, date_field)[:6])
                            break
                    if dt is None:
                        dt = datetime.now()
                    dt = pytz.timezone('Europe/Rome').localize(dt)
                    
                    description = ''
                    if hasattr(entry, 'description'):
                        description = entry.description
                    elif hasattr(entry, 'summary'):
                        description = entry.summary
                    elif hasattr(entry, 'content'):
                        description = entry.content[0].value
                    
                    description = re.sub('<[^<]+?>', '', description)
                    description = re.sub(r'\s+', ' ', description)
                    description = description.strip()
                    
                    news_items.append({
                        'title': entry.title.strip(),
                        'link': entry.link,
                        'source': source,
                        'date': dt,
                        'description': description
                    })
                except Exception as e:
                    continue
        except Exception as e:
            continue
    
    # Fetch news from scraper.py
    try:
        scraped_news = scrape_approfondimenti()
        for news in scraped_news:
            news_items.append({
                'title': news['title'],
                'link': news['link'],
                'source': 'Soldionline',
                'date': datetime.now(pytz.timezone('Europe/Rome')),  # Make scraped news dates timezone-aware
                'description': ''
            })
    except Exception as e:
        st.warning(f"Errore nel recupero delle notizie da Soldionline: {str(e)}")
    
    # Sort and remove duplicates
    news_items.sort(key=lambda x: x['date'], reverse=True)
    seen_titles = set()
    unique_news = []
    for item in news_items:
        title_normalized = re.sub(r'\s+', ' ', item['title'].lower().strip())
        if title_normalized not in seen_titles:
            seen_titles.add(title_normalized)
            unique_news.append(item)
    
    return unique_news
def filter_news(news_items, filter_type, stocks):
    if filter_type == "Tutte le Notizie":
        return news_items
    
    filtered_news = []
    stock_names = [name.lower() for name in stocks]
    
    for item in news_items:
        title_lower = item['title'].lower()
        desc_lower = item['description'].lower()
        content = title_lower + " " + desc_lower
        
        if filter_type == "Economia Generale":
            keywords = [
                'economia', 'pil', 'inflazione', 'mercati', 'borsa', 'ftse', 'mib',
                'spread', 'btp', 'bund', 'bce', 'fed', 'tassi', 'rendimenti',
                'piazza affari', 'wall street', 'nasdaq', 'dow jones',
                'rating', 'moody\'s', 'standard & poor\'s', 'fitch',
                'treasury', 'obbligazioni', 'bond', 'titoli di stato'
            ]
            if any(keyword in content for keyword in keywords):
                filtered_news.append(item)
        else:  # Filtra per azione specifica
            stock_name = filter_type.lower()
            if stock_name in content:
                filtered_news.append(item)
    
    return filtered_news

def add_position(symbol, quantity, entry_price):
    if symbol not in st.session_state.portfolio:
        st.session_state.portfolio[symbol] = []
    st.session_state.portfolio[symbol].append({
        'quantity': quantity,
        'entry_price': entry_price,
        'date': datetime.now().strftime('%Y-%m-%d')
    })
    # Salva il portfolio dopo ogni aggiunta
    save_portfolio(st.session_state.portfolio)

def remove_position(symbol, index):
    if symbol in st.session_state.portfolio:
        st.session_state.portfolio[symbol].pop(index)
        if not st.session_state.portfolio[symbol]:
            del st.session_state.portfolio[symbol]
        # Salva il portfolio dopo ogni rimozione
        save_portfolio(st.session_state.portfolio)

def calculate_position_value(symbol, current_price):
    if symbol not in st.session_state.portfolio:
        return 0, 0, 0
    
    total_quantity = sum(pos['quantity'] for pos in st.session_state.portfolio[symbol])
    total_cost = sum(pos['quantity'] * pos['entry_price'] for pos in st.session_state.portfolio[symbol])
    current_value = total_quantity * current_price
    profit_loss = current_value - total_cost
    profit_loss_pct = (profit_loss / total_cost * 100) if total_cost > 0 else 0
    
    return total_quantity, profit_loss, profit_loss_pct

def create_stock_chart(data, title, portfolio_positions=None):
    if data is None or data.empty:
        return None
        
    fig = go.Figure()
    
    # Aggiungi il grafico candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Prezzo'
    ))
    
    # Se ci sono posizioni nel portfolio, aggiungile come punti
    if portfolio_positions:
        entry_prices = []
        entry_dates = []
        quantities = []
        for pos in portfolio_positions:
            entry_prices.append(pos['entry_price'])
            entry_dates.append(pos['date'])
            quantities.append(pos['quantity'])
        
        # Aggiungi i punti di entrata
        fig.add_trace(go.Scatter(
            x=entry_dates,
            y=entry_prices,
            mode='markers',
            marker=dict(
                size=[min(q * 2, 20) for q in quantities],  # Dimensione proporzionale alla quantità
                color='green',
                symbol='star'
            ),
            name='Posizioni Portfolio'
        ))
    
    fig.update_layout(
        title=title,
        yaxis_title='Prezzo',
        xaxis_title='Data',
        height=400,
        template='plotly_white',
        font=dict(size=14)
    )
    
    return fig

def get_stock_info(symbol):
    """Recupera informazioni aggiuntive sullo stock"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'forward_pe': info.get('forwardPE', 0),
            'market_cap': info.get('marketCap', 0),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A')
        }
    except:
        return None

def get_perplexity_research(query, api_key=PERPLEXITY_API_KEY):
    """Esegue una ricerca usando l'API di Perplexity"""
    if not api_key:
        return {"error": "API key non configurata"}
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {
                "role": "system",
                "content": "Sei un analista finanziario esperto. Fornisci analisi dettagliate ma concise sulle aziende, includendo dati finanziari chiave, prospettive di mercato e potenziali rischi/opportunità."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500,
        "return_citations": True
    }
    
    try:
        response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Main layout
st.markdown('<h1 class="main-title">📊 Dashboard Finanziaria</h1>', unsafe_allow_html=True)

# Tabs per la navigazione
tab_main, tab_portfolio, tab_analysis = st.tabs(["📈 Dashboard", "💼 Portfolio", "🔍 Analisi"])

with tab_main:
    # Create two columns for main dashboard
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<h2>📈 Andamento Azioni</h2>', unsafe_allow_html=True)
        
        # Selezione periodo come semplice dropdown
        selected_period = st.selectbox(
            'Periodo:',
            list(PERIODS.keys()),
            index=0
        )
        
        for name, symbol in STOCKS.items():
            data = fetch_stock_data(symbol, PERIODS[selected_period])
            if data is not None and not data.empty and len(data) > 0:
                try:
                    current_price = data['Close'].iloc[-1]
                    prev_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
                    price_change = ((current_price - prev_price) / prev_price) * 100
                    
                    st.markdown(f"<h3>{name}</h3>", unsafe_allow_html=True)
                    col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
                    with col_metrics1:
                        st.metric("Prezzo Attuale", f"€{current_price:.2f}")
                    with col_metrics2:
                        st.metric("Variazione %", f"{price_change:.2f}%")
                    with col_metrics3:
                        st.metric("Volume", f"{data['Volume'].iloc[-1]:,.0f}")
                    with col_metrics4:
                        # Ottieni il rendimento del dividendo
                        stock_info = get_stock_info(symbol)
                        dividend_yield = stock_info['dividend_yield'] if stock_info else 0
                        st.metric("Dividendo in %", f"{dividend_yield:.2f}%")
                    
                    # Passa le posizioni del portfolio al grafico se esistono
                    portfolio_positions = st.session_state.portfolio.get(name, [])
                    fig = create_stock_chart(data, name, portfolio_positions)
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Errore nell'elaborazione dei dati per {name}: {str(e)}")
            else:
                st.warning(f"Nessun dato disponibile per {name} ({symbol})")
    
    with col2:
        st.markdown('<h2>📰 Ultime Notizie</h2>', unsafe_allow_html=True)
        
        # Filtri per le notizie
        filter_options = ["Tutte le Notizie", "Economia Generale"] + list(STOCKS.keys())
        news_filter = st.selectbox("Filtra notizie per:", filter_options)
        
        news_items = fetch_news()
        filtered_news = filter_news(news_items, news_filter, STOCKS.keys())
        
        if filtered_news:
            for item in filtered_news:
                st.markdown(f"""
                <div class="news-card">
                    <a href="{item['link']}" target="_blank">{item['title']}</a>
                    <div>
                        <span class="news-source">{item['source']}</span>
                        <span class="news-date">{item['date'].strftime('%d/%m/%Y %H:%M')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"Nessuna notizia disponibile per il filtro selezionato: {news_filter}")

with tab_portfolio:
    st.markdown('<h2>💼 Gestione Portfolio</h2>', unsafe_allow_html=True)
    
    # Toggle per la modalità di modifica
    edit_mode = st.toggle('Modalità Modifica', value=st.session_state.edit_mode)
    st.session_state.edit_mode = edit_mode
    
    col_portfolio_left, col_portfolio_right = st.columns([1, 1])
    
    with col_portfolio_left:
        if edit_mode:
            st.markdown("### Aggiungi Posizione")
            with st.form("add_position_form"):
                selected_stock = st.selectbox("Seleziona Asset", list(STOCKS.keys()))
                quantity = st.number_input("Quantità", min_value=0.0, step=0.01)
                entry_price = st.number_input("Prezzo di Acquisto (€)", min_value=0.0, step=0.01)
                
                if st.form_submit_button("Aggiungi al Portfolio"):
                    add_position(selected_stock, quantity, entry_price)
                    st.success(f"Posizione aggiunta per {selected_stock}")
        
        # Visualizza il portfolio
        st.markdown("### Posizioni Attuali")
        total_portfolio_value = 0
        total_portfolio_cost = 0
        
        for stock_name, positions in st.session_state.portfolio.items():
            if not positions:
                continue
            
            st.markdown(f"**{stock_name}**")
            data = fetch_stock_data(STOCKS[stock_name], '1mo')
            if data is not None and not data.empty:
                current_price = data['Close'].iloc[-1]
                total_quantity, profit_loss, profit_loss_pct = calculate_position_value(stock_name, current_price)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Quantità Totale", f"{total_quantity:.2f}")
                with col2:
                    st.metric("P/L", f"€{profit_loss:.2f}")
                with col3:
                    st.metric("P/L %", f"{profit_loss_pct:.2f}%")
                
                if edit_mode:
                    for idx, pos in enumerate(positions):
                        st.markdown(f"Posizione {idx + 1}: {pos['quantity']} @ €{pos['entry_price']:.2f}")
                        if st.button(f"Rimuovi Posizione {idx + 1}", key=f"remove_{stock_name}_{idx}"):
                            remove_position(stock_name, idx)
                            st.rerun()
                
                # Aggiorna i totali
                position_value = total_quantity * current_price
                position_cost = sum(pos['quantity'] * pos['entry_price'] for pos in positions)
                total_portfolio_value += position_value
                total_portfolio_cost += position_cost
    
    with col_portfolio_right:
        # Mostra il riepilogo del portfolio
        st.markdown("### Riepilogo Portfolio")
        total_pl = total_portfolio_value - total_portfolio_cost
        total_pl_pct = (total_pl / total_portfolio_cost * 100) if total_portfolio_cost > 0 else 0
        
        st.metric("Valore Totale Portfolio", f"€{total_portfolio_value:,.2f}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("P/L Totale", f"€{total_pl:,.2f}")
        with col2:
            st.metric("P/L % Totale", f"{total_pl_pct:.2f}%")
        
        # Grafico composizione portfolio
        if st.session_state.portfolio:
            st.markdown("### Composizione Portfolio")
            portfolio_data = []
            for stock_name, positions in st.session_state.portfolio.items():
                if positions:
                    data = fetch_stock_data(STOCKS[stock_name], '1mo')
                    if data is not None and not data.empty:
                        current_price = data['Close'].iloc[-1]
                        total_quantity = sum(pos['quantity'] for pos in positions)
                        value = total_quantity * current_price
                        portfolio_data.append({
                            'Asset': stock_name,
                            'Valore': value
                        })
            
            if portfolio_data:
                df = pd.DataFrame(portfolio_data)
                fig = px.pie(df, values='Valore', names='Asset', title='Composizione Portfolio')
                st.plotly_chart(fig, use_container_width=True)

with tab_analysis:
    st.markdown('<h2>🔍 Analisi Approfondita</h2>', unsafe_allow_html=True)
    
    # Selezione dell'azienda per l'analisi
    selected_company = st.selectbox(
        "Seleziona un'azienda per l'analisi:",
        list(STOCKS.keys())
    )
    
    # Recupera informazioni sul rendimento
    stock_info = get_stock_info(STOCKS[selected_company])
    if stock_info:
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("Rendimento Dividendo", f"{stock_info['dividend_yield']:.2f}%")
        with col_info2:
            st.metric("P/E Forward", f"{stock_info['forward_pe']:.2f}")
        with col_info3:
            st.metric("Capitalizzazione", f"€{stock_info['market_cap']:,.0f}")
        
        st.markdown(f"""
        **Settore:** {stock_info['sector']}  
        **Industria:** {stock_info['industry']}
        """)
    
    # Campo di ricerca personalizzato
    custom_query = st.text_input(
        "Inserisci una domanda specifica (opzionale):",
        placeholder=f"Es: Quali sono le prospettive di crescita per {selected_company}?"
    )
    
    if st.button("🔍 Analizza"):
        with st.spinner("Ricerca in corso..."):
            # Prepara la query
            if custom_query:
                query = f"{custom_query} per {selected_company}"
            else:
                query = f"Fornisci un'analisi dettagliata di {selected_company}, includendo performance recente, strategie aziendali e prospettive future."
            
            # Esegui la ricerca
            research = get_perplexity_research(query)
            
            if "error" in research:
                st.error(f"Errore nella ricerca: {research['error']}")
            else:
                # Mostra il risultato
                st.markdown("### Risultati dell'Analisi")
                st.markdown(research['choices'][0]['message']['content'])
                
                # Mostra le citazioni
                if 'citations' in research and research['citations']:
                    st.markdown("### Fonti")
                    for citation in research['citations']:
                        st.markdown(f"- [{citation}]({citation})")

# Add auto-refresh button
if st.button("🔄 Aggiorna Dati", key="refresh"):
    st.experimental_rerun() 