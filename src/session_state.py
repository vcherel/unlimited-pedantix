from typing import Optional, List, Set, Dict, Any, cast
import streamlit as st


class SessionState:
    def __init__(self):
        # Default values with proper types
        self._defaults: Dict[str, Any] = {
            'language': None,                 # type: Optional[str]
            'article': None,                  # type: Optional[Dict[str, Any]]
            'full_text': "",                  # type: str
            'words': [],                      # type: List[Dict[str, Any]]
            'revealed': set(),                # type: Set[str]
            'guesses': [],                    # type: List[str]
            'model': None,                    # type: Optional[Any]
            'game_won': False,                # type: bool
            'last_similarity': 0.0            # type: float
        }

        # Initialize Streamlit session state
        for key, value in self._defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @property
    def language(self) -> Optional[str]:
        return st.session_state.language

    @language.setter
    def language(self, value: Optional[str]):
        st.session_state.language = value

    @property
    def article(self) -> Optional[Dict[str, Any]]:
        return st.session_state.article

    @article.setter
    def article(self, value: Optional[Dict[str, Any]]):
        st.session_state.article = value

    @property
    def full_text(self) -> str:
        return st.session_state.full_text

    @full_text.setter
    def full_text(self, value: str):
        st.session_state.full_text = value

    @property
    def words(self) -> List[Dict[str, Any]]:
        return st.session_state.words

    @words.setter
    def words(self, value: List[Dict[str, Any]]):
        st.session_state.words = value

    @property
    def revealed(self) -> set[str]:
        return cast(set[str], st.session_state.revealed)

    @revealed.setter
    def revealed(self, value: Set[str]):
        st.session_state.revealed = value

    @property
    def guesses(self) -> list[str]:
        return cast(list[str], st.session_state.guesses)

    @guesses.setter
    def guesses(self, value: List[str]):
        st.session_state.guesses = value

    @property
    def model(self) -> Optional[Any]:
        return st.session_state.model

    @model.setter
    def model(self, value: Any):
        st.session_state.model = value

    @property
    def game_won(self) -> bool:
        return st.session_state.game_won

    @game_won.setter
    def game_won(self, value: bool):
        st.session_state.game_won = value

    @property
    def last_similarity(self) -> float:
        return st.session_state.get('last_similarity', 0.0)

    @last_similarity.setter
    def last_similarity(self, value: float):
        st.session_state['last_similarity'] = value


session_state = SessionState()