from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Set, Dict, Any, cast, TYPE_CHECKING
import streamlit as st

if TYPE_CHECKING:
    import numpy as np

@dataclass
class SimilarityResult:
    word: str           # The word
    similarity: float   # The similarity with the guess
    index: int          # Index in the text

@dataclass
class WikipediaPage:
    title: str
    text: str       # Initially, text is the HTML of the page, and then the selected
    url: str

@dataclass
class WordInfo:
    word: str
    embedding: np.ndarray
    normalized: str                     # The word without accent and capital letter
    start: int                          # Start/End positon of word to place it
    end: int
    best_guess: Optional[str] = None    # The most similar guess found
    best_similarity: float = 0.0        # Its similarity score


class SessionState:
    _defaults: Dict[str, Any] = {
        'language': None,       # The language we play the game with ('en' or 'fr')
        'article': None,        # The fetched article (WikipediaPage type)
        'words': [],            # The words of the article (WordInfo type)
        'revealed': set(),      # Set of revealed words
        'guesses': [],          # List of guesses made ; TODO: add something visually to tell the user he already tried this word
        'model': None,          # Fasttext model
        'game_won': False,      # State of the game
        'last_similarity': 0.0  # Best similarity found with a word in the text ; TODO: remove
    }

    def __init__(self):
        for key, value in self._defaults.items():
            st.session_state.setdefault(key, value)

    def _get(self, key: str) -> Any:
        return st.session_state[key]

    def _set(self, key: str, value: Any):
        st.session_state[key] = value

    language: Optional[str] = property(lambda self: self._get('language'), lambda self, v: self._set('language', v))
    article: Optional[WikipediaPage] = property(lambda self: self._get('article'), lambda self, v: self._set('article', v))
    words: List['WordInfo'] = property(lambda self: self._get('words'), lambda self, v: self._set('words', v))
    revealed: Set[str] = property(lambda self: cast(Set[str], self._get('revealed')), lambda self, v: self._set('revealed', v))
    guesses: List[str] = property(lambda self: cast(List[str], self._get('guesses')), lambda self, v: self._set('guesses', v))
    model: Optional[Any] = property(lambda self: self._get('model'), lambda self, v: self._set('model', v))
    game_won: bool = property(lambda self: self._get('game_won'), lambda self, v: self._set('game_won', v))
    last_similarity: float = property(lambda self: self._get('last_similarity'), lambda self, v: self._set('last_similarity', v))


session_state = SessionState()