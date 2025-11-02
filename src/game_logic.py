from concurrent.futures import ThreadPoolExecutor, as_completed
import fasttext

from wiki_api import fetch_random_title, fetch_page_views, fetch_wikipedia_content, extract_first_paragraphs
from text_utils import tokenize_text, words_match, compute_similarity
from session_state import session_state


def fetch_candidate(language):
    try:
        title = fetch_random_title(language)
        views = fetch_page_views(language, title)
        return title, views
    except:
        return None

def load_game(language):
    try:
        candidates = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_candidate, language) for _ in range(5)]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    candidates.append(result)
        if not candidates:
            return False
        best_title = max(candidates, key=lambda x: x[1])[0]
        article = fetch_wikipedia_content(best_title, language)
        text = extract_first_paragraphs(article['html'])
        if not text or len(text) < 100:
            return False
        model = fasttext.load_model(f'models/cc.{language}.300.bin')
        words = tokenize_text(text)
        if not words:
            return False
        session_state.article = article
        session_state.full_text = text
        session_state.words = words
        session_state.revealed = set()
        session_state.guesses = []
        session_state.model = model
        session_state.game_won = False
        return True
    except:
        return False

def handle_guess(guess: str):
    guess = guess.strip()
    if not guess:
        return
    session_state.guesses.append(guess)
    if guess.lower() == session_state.article['title'].lower():
        session_state.game_won = True
        session_state.revealed.update(w['normalized'] for w in session_state.words)
        return
    found = False
    for word_info in session_state.words:
        if words_match(guess, word_info['text']):
            session_state.revealed.add(word_info['normalized'])
            found = True
    if not found and session_state.model:
        similar = compute_similarity(guess, session_state.words, session_state.model)
        session_state.last_similarity = similar[0]['similarity'] if similar else 0
