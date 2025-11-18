from __future__ import annotations

from typing import Dict, Optional, List, Set, Any, TYPE_CHECKING, cast
from dataclasses import dataclass
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
        'language': None,           # The language we play the game with ('en' or 'fr')
        'all_words': [],            # List of all words in the language
        'article': None,            # The fetched article (WikipediaPage type)
        'titles': [],               # The list of potential titles that could have been chosen
        'liked_titles': [],         # The titles that the user liked
        'article_words': [],        # The words of the article (WordInfo type)
        'title_words': [],          # The words of the title
        'model': None,              # Fasttext model
        'game_won': False,          # State of the game
        'revealed': set(),          # Set of revealed words (normalized)
        'revealed_end': set(),      # Set of revealed words at the end (normalized)
        'guesses': [],              # List of guesses made
        'guess_input': "",          # The user's input
        'feedback_color': "555",    # Color of the feedback
        'feedback_content': "💡 Tapez un mot dans la barre !",    # Feedback for the last guess
    }

    def __init__(self):
        for key, value in self._defaults.items():
            st.session_state.setdefault(key, value)

    def _get(self, key: str) -> Any:
        return st.session_state.get(key, self._defaults[key])

    def _set(self, key: str, value: Any):
        st.session_state[key] = value
    
    def reset(self):
        keys_to_delete = list(st.session_state.keys())
        for key in keys_to_delete:
            del st.session_state[key]

    language: Optional[str] = property(lambda self: self._get('language'), lambda self, v: self._set('language', v))
    all_words: List[str] = property(lambda self: cast(List[str], self._get('all_words')), lambda self, v: self._set('all_words', v))
    article: Optional[WikipediaPage] = property(lambda self: self._get('article'), lambda self, v: self._set('article', v))
    titles: List[str] = property(lambda self: self._get('titles'), lambda self, v: self._set('titles', v))
    liked_titles: List[str] = property(lambda self: self._get('liked_titles'), lambda self, v: self._set('liked_titles', v))
    article_words: List[WordInfo] = property(lambda self: self._get('article_words'), lambda self, v: self._set('article_words', v))
    title_words: List[WordInfo] = property(lambda self: self._get('title_words'), lambda self, v: self._set('title_words', v))
    model: Optional[Any] = property(lambda self: self._get('model'), lambda self, v: self._set('model', v))
    game_won: bool = property(lambda self: self._get('game_won'), lambda self, v: self._set('game_won', v))
    revealed: Set[str] = property(lambda self: cast(Set[str], self._get('revealed')), lambda self, v: self._set('revealed', v))
    revealed_end: Set[str] = property(lambda self: cast(Set[str], self._get('revealed_end')), lambda self, v: self._set('revealed_end', v))
    guesses: List[str] = property(lambda self: cast(List[str], self._get('guesses')), lambda self, v: self._set('guesses', v))
    guess_input: str = property(lambda self: cast(str, self._get('guess_input')), lambda self, v: self._set('guess_input', v))
    feedback_color: str = property(lambda self: cast(str, self._get('feedback_color')), lambda self, v: self._set('feedback_color', v))
    feedback_content: str = property(lambda self: cast(str, self._get('feedback_content')), lambda self, v: self._set('feedback_content', v))