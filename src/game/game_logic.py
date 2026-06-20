from __future__ import annotations

import asyncio
import difflib
import math
import os
import re
import shutil
import threading
import time
import traceback
from typing import TYPE_CHECKING, List

import aiohttp
import numpy as np
import requests
import streamlit as st

from config import NB_ARTICLES, NB_ARTICLES_CLASSIFIER, USE_COMPRESSED_MODEL
from game.embedding_utils import (
    compute_similarity,
    embed_word,
    normalize_word,
    tokenize_text,
    words_match,
)
from game.wiki_api import (
    extract_first_paragraphs,
    fetch_page_views,
    fetch_random_titles,
    fetch_wikipedia_content,
)

if TYPE_CHECKING:
    from classes import SessionState, WikipediaPage
    from game.embedding_utils import SimilarityResult


_warmup_started = False
_warmup_lock = threading.Lock()


def warmup_imports():
    """Preload the heavy ML imports (sentence-transformers, xgboost,
    compress_fasttext — ~7s) in a background thread while the user is on the
    language menu, so the first game load doesn't pay that cost.

    Runs at most once per process. Only warms imports, not the language-specific
    models, and never touches Streamlit APIs (no ScriptRunContext in the thread).
    """
    global _warmup_started
    with _warmup_lock:
        if _warmup_started:
            return
        _warmup_started = True

    def _run():
        try:
            import compress_fasttext.models  # noqa: F401

            import game.classifier  # noqa: F401  (pulls in sentence_transformers, xgboost, ...)
        except Exception as e:
            print(f"Warmup import failed: {e}")

    threading.Thread(target=_run, daemon=True).start()


@st.cache_resource
def _load_fasttext_model(language: str):
    # Heavy imports are deferred to keep app startup fast (see load_game).
    from compress_fasttext.models import CompressedFastTextKeyedVectors

    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)

    if USE_COMPRESSED_MODEL:
        model_path = f"{models_dir}/fasttext-{language}-mini"
        if not os.path.exists(model_path):
            url = f"https://zenodo.org/records/4905385/files/fasttext-{language}-mini?download=1"
            r = requests.get(url)
            with open(model_path, "wb") as f:
                f.write(r.content)
        return CompressedFastTextKeyedVectors.load(model_path)
    else:
        import fasttext
        import fasttext.util

        local_path = f"{models_dir}/cc.{language}.300.bin"
        if not os.path.exists(local_path):
            fasttext.util.download_model(language, if_exists="ignore")
            shutil.move(f"cc.{language}.300.bin", local_path)
        return fasttext.load_model(local_path)


async def fetch_views_for_title(
    session: aiohttp.ClientSession, language: str, title: str, semaphore: asyncio.Semaphore
) -> tuple[str, int] | None:
    """Fetch page views for a single title, rate-limited by semaphore."""
    async with semaphore:
        try:
            views = await fetch_page_views(session, language, title)
            return (title, views) if views > 0 else None
        except aiohttp.ClientError as e:
            print(f"Client error for a candidate: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error for a candidate: {e}")
            traceback.print_exc()
            return None


async def fetch_ranked_candidates(language, update_spinner_func=None):
    """Fetch a random batch of articles and rank them by recent page views."""
    if update_spinner_func:
        update_spinner_func("Récupération d'articles aléatoires...")
        time.sleep(0.2)

    async with aiohttp.ClientSession() as session:
        titles = await fetch_random_titles(session, language, NB_ARTICLES)
        semaphore = asyncio.Semaphore(10)
        tasks = [fetch_views_for_title(session, language, t, semaphore) for t in titles]
        results = await asyncio.gather(*tasks)
        candidates = [r for r in results if r is not None]

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates


def build_game_from_title(title, language, update_spinner_func=None):
    """Fetch and prepare a playable game for a specific Wikipedia title.

    Returns the game dict, or None if the page has no usable text. Used by both
    the solo (classifier-picked) and pass-and-play (human-picked) flows.
    """
    if update_spinner_func:
        update_spinner_func("Récupération de l'article...")
        time.sleep(0.2)

    article: WikipediaPage = fetch_wikipedia_content(title, language)
    article.text = extract_first_paragraphs(article.text)

    if not article.text:
        return None

    if update_spinner_func:
        update_spinner_func("Préparation de l'IA tueuse...")
        time.sleep(0.2)

    model = _load_fasttext_model(language)
    article_words = tokenize_text(article.text, model)
    title_words = tokenize_text(article.title, model)

    return {
        "article": article,
        "article_words": article_words,
        "title_words": title_words,
        "model": model,
    }


