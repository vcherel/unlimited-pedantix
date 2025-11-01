import streamlit as st
import requests
from urllib.parse import quote
import re
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import unicodedata


# Configuration
MODELS = {
    'en': 'all-MiniLM-L6-v2',
    'fr': 'distiluse-base-multilingual-cased-v1'
}

def initialize_session_state():
    """Initialize all session state variables."""
    if 'language' not in st.session_state:
        st.session_state.language = None
    if 'article' not in st.session_state:
        st.session_state.article = None
    if 'words' not in st.session_state:
        st.session_state.words = []
    if 'revealed' not in st.session_state:
        st.session_state.revealed = set()
    if 'guesses' not in st.session_state:
        st.session_state.guesses = []
    if 'model' not in st.session_state:
        st.session_state.model = None
    if 'embeddings' not in st.session_state:
        st.session_state.embeddings = None
    if 'game_won' not in st.session_state:
        st.session_state.game_won = False

def fetch_random_title(language):
    """Fetch a random Wikipedia page title."""
    url = f"https://{language}.wikipedia.org/api/rest_v1/page/random/summary"
    headers = {"User-Agent": "PedantixGame/1.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['title']

def fetch_page_views(language, title):
    """Fetch page views for the last 30 days."""
    try:
        encoded_title = quote(title)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{language}.wikipedia/all-access/all-agents/{encoded_title}/daily/{start_str}/{end_str}"
        headers = {"User-Agent": "PedantixGame/1.0"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            return sum(item.get('views', 0) for item in items)
        return 0
    except:
        return 0

def fetch_wikipedia_content(title, language):
    """Fetch Wikipedia page content."""
    encoded_title = quote(title)
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        'action': 'parse',
        'format': 'json',
        'page': encoded_title,
        'prop': 'text',
        'redirects': 1
    }
    headers = {"User-Agent": "PedantixGame/1.0"}
    
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    if 'error' in data:
        raise Exception(f"Page not found: {data['error']['info']}")
    
    parse_obj = data['parse']
    actual_title = parse_obj['title']
    html_content = parse_obj['text']['*']
    
    return {
        'title': actual_title,
        'html': html_content,
        'url': f"https://{language}.wikipedia.org/wiki/{quote(actual_title)}"
    }

def extract_first_paragraphs(html_content, max_paragraphs=3):
    """Extract first few paragraphs from Wikipedia HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for tag in soup.find_all(['style', 'script', 'sup', 'table', 'div']):
        tag.decompose()
    
    paragraphs = []
    for p in soup.find_all('p'):
        text = p.get_text().strip()
        if len(text) > 50:  # Only substantial paragraphs
            paragraphs.append(text)
        if len(paragraphs) >= max_paragraphs:
            break
    
    return ' '.join(paragraphs)

def normalize_word(word):
    """Normalize word for comparison (lowercase, remove accents)."""
    word = word.lower().strip()
    # Remove accents
    word = ''.join(c for c in unicodedata.normalize('NFD', word) 
                   if unicodedata.category(c) != 'Mn')
    return word

def tokenize_text(text):
    """Tokenize text into words with their positions."""
    # Split by whitespace and punctuation while keeping structure
    pattern = r'\b\w+\b'
    words = []
    for match in re.finditer(pattern, text):
        word = match.group()
        if len(word) > 1:  # Ignore single characters
            words.append({
                'text': word,
                'normalized': normalize_word(word),
                'start': match.start(),
                'end': match.end()
            })
    return words

def words_match(guess, target):
    """Check if guess matches target (handles plurals, variants)."""
    guess_norm = normalize_word(guess)
    target_norm = normalize_word(target)
    
    # Exact match
    if guess_norm == target_norm:
        return True
    
    # Simple plural handling (English and French)
    if guess_norm + 's' == target_norm or target_norm + 's' == guess_norm:
        return True
    if guess_norm + 'x' == target_norm or target_norm + 'x' == guess_norm:
        return True
    if guess_norm + 'es' == target_norm or target_norm + 'es' == guess_norm:
        return True
    
    return False

def compute_similarity(guess, words, model):
    """Compute semantic similarity between guess and hidden words."""
    if not words or model is None:
        return []
    
    guess_embedding = model.encode([guess])[0]
    similarities = []
    
    for word_info in words:
        if word_info['normalized'] not in st.session_state.revealed:
            word_embedding = model.encode([word_info['text']])[0]
            similarity = np.dot(guess_embedding, word_embedding) / (
                np.linalg.norm(guess_embedding) * np.linalg.norm(word_embedding)
            )
            similarities.append({
                'word': word_info['text'],
                'similarity': float(similarity),
                'index': words.index(word_info)
            })
    
    # Return top 3 most similar words above threshold
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    threshold = 0.5
    return [s for s in similarities[:3] if s['similarity'] > threshold]

def load_game(language):
    """Load a new game with the selected language."""
    with st.spinner(f"Loading game in {language.upper()}..."):
        # Fetch multiple random titles and get view counts
        candidates = []
        for _ in range(5):
            try:
                title = fetch_random_title(language)
                views = fetch_page_views(language, title)
                candidates.append((title, views))
            except:
                continue
        
        # Pick the most viewed article
        if not candidates:
            st.error("Failed to fetch articles. Please try again.")
            return
        
        best_title = max(candidates, key=lambda x: x[1])[0]
        
        # Fetch full content
        article = fetch_wikipedia_content(best_title, language)
        text = extract_first_paragraphs(article['html'])
        
        # Load embedding model
        model = SentenceTransformer(MODELS[language])
        
        # Tokenize text
        words = tokenize_text(text)
        
        # Store in session state
        st.session_state.article = article
        st.session_state.full_text = text
        st.session_state.words = words
        st.session_state.revealed = set()
        st.session_state.guesses = []
        st.session_state.model = model
        st.session_state.game_won = False

def display_text():
    """Display the text with revealed/hidden words."""
    if not st.session_state.words:
        return
    
    text = st.session_state.full_text
    words = st.session_state.words
    revealed = st.session_state.revealed
    
    # Build HTML output
    html_parts = []
    last_pos = 0
    
    for word_info in words:
        # Add text before this word
        html_parts.append(text[last_pos:word_info['start']])
        
        # Add word (revealed or hidden)
        if word_info['normalized'] in revealed:
            html_parts.append(f"<span style='color: #2ecc71; font-weight: bold;'>{word_info['text']}</span>")
        else:
            # Black box with same width
            box_width = len(word_info['text']) * 0.6
            html_parts.append(f"<span style='display: inline-block; width: {box_width}em; height: 1.2em; background-color: #2c3e50; vertical-align: middle; margin: 0 2px;'></span>")
        
        last_pos = word_info['end']
    
    # Add remaining text
    html_parts.append(text[last_pos:])
    
    # Display
    st.markdown(f"<div style='font-size: 1.1em; line-height: 1.8; padding: 20px; background-color: #f8f9fa; border-radius: 10px;'>{''.join(html_parts)}</div>", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Pedantix Game", page_icon="🎮", layout="wide")
    
    initialize_session_state()
    
    st.title("🎮 Pedantix - Wikipedia Guessing Game")
    
    # Language selection
    if st.session_state.language is None:
        st.markdown("### Choose your language:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🇬🇧 English", use_container_width=True):
                st.session_state.language = 'en'
                load_game('en')
                st.rerun()
        with col2:
            if st.button("🇫🇷 Français", use_container_width=True):
                st.session_state.language = 'fr'
                load_game('fr')
                st.rerun()
        return
    
    # Game interface
    if st.session_state.article:
        # Header with stats
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### Language: {st.session_state.language.upper()}")
        with col2:
            st.metric("Guesses", len(st.session_state.guesses))
        with col3:
            revealed_count = len(st.session_state.revealed)
            total_unique = len(set(w['normalized'] for w in st.session_state.words))
            st.metric("Revealed", f"{revealed_count}/{total_unique}")
        
        # Display text
        display_text()
        
        # Win condition
        if st.session_state.game_won:
            st.success(f"🎉 Congratulations! You found the article: **{st.session_state.article['title']}**")
            st.markdown(f"[View on Wikipedia]({st.session_state.article['url']})")
            if st.button("Play Again"):
                st.session_state.language = None
                st.rerun()
            return
        
        # Guess input
        st.markdown("---")
        guess = st.text_input("Enter your guess:", key="guess_input")
        
        if st.button("Submit Guess") and guess:
            guess = guess.strip()
            if guess:
                st.session_state.guesses.append(guess)
                
                # Check if it's the title
                if normalize_word(guess) == normalize_word(st.session_state.article['title']):
                    st.session_state.game_won = True
                    # Reveal all words
                    for word in st.session_state.words:
                        st.session_state.revealed.add(word['normalized'])
                    st.rerun()
                
                # Check if word appears in text
                found = False
                for word_info in st.session_state.words:
                    if words_match(guess, word_info['text']):
                        st.session_state.revealed.add(word_info['normalized'])
                        found = True
                
                if found:
                    st.success(f"✅ Found '{guess}' in the text!")
                else:
                    # Check semantic similarity
                    similar = compute_similarity(guess, st.session_state.words, st.session_state.model)
                    if similar:
                        st.info(f"🔍 '{guess}' is semantically similar to some hidden words (similarity: {similar[0]['similarity']:.2f})")
                    else:
                        st.warning(f"❌ '{guess}' not found and not similar to any words")
                
                st.rerun()
        
        # Show guess history
        if st.session_state.guesses:
            with st.expander("Guess History"):
                for i, g in enumerate(reversed(st.session_state.guesses), 1):
                    st.text(f"{len(st.session_state.guesses) - i + 1}. {g}")
        
        # New game button
        st.markdown("---")
        if st.button("New Game"):
            load_game(st.session_state.language)
            st.rerun()
        
        if st.button("Change Language"):
            st.session_state.language = None
            st.rerun()

if __name__ == "__main__":
    main()