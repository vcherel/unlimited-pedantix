from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, TYPE_CHECKING
import traceback
import fasttext
import numpy as np

from wiki_api import fetch_random_title, fetch_page_views, fetch_wikipedia_content, extract_first_paragraphs
from embedding_utils import embed_word, normalize_word, tokenize_text, words_match, compute_similarity
from classes import session_state
from config import NB_ARTICLES

if TYPE_CHECKING:
    from embedding_utils import SimilarityResult
    from classes import WikipediaPage


def fetch_candidate(language):
    """Fetch one wikipedia article and the views"""
    try:
        title = fetch_random_title(language)
        views = fetch_page_views(language, title)
        print(f"{title} -> {views}")
        return title, views
    
    except Exception as e:
        print(f"Error in load_game: {e}")
        traceback.print_exc()
        return False

def load_game(language):
    """Choose the wikipedia article for the game"""
    try:
        # We fetch NB_ARTICLES articles and keep the one with most view
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
        print(f"\n### {best_title} ###")

        # Extract the content
        article: WikipediaPage = fetch_wikipedia_content(best_title, language)
        article.text = extract_first_paragraphs(article.text)
        if not article.text:
            return False
        
        # Tokenize text
        print("Tokenizing text...")
        model = fasttext.load_model(f'models/cc.{language}.300.bin')
        article_words = tokenize_text(article.text, model)
        title_words = tokenize_text(article.title, model)
        print("Done.")
        
        # Update session parameters
        session_state.article = article
        session_state.article_words = article_words
        session_state.title_words = title_words
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
    guess = guess.strip().lower()
    if not guess:
        return

    session_state.guesses.append(guess)

    # Check if the guess matches any individual words
    for word_info in session_state.article_words:
        if words_match(guess, word_info.word):
            session_state.revealed.add(word_info.normalized)

    # Check similarities
    guess_vec = embed_word(normalize_word(guess), session_state.model)
    if np.all(guess_vec == 0):
        print(f"Warining: Zero word vector for guess: {guess}")

    similar_results: List[SimilarityResult] = compute_similarity(guess_vec, session_state.article_words)

    # Store the highest similarity for feedback
    session_state.last_similarity = similar_results[0].similarity if similar_results else 0
    
    # Update best guesses for similar words
    for result in similar_results:
        word_info = session_state.article_words[result.index]
        
        # If this guess is better than the current best, update it
        if result.similarity > word_info.best_similarity:
            word_info.best_guess = guess
            word_info.best_similarity = result.similarity
    
    # Check victory
    title_words = [w.lower() for w in session_state.article.title.split()]
    if all(w in session_state.revealed for w in title_words):
        session_state.game_won = True
        return