async def load_game(language, update_spinner_func):
    """Solo mode: pick the best article from a random batch via the classifier."""
    try:
        candidates = await fetch_ranked_candidates(language, update_spinner_func)

        if not candidates:
            print("No candidates were successfully fetched.")
            return []

        print(f"\nTop {NB_ARTICLES_CLASSIFIER} articles by views:")
        for title, views in candidates[:NB_ARTICLES_CLASSIFIER]:
            print(f"  {title}: {views} views")

        update_spinner_func("Sélection du meilleur titre...")
        time.sleep(0.2)

        # Imported lazily: pulls in sentence-transformers/xgboost (~7s), only
        # needed once a game is actually loaded, not on the startup menu.
        from game.classifier import choose_title

        titles = [t for t, _ in candidates[:NB_ARTICLES_CLASSIFIER]]
        best_title = choose_title(titles, language)

        print(f"\n~~~~ {best_title} ~~~~")

        game = build_game_from_title(best_title, language, update_spinner_func)
        if not game:
            return False

        game["wikipedia_choices"] = titles

        update_spinner_func("Finito !")
        time.sleep(0.2)
        return game

    except Exception as e:
        print(f"Error in load_game: {e}")
        traceback.print_exc()
        return False


def numeric_similarity(a: float, b: float, sigma: float = 5.0) -> float:
    """Compute a smooth similarity between two numbers"""
    return math.exp(-((a - b) ** 2) / (2 * sigma**2))


def process_guess(guess: str, session_state: SessionState):
    """Logic to handle a guess including feedback and suggestions"""
    guess = guess.strip().lower()
    if not guess:
        return

    if normalize_word(guess) in session_state.guesses:
        repeated = f"'<b>{guess}</b>' a déjà été proposé", "orange"
    else:
        repeated = None

    handle_guess(guess, session_state)

    if repeated:
        return repeated

    found_count = sum(1 for w in session_state.article_words if words_match(guess, w.word))
    updated_count = sum(1 for w in session_state.article_words if w.best_guess == guess)

    if found_count == 0 and updated_count == 0:
        if re.fullmatch(r"\d+", guess.strip()):
            return f"'<b>{guess}</b>': 🟥", "red"

        close_matches = difflib.get_close_matches(guess, session_state.all_words, n=1, cutoff=0.7)
        close_word = close_matches[0] if close_matches else None

        if close_word and close_word != guess:
            handle_guess(close_word, session_state)

            found_close = sum(
                1 for w in session_state.article_words if words_match(close_word, w.word)
            )
            updated_close = sum(
                1 for w in session_state.article_words if w.best_guess == close_word
            )

            if found_close > 0:
                feedback = f"{'🟩' * found_close}{'🟧' * updated_close}"
                color = "green"
            elif updated_close > 0:
                feedback = f"{'🟧' * updated_close}"
                color = "orange"
            else:
                feedback = "🟥"
                color = "red"

            session_state.guess_input = ""
            return f"'<b>{guess}</b>' corrigé en '<b>{close_word}</b>' : {feedback}", color

        else:
            return f"'<b>{guess}</b>' : 🟥", "red"

    if found_count > 0:
        return f"'<b>{guess}</b>': {'🟩' * found_count}{'🟧' * updated_count}", "green"
    else:
        return f"'<b>{guess}</b>': {'🟧' * updated_count}", "orange"


def handle_guess(guess: str, session_state: SessionState):
    session_state.guesses.append(normalize_word(guess))

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
        guess_vec = embed_word(normalize_word(guess), session_state.model)
        if np.all(guess_vec == 0):
            # print(f"Warning: Zero word vector for guess: {guess}")
            pass

        similar_results: List[SimilarityResult] = compute_similarity(
            guess_vec, session_state.article_words, session_state.revealed
        )

        for result in similar_results:
            word_info = session_state.article_words[result.index]
            if result.similarity > word_info.best_similarity:
                word_info.best_guess = guess
                word_info.best_similarity = result.similarity

    if all(w in session_state.revealed for w in [w.normalized for w in session_state.title_words]):
        session_state.game_won = True
