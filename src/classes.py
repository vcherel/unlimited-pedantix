from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Set, Any, TYPE_CHECKING
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


@dataclass
class SessionState:
    language: Optional[str] = None
    all_words: List[str] = field(default_factory=list)
    article: Optional[WikipediaPage] = None
    article_words: List[WordInfo] = field(default_factory=list)
    title_words: List[WordInfo] = field(default_factory=list)
    revealed: Set[str] = field(default_factory=set)
    revealed_end: Set[str] = field(default_factory=set)
    guess_input: str = ""
    guesses: List[str] = field(default_factory=list)
    feedback_content: str = ""
    feedback_color: str = ""
    model: Optional[Any] = None
    game_won: bool = False
    
    @classmethod
    def initialize(cls):
        """Initialize session state if it doesn't exist"""
        if 'state' not in st.session_state:
            st.session_state.state = cls()
        return st.session_state.state


# Global instance
session_state = SessionState.initialize()