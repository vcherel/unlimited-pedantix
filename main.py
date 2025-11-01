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
    if 'full_text' not in st.session_state:
        st.session_state.full_text = ""
    if 'words' not in st.session_state:
        st.session_state.words = []
    if 'revealed' not in st.session_state:
        st.session_state.revealed = set()
    if 'guesses' not in st.session_state:
        st.session_state.guesses = []
    if 'model' not in st.session_state:
        st.session_state.model = None
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
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        'action': 'parse',
        'format': 'json',
        'page': title,
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
    
    # Remove unwanted elements but keep the structure
    for tag in soup.find_all(['style', 'script', 'sup']):
        tag.decompose()
    
    # Remove reference brackets like [1], [citation needed], etc.
    for tag in soup.find_all('a'):
        if tag.get('href', '').startswith('#cite'):
            tag.decompose()
    
    paragraphs = []
    for p in soup.find_all('p'):
        # Get text and clean it
        text = p.get_text()
        # Remove reference numbers in brackets
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[citation needed\]', '', text, flags=re.IGNORECASE)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > 50:  # Only substantial paragraphs
            paragraphs.append(text)
        
        if len(paragraphs) >= max_paragraphs:
            break
    
    result = ' '.join(paragraphs)
    return result

def normalize_word(word):
    """Normalize word for comparison (lowercase, remove accents)."""
    word = word.lower().strip()
    # Remove accents
    word = ''.join(c for c in unicodedata.normalize('NFD', word) 
                   if unicodedata.category(c) != 'Mn')
    return word

def tokenize_text(text):
    """Tokenize text into words with their positions."""
    # Split by word boundaries
    pattern = r'\b[\w\'-]+\b'
    words = []
    for match in re.finditer(pattern, text):
        word = match.group()
        if len(word) > 1 or word.isalpha():  # Keep single letters if alphabetic
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
    
    # Check if one contains the other (for plurals and variants)
    if len(guess_norm) >= 3 and len(target_norm) >= 3:
        # Simple plural handling (English and French)
        if guess_norm.endswith('s') and guess_norm[:-1] == target_norm:
            return True
        if target_norm.endswith('s') and target_norm[:-1] == guess_norm:
            return True
        if guess_norm.endswith('es') and guess_norm[:-2] == target_norm:
            return True
        if target_norm.endswith('es') and target_norm[:-2] == guess_norm:
            return True
        # French plurals
        if guess_norm.endswith('x') and guess_norm[:-1] == target_norm:
            return True
        if target_norm.endswith('x') and target_norm[:-1] == guess_norm:
            return True
    
    return False

def compute_similarity(guess, words, model):
    """Compute semantic similarity between guess and hidden words."""
    if not words or model is None:
        return []
    
    try:
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
        threshold = 0.4
        return [s for s in similarities[:3] if s['similarity'] > threshold]
    except Exception as e:
        st.error(f"Similarity computation error: {e}")
        return []

def load_game(language):
    """Load a new game with the selected language."""
    try:        
        # Fetch multiple random titles and get view counts
        candidates = []
        # TODO: make it parallel
        for i in range(5):
            try:
                title = fetch_random_title(language)
                print(f"Fetched random title {i+1}: {title}")
                views = fetch_page_views(language, title)
                print(f"Views for '{title}': {views}")
                candidates.append((title, views))
            except Exception as e:
                print(f"Error fetching candidate {i+1}: {e}")
                continue
        
        # Pick the most viewed article
        if not candidates:
            print("ERROR: No candidates found")
            st.session_state.article = None
            st.session_state.words = []
            return False
        
        best_title = max(candidates, key=lambda x: x[1])[0]
        print(f"Selected article: {best_title}")
        
        # Fetch full content
        article = fetch_wikipedia_content(best_title, language)
        print(f"Fetched article content, title: {article['title']}")
        
        text = extract_first_paragraphs(article['html'])
        print(f"Extracted text, length: {len(text)} chars")
        
        if not text or len(text) < 100:
            print(f"ERROR: Text too short: {len(text)} chars")
            st.session_state.article = None
            st.session_state.words = []
            return False
        
        # Load embedding model
        model = SentenceTransformer(MODELS[language])
        
        # Tokenize text
        words = tokenize_text(text)
        
        if not words:
            print("ERROR: No words tokenized")
            st.session_state.article = None
            st.session_state.words = []
            return False
        
        # Store in session state
        st.session_state.article = article
        st.session_state.full_text = text
        st.session_state.words = words
        st.session_state.revealed = set()
        st.session_state.guesses = []
        st.session_state.model = model
        st.session_state.game_won = False
        
        print("Game loaded successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Error loading game: {e}", exc_info=True)
        st.session_state.article = None
        st.session_state.words = []
        st.session_state.error_msg = str(e)
        return False

