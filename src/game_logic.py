from __future__ import annotations

import os
from typing import List, TYPE_CHECKING
import compress_fasttext.models
import numpy as np
import traceback
import difflib
import asyncio
import aiohttp
import time
import math
import re

import requests

from wiki_api import fetch_random_title, fetch_page_views, fetch_wikipedia_content, extract_first_paragraphs
from embedding_utils import embed_word, normalize_word, tokenize_text, words_match, compute_similarity
from config import NB_ARTICLES

if TYPE_CHECKING:
    from embedding_utils import SimilarityResult
    from classes import WikipediaPage, SessionState


async def fetch_candidate(session: aiohttp.ClientSession, language: str) -> tuple[str, int] | None:
    """Asynchronously fetch one wikipedia article title and its views."""
    try:
        title = await fetch_random_title(session, language)
        views = await fetch_page_views(session, language, title)
        
        if views > 0:
            return title, views
        return None
    except aiohttp.ClientError as e:
        print(f"Client error for a candidate: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error for a candidate: {e}")
        traceback.print_exc()
        return None

async def load_game(language, update_spinner_func, session_state: SessionState):
    """Choose the wikipedia article for the game"""
    try:
        update_spinner_func("Choix de l'article en cours...")
        time.sleep(0.2)
        
        # Use a single session for all requests for connection pooling
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_candidate(session, language) for _ in range(NB_ARTICLES)]
            
            # Run all tasks in parallel
            results = await asyncio.gather(*tasks)
            
            # Filter out failed/None results
            candidates = [result for result in results if result is not None]

        if not candidates:
            print("No candidates were successfully fetched.")
            return []
        
        # Sort the results by view count
        candidates.sort(key=lambda x: x[1], reverse=True)
        
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
        
        model_path = f'models/fasttext-{language}-mini'
        os.makedirs('models', exist_ok=True)

        # Check if model file exists
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}. Downloading...")
            url = f'https://zenodo.org/records/4905385/files/fasttext-{language}-mini?download=1'
            response = requests.get(url)
            with open(model_path, 'wb') as f:
                f.write(response.content)
            print("Download complete.")

        # Load the model
        model = compress_fasttext.models.CompressedFastTextKeyedVectors.load(f'models/fasttext-{language}-mini')
        article_words = tokenize_text(article.text, model)
        title_words = tokenize_text(article.title, model)
        
        update_spinner_func("Finito !")
        time.sleep(0.2)

        session_state.language = language
        with open(f"data/words_{session_state.language}.txt", encoding="utf-8") as f:
            session_state.all_words = [line.strip() for line in f]
        
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
    """Compute a smooth similarity between two numbers"""
    return math.exp(-((a - b) ** 2) / (2 * sigma ** 2))

def process_guess(guess: str, session_state: SessionState):
    """Logic to handle a guess including feedback and suggestions"""
    guess = guess.strip().lower()
    if not guess:
        return

    # Check for repeated guess
    if normalize_word(guess) in session_state.guesses:
        repeated = f"'<b>{guess}</b>' a déjà été proposé", "orange"
    else:
        repeated = None

    handle_guess(guess, session_state)

    if repeated:
        return repeated

    found_count = sum(1 for w in session_state.article_words if words_match(guess, w.word))
    updated_count = sum(1 for w in session_state.article_words if w.best_guess == guess)

    # Suggest close word if not found
    if found_count == 0 and updated_count == 0:
        if re.fullmatch(r"\d+", guess.strip()):
            return f"'<b>{guess}</b>': 🟥", "red"

        close_matches = difflib.get_close_matches(guess, session_state.all_words, n=1, cutoff=0.7)
        close_word = close_matches[0] if close_matches else None

        if close_word and close_word != guess:
            # Handle the corrected guess
            handle_guess(close_word, session_state)

            # Compute feedback for corrected word
            found_close = sum(1 for w in session_state.article_words if words_match(close_word, w.word))
            updated_close = sum(1 for w in session_state.article_words if w.best_guess == close_word)

            if found_close > 0:
                feedback = f"{'🟩'*found_close}{'🟧'*updated_close}"
                color = "green"
            elif updated_close > 0:
                feedback = f"{'🟧'*updated_close}"
                color = "orange"
            else:
                feedback = f"🟥"
                color = "red"

            session_state.guess_input = ""
            return f"'<b>{guess}</b>' corrigé en '<b>{close_word}</b>' : {feedback}",color

        else:
            return f"'<b>{guess}</b>' : 🟥", "red"

    # Provide normal feedback
    if found_count > 0:
        return f"'<b>{guess}</b>': {'🟩'*found_count}{'🟧'*updated_count}", "green"
    else:
        return f"'<b>{guess}</b>': {'🟧'*updated_count}", "orange"

def handle_guess(guess: str, session_state: SessionState):
    """Handle one word guess"""
    session_state.guesses.append(normalize_word(guess))

    # Check if the guess matches any individual words
    for word_info in session_state.article_words:
        if words_match(guess, word_info.word):
            word_info.best_similarity = 1
            session_state.revealed.add(word_info.normalized)

    for word_info in session_state.title_words:
        if words_match(guess, word_info.word):
            word_info.best_similarity = 1
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
            # print(f"Warning: Zero word vector for guess: {guess}")
            pass

        similar_results: List[SimilarityResult] = compute_similarity(guess_vec, session_state.article_words, session_state.revealed)

        for result in similar_results:
            word_info = session_state.article_words[result.index]
            if result.similarity > word_info.best_similarity:
                word_info.best_guess = guess
                word_info.best_similarity = result.similarity

    # Check victory
    if all(w in session_state.revealed for w in [w.normalized for w in session_state.title_words]):
        session_state.game_won = True
