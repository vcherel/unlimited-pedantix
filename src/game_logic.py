from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, TYPE_CHECKING
import numpy as np
import traceback
import fasttext
import difflib
import math
import time

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
        return title, views
    
    except Exception as e:
        print(f"Error in load_game: {e}")
        traceback.print_exc()
        return False

def load_game(language, update_spinner_func):
    """Choose the wikipedia article for the game"""
    try:
        update_spinner_func("Choix de l'article en cours...")
        time.sleep(0.2)
        
        candidates = []
        with ThreadPoolExecutor(max_workers=NB_ARTICLES) as executor:
            futures = [executor.submit(fetch_candidate, language) for _ in range(NB_ARTICLES)]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    candidates.append(result)
        
        if not candidates:
            return False
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Print top 5 articles and their views
        print("\nTop 5 articles by views:")
        for title, views in candidates[:5]:
            print(f"  {title}: {views} views")
        
        best_title = candidates[0][0]
        print(f"\n~~~~ {best_title} ~~~~")
        
        update_spinner_func(f"Récupération de l'article...")
        time.sleep(0.2)
        
        article: WikipediaPage = fetch_wikipedia_content(best_title, language)
        article.text = extract_first_paragraphs(article.text)
        
        if not article.text:
            return False
        
        update_spinner_func("Préparation de l'IA tueuse...")
        time.sleep(0.2)
        
        model = fasttext.load_model(f'models/cc.{language}.300.bin')
        article_words = tokenize_text(article.text, model)
        title_words = tokenize_text(article.title, model)
        
        update_spinner_func("Finito !")
        time.sleep(0.2)
        
        session_state.article = article
        session_state.article_words = article_words
        session_state.title_words = title_words
        session_state.revealed = set()
        session_state.revealed_end = set()
        session_state.guesses = []
        session_state.feedback_content = "💡 Tapez un mot dans la barre !"
        session_state.feedback_color = "555"
        session_state.model = model
        session_state.game_won = False

        
        return True
    except Exception as e:
        print(f"Error in load_game: {e}")
        traceback.print_exc()
        return False
    
def numeric_similarity(a: float, b: float, sigma: float = 5.0) -> float:
    """
    Compute a smooth similarity between two numbers.
    """
    return math.exp(-((a - b) ** 2) / (2 * sigma ** 2))

def process_guess(guess):
    """Logic to handle a guess including feedback and suggestions"""
    handle_guess(guess)

    found_count = sum(1 for w in session_state.article_words if words_match(guess, w.word))
    updated_count = sum(1 for w in session_state.article_words if getattr(w, "best_guess", "") == guess)

    # Suggest close word if not found
    if found_count == 0 and updated_count == 0:
        print(guess, type(session_state.all_words))
        close_matches = difflib.get_close_matches(guess, session_state.all_words, n=1, cutoff=0.7)
        close_word = close_matches[0] if close_matches else None    
        if close_word and close_word != guess:
            # Automatically handle the corrected guess
            handle_guess(close_word)
            session_state.guess_input = ""  # Clear input after correction
            return f"❌ '{guess}' not found, did you mean '{close_word}'?", "red", close_word
        else:
            return f"❌ '{guess}' not found", "red", ""

    # Provide normal feedback
    if found_count > 0:
        return f"✅ '{guess}': {'🟩'*found_count}{'🟧'*updated_count}", "green", ""
    else:
        return f"🟠 '{guess}': {'🟧'*updated_count}", "orange", ""

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

    for word_info in session_state.title_words:
        if words_match(guess, word_info.word):
            session_state.revealed.add(word_info.normalized)

    if guess.isdigit():
        guess_num = float(guess)
        max_similarity = 0.0
        for word_info in session_state.article_words:
            if word_info.word.isdigit():
                word_num = float(word_info.word)
                similarity = numeric_similarity(guess_num, word_num, sigma=5.0)
                if similarity > word_info.best_similarity:
                    word_info.best_guess = guess
                    word_info.best_similarity = similarity
                max_similarity = max(max_similarity, similarity)
    else:
        # Existing embedding-based logic
        guess_vec = embed_word(normalize_word(guess), session_state.model)
        if np.all(guess_vec == 0):
            print(f"Warning: Zero word vector for guess: {guess}")

        similar_results: List[SimilarityResult] = compute_similarity(guess_vec, session_state.article_words)

        for result in similar_results:
            word_info = session_state.article_words[result.index]
            if result.similarity > word_info.best_similarity:
                word_info.best_guess = guess
                word_info.best_similarity = result.similarity

    # Check victory
    if all(w in session_state.revealed for w in [w.normalized for w in session_state.title_words]):
        session_state.game_won = True
