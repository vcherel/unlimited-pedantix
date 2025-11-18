import streamlit.components.v1 as components
import streamlit as st
import asyncio
import json
import os

import ui.ui_components as ui
from classes import SessionState
from ui.display_article import display_article
from game.game_logic import load_game, process_guess


def save_liked_articles(titles, liked_titles, language):
        """Save liked titles"""
        if liked_titles:
            # Save dataset
            os.makedirs("output", exist_ok=True)
            dataset_path = "output/dataset.json"
            
            # Load existing data
            if os.path.exists(dataset_path):
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'en': [], 'fr': []}
            
            # Add current ratings
            for title in titles:
                data[language].append({
                    'title': title,
                    'score': 1 if title in liked_titles else 0
                })
            
            # Save
            with open(dataset_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    state = SessionState()
    st.set_page_config(page_title="Pedantix Illimité", page_icon="🎮", layout="wide")

    # Language selection
    if state.language is None:
        # Big buttons
        st.markdown(ui.get_language_button(), unsafe_allow_html=True)

        # Add vertical spacing to center on page
        st.markdown("<div style='margin-top: 20vh;'></div>", unsafe_allow_html=True)
        
        # Center the language selection horizontally
        _, col_center, _ = st.columns([1, 2, 1])
        
        with col_center:
            st.markdown(ui.get_main_menu_text(), unsafe_allow_html=True)

            selected_language = None

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🇫🇷", use_container_width=True):
                    selected_language = 'fr'
                    
            with col2:
                if st.button("🇬🇧", use_container_width=True):
                    selected_language = 'en'

        # Loading pinner
        if selected_language:

            # Show where we are in the game loading
            def updated_spinner(status_text=""):
                st.markdown(ui.get_spinner_effect(status_text), unsafe_allow_html=True)
            updated_spinner()

            success_dict = asyncio.run(load_game(selected_language, updated_spinner))
            
            if success_dict:
                state.language = selected_language
                state.article = success_dict['article']
                state.article_words = success_dict['article_words']
                state.title_words = success_dict['title_words']
                state.model = success_dict['model']
                state.titles = success_dict['wikipedia_choices']

                # Load dict with all words from the language
                with open(f"data/words_{state.language}.txt", encoding="utf-8") as f:
                    state.all_words = [line.strip() for line in f]

                st.rerun()
            else:
                st.error("Erreur chargement du jeu.")
                state.language = None
            return

    # Game interface
    if state.article and state.article_words:

        # Header stats
        col1, col2, col3 = st.columns([2, 1, 1])

        # Display language
        with col1:
            language_map = {
                "en": "anglais",
                "fr": "français"
            }
            st.markdown(f"### Jeu en {language_map.get(state.language, state.language)}")
        
        # Display number of tries
        with col2:
            st.metric("Essais", len(state.guesses))

        # Display progress
        with col3:
            revealed_count = len(state.revealed)
            total_unique = len(set(w.normalized for w in state.article_words))
            st.metric("Progression", f"{revealed_count}/{total_unique} ({round(revealed_count / total_unique * 100, 1)}%)")

        # Winner interface
        if state.game_won:
            st.markdown(ui.get_winner_style(), unsafe_allow_html=True)

            st.markdown(
                ui.get_winner_bar(state.article.title, len(state.guesses), state.article.url), unsafe_allow_html=True,)

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Rejouer", type="primary", use_container_width=True):
                    save_liked_articles(state.titles, state.liked_titles, state.language)
                    state.reset()
                    st.rerun()

            with col3:
                if st.button("Afficher tout", use_container_width=True):
                    state.revealed_end.update(
                        word_info.normalized for word_info in state.article_words
                        if word_info.normalized not in state.revealed
                    )

        # Text input (triggers on Enter key)
        st.markdown(ui.get_text_input(), unsafe_allow_html=True,)

        def on_guess_change():
            guess = state.guess_input
            state.guess_input = ""

            content, color = process_guess(guess, state)
            state.feedback_content = content
            state.feedback_color = color

        st.text_input(
            "input",
            key="guess_input",
            label_visibility="collapsed",
            on_change=on_guess_change
        )
        
        # JavaScript to auto-focus and capture keyboard input
        components.html(ui.get_keyboard_focus(), height=0)
        
        # Feedback for last guess
        st.markdown(ui.get_guess_feedback(state.feedback_color, state.feedback_content), unsafe_allow_html=True)

        # Article display
        display_article(state)

        _, col_center, _ = st.columns([2, 1, 2])

        # Display rating system
        if state.game_won:
            st.markdown("### Note les autres choix potentiels de page :")
            col1, col2 = st.columns(2)
            for i, wiki_title in enumerate(state.titles):
                with col1 if i % 2 == 0 else col2:
                    if st.button(
                        wiki_title,
                        key=f"wiki_{i}",
                        type="primary" if wiki_title in state.liked_titles else "secondary",
                        use_container_width=True
                    ):
                        if wiki_title in state.liked_titles:
                            state.liked_titles.remove(wiki_title)
                        else:
                            state.liked_titles.append(wiki_title)
                        st.rerun()

        # Main menu button
        with col_center:
            st.markdown(ui.get_main_menu_button(), unsafe_allow_html=True)
            
            if st.button("Main menu", use_container_width=True):
                save_liked_articles(state.titles, state.liked_titles, state.language)
                state.reset()
                st.rerun()


if __name__ == "__main__":
    main()
