from __future__ import annotations

from typing import List, TYPE_CHECKING 
import streamlit as st

from config import SIMILARITY_THRESHOLD
from game_logic import load_game, handle_guess
from embedding_utils import words_match
from classes import session_state
from ui_utils import display_article

if TYPE_CHECKING:
    from classes import WordInfo


def main():
    st.set_page_config(page_title="Pedantix amélioré", page_icon="🎮", layout="wide")

    # Language selection
    if session_state.language is None:
        # Big buttons
        st.markdown("""
            <style>
            .stButton > button {
                height: 100px !important;
            }
            .stButton > button p {
                font-size: 50px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # Add vertical spacing to center on page
        st.markdown("<div style='margin-top: 20vh;'></div>", unsafe_allow_html=True)
        
        # Center the language selection horizontally
        _, col_center, _ = st.columns([1, 2, 1])
        
        with col_center:
            st.markdown(
                """
                <h1 style='text-align: center; margin-bottom: 20px;'>
                    Choisis une langue pour jouer :
                </h1>
                """,
                unsafe_allow_html=True
            )

            selected_language = None

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🇫🇷", use_container_width=True):
                    selected_language = 'fr'

            with col2:
                if st.button("🇬🇧", use_container_width=True):
                    selected_language = 'en'

        # Spinner
        if selected_language:
            session_state.language = selected_language
            
            # Clear the entire page first
            st.empty()
            
            spinner_html = """
            <style>
            .spinner-container {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 140vh;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                z-index: 9999;
            }
            .spinner {
                border: 8px solid #f3f3f3;
                border-top: 8px solid #3498db;
                border-radius: 50%;
                width: 80px;
                height: 80px;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            </style>
            <div class="spinner-container">
                <div class="spinner"></div>
            </div>
            """
            
            st.markdown(spinner_html, unsafe_allow_html=True)
            
            success = load_game(selected_language)
            
            if success:
                st.rerun()
            else:
                st.error("Erreur chargement du jeu.")
                session_state.language = None
        
        return

    # Game interface
    if session_state.article and session_state.article_words:
        # Header stats
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            language_map = {
                "en": "anglais",
                "fr": "français"
            }
            st.markdown(f"### Jeu en {language_map.get(session_state.language, session_state.language)}")
        with col2:
            st.metric("Essais", len(session_state.guesses))
        with col3:
            revealed_count = len(session_state.revealed)
            total_unique = len(set(w.normalized for w in session_state.article_words))
            st.metric("Progression", f"{revealed_count}/{total_unique} ({round(revealed_count / total_unique * 100, 1)}%)")

        # Win condition
        if session_state.game_won:
            st.balloons()
            st.success(f"Bravo ! Article: **{session_state.article.title}**")
            st.markdown(f"**Nombre total d'essais:** {len(session_state.guesses)}")
            st.markdown(f"[Voir sur Wikipédia]({session_state.article.url})")
            if st.button("Rejouer"):
                session_state.language = None
                st.rerun()
            return

        st.markdown("---")
        st.markdown("### Tente ta chance :")
        
        def on_guess_change():
            guess = st.session_state.guess_input
            if guess:  # Only process if there's actual input
                handle_guess(guess)
                # Clear the input after processing
                st.session_state.guess_input = ""

        # Text input with on_change callback (triggers on Enter key)
        st.markdown("""
            <style>
            .stTextInput > div > div > input {
                font-size: 18px;
                padding: 12px;
            }
            .stTextInput {
                max-width: 300px;
                margin-top: -20px;
            }
            </style>
            """, unsafe_allow_html=True)
        st.text_input(
            "input", 
            key="guess_input",
            label_visibility="collapsed",
            on_change=on_guess_change
        )

        # Feedback for last guess
        if session_state.guesses:
            last_guess = session_state.guesses[-1]

            # Check if the word was already proposed (excluding the last entry itself)
            if session_state.guesses.count(last_guess) > 1:
                st.warning(f"⚠️ {last_guess} a déjà été proposé")
                            
            elif " " in last_guess:
                st.warning("⚠️ Les espaces ne sont pas autorisés")

            else:
                found_count = sum(1 for w in session_state.article_words if words_match(last_guess, w.word))
                updated_count = sum(1 for w in session_state.article_words if w.best_guess == last_guess)

                if found_count == 0 and updated_count == 0:
                    st.error(f"{last_guess} : 🟥")
                elif found_count == 0:
                    st.warning(f"{last_guess} : {'🟧' * updated_count}")
                else:
                    st.success(f"{last_guess} : {'🟩' * found_count}{'🟧' * updated_count}")

        # Article display
        display_article()

        _, col_center, _ = st.columns([2, 1, 2])

        # Main menu button
        with col_center:
            st.markdown("""
                <style>
                .stButton > button {
                    height: 60px !important;
                }
                .stButton > button p {
                    font-size: 25px !important;
                }
                </style>
            """, unsafe_allow_html=True)
            if st.button("Main menu", use_container_width=True):
                session_state.language = None
                st.rerun()


if __name__ == "__main__":
    main()
