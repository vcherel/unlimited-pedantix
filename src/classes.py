from __future__ import annotations

from typing import Optional, List, Set, Dict, Any, cast, TYPE_CHECKING
import streamlit as st

if TYPE_CHECKING:
    import numpy as np


class WordInfo:
    def __init__(self, text: str, embedding: np.ndarray, normalized: str, start: int, end: int):
        self.text: str = text
        self.embedding: np.ndarray = embedding
        self.normalized: str = normalized
        self.start: int = start
        self.end: int = end


class SessionState:
    _defaults: Dict[str, Any] = {
        'language': None,
        'article': None,
        'full_text': "",
        'words': [],
        'revealed': set(),
        'guesses': [],
        'model': None,
        'game_won': False,
        'last_similarity': 0.0
    }

    def __init__(self):
        for key, value in self._defaults.items():
            st.session_state.setdefault(key, value)

    def _get(self, key: str) -> Any:
        return st.session_state[key]

    def _set(self, key: str, value: Any):
        st.session_state[key] = value

    language: Optional[str] = property(lambda self: self._get('language'), lambda self, v: self._set('language', v))
    article: Optional[Dict[str, Any]] = property(lambda self: self._get('article'), lambda self, v: self._set('article', v))
    full_text: str = property(lambda self: self._get('full_text'), lambda self, v: self._set('full_text', v))
    words: List['WordInfo'] = property(lambda self: self._get('words'), lambda self, v: self._set('words', v))
    revealed: Set[str] = property(lambda self: cast(Set[str], self._get('revealed')), lambda self, v: self._set('revealed', v))
    guesses: List[str] = property(lambda self: cast(List[str], self._get('guesses')), lambda self, v: self._set('guesses', v))
    model: Optional[Any] = property(lambda self: self._get('model'), lambda self, v: self._set('model', v))
    game_won: bool = property(lambda self: self._get('game_won'), lambda self, v: self._set('game_won', v))
    last_similarity: float = property(lambda self: self._get('last_similarity'), lambda self, v: self._set('last_similarity', v))

session_state = SessionState()