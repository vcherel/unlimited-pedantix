from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, TYPE_CHECKING
import traceback
import fasttext

from wiki_api import fetch_random_title, fetch_page_views, fetch_wikipedia_content, extract_first_paragraphs
from text_utils import tokenize_text, words_match, compute_similarity
from classes import session_state
from config import NB_ARTICLES

if TYPE_CHECKING:
    from text_utils import SimilarityResult


def fetch_candidate(language):
    try:
        title = fetch_random_title(language)
        views = fetch_page_views(language, title)
        return title, views
    except Exception as e:
        print(f"Error in load_game: {e}")
        traceback.print_exc()
        return False

def load_game(language):
    try:
        candidates = []
        with ThreadPoolExecutor(max_workers=NB_ARTICLES) as executor:
            futures = [executor.submit(fetch_candidate, language) for _ in range(NB_ARTICLES)]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    candidates.append(result)
        if not candidates:
            return False
        best_title = max(candidates, key=lambda x: x[1])[0]
        article = fetch_wikipedia_content(best_title, language)
        # TODO: make article class
        text = extract_first_paragraphs(article['html'])
        if not text or len(text) < 100:
            return False
        model = fasttext.load_model(f'models/cc.{language}.300.bin')
        words = tokenize_text(text, model)
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
    except Exception as e:
        print(f"Error in load_game: {e}")
        traceback.print_exc()
        return False

def handle_guess(guess: str):
    """Handle one word guess"""
    guess = guess.strip()
    if not guess:
        return

    session_state.guesses.append(guess)

    # Check if the guess matches the article title
    # TODO: all the words from title must be found to reveal
    if guess.lower() == session_state.article['title'].lower():
        session_state.game_won = True
        # Reveal all words since the game is won
        session_state.revealed.update(w.normalized for w in session_state.words)
        return

    # Check if the guess matches any individual words
    found = False
    for word_info in session_state.words:
        if words_match(guess, word_info.text):
            session_state.revealed.add(word_info.normalized)
            found = True

    # If no exact match, compute similarity (if model is available)
    if not found and session_state.model:
        similar_results: List[SimilarityResult] = compute_similarity(guess, session_state.words, session_state.model)
        # Store the highest similarity for feedback
        # TODO: all the similar words should be replaced with the similar word
        session_state.last_similarity = similar_results[0].similarity if similar_results else 0