def display_text():
    """Display the text with revealed/hidden words."""
    if not st.session_state.words or not st.session_state.full_text:
        st.warning("No text to display")
        return
    
    text = st.session_state.full_text
    words = st.session_state.words
    revealed = st.session_state.revealed
    
    # Build HTML output
    html_parts = []
    last_pos = 0
    
    for word_info in words:
        # Add text before this word (spaces, punctuation)
        between = text[last_pos:word_info['start']]
        html_parts.append(between)
        
        # Add word (revealed or hidden)
        if word_info['normalized'] in revealed:
            html_parts.append(f"<span style='color: #27ae60; font-weight: bold;'>{word_info['text']}</span>")
        else:
            # Black box - display as inline block with fixed character
            word_length = len(word_info['text'])
            boxes = '█' * word_length  # Use block character
            html_parts.append(f"<span style='color: #34495e; background-color: #34495e; user-select: none;'>{boxes}</span>")
        
        last_pos = word_info['end']
    
    # Add remaining text
    html_parts.append(text[last_pos:])
    
    # Display with better styling
    full_html = ''.join(html_parts)
    st.markdown(f"""
    <div style='font-size: 1.1em; line-height: 2.0; padding: 20px; 
                background-color: #ecf0f1; border-radius: 10px; 
                font-family: Georgia, serif; white-space: pre-wrap;'>
        {full_html}
    </div>
    """, unsafe_allow_html=True)

def handle_guess(guess):
    """Process a guess."""
    if not guess or not guess.strip():
        return
    
    guess = guess.strip()
    st.session_state.guesses.append(guess)
    
    # Check if it's the title
    if normalize_word(guess) == normalize_word(st.session_state.article['title']):
        st.session_state.game_won = True
        # Reveal all words
        for word in st.session_state.words:
            st.session_state.revealed.add(word['normalized'])
        return
    
    # Check if word appears in text
    found = False
    for word_info in st.session_state.words:
        if words_match(guess, word_info['text']):
            st.session_state.revealed.add(word_info['normalized'])
            found = True
    
    if not found:
        # Check semantic similarity
        similar = compute_similarity(guess, st.session_state.words, st.session_state.model)
        if similar:
            st.session_state.last_similarity = similar[0]['similarity']
        else:
            st.session_state.last_similarity = 0

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
                with st.spinner("Loading game..."):
                    success = load_game('en')
                if not success:
                    st.error("Failed to load game. Please try again.")
                    st.session_state.language = None
                else:
                    st.rerun()
        with col2:
            if st.button("🇫🇷 Français", use_container_width=True):
                st.session_state.language = 'fr'
                with st.spinner("Loading game..."):
                    success = load_game('fr')
                if not success:
                    st.error("Failed to load game. Please try again.")
                    st.session_state.language = None
                else:
                    st.rerun()
        
        st.markdown("---")
        st.markdown("""
        ### How to Play:
        1. Choose your language (English or French)
        2. Guess words that appear in the hidden Wikipedia article
        3. If a word appears, all occurrences will be revealed in green
        4. If a word is semantically similar, you'll get similarity feedback
        5. Win by guessing the article's title!
        
        **Tip:** Press Enter to submit your guess!
        """)
        return
    
    # Game interface
    if st.session_state.article and st.session_state.words:
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
        st.markdown("### Article Text:")
        display_text()
        
        # Win condition
        if st.session_state.game_won:
            st.balloons()
            st.success(f"🎉 Congratulations! You found the article: **{st.session_state.article['title']}**")
            st.markdown(f"**Total guesses:** {len(st.session_state.guesses)}")
            st.markdown(f"[View on Wikipedia]({st.session_state.article['url']})")
            if st.button("Play Again"):
                st.session_state.language = None
                st.rerun()
            return
        
        # Guess input - with form for Enter key support
        st.markdown("---")
        st.markdown("### Make a Guess:")
        
        with st.form(key='guess_form', clear_on_submit=True):
            guess = st.text_input("Type a word and press Enter:", key="guess_input", label_visibility="collapsed")
            submitted = st.form_submit_button("Submit Guess", use_container_width=True)
            
            if submitted and guess:
                handle_guess(guess)
                st.rerun()
        
        # Feedback for last guess
        if st.session_state.guesses:
            last_guess = st.session_state.guesses[-1]
            
            # Check if last guess was found
            found = any(words_match(last_guess, w['text']) for w in st.session_state.words)
            
            if found:
                st.success(f"✅ Found '{last_guess}' in the text!")
            else:
                if hasattr(st.session_state, 'last_similarity') and st.session_state.last_similarity > 0:
                    st.info(f"🔍 '{last_guess}' is similar to hidden words (similarity: {st.session_state.last_similarity:.2%})")
                else:
                    st.warning(f"❌ '{last_guess}' not found")
        
        # Show guess history
        if st.session_state.guesses:
            with st.expander(f"Guess History ({len(st.session_state.guesses)} guesses)"):
                for i, g in enumerate(st.session_state.guesses, 1):
                    st.text(f"{i}. {g}")
        
        # New game buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Game (Same Language)", use_container_width=True):
                with st.spinner("Loading new game..."):
                    success = load_game(st.session_state.language)
                if success:
                    st.rerun()
                else:
                    st.error("Failed to load new game. Please try again.")
        with col2:
            if st.button("🌍 Change Language", use_container_width=True):
                st.session_state.language = None
                st.rerun()
    else:
        st.error("Failed to load game. Please select a language and try again.")
        if st.button("⬅️ Back to Language Selection"):
            st.session_state.language = None
            st.rerun()

if __name__ == "__main__":
    main()