import asyncio
import json
import os

import streamlit as st
import streamlit.components.v1 as components

import ui.ui_components as ui
from classes import SessionState
from game.game_logic import load_game, process_guess
from ui.display_article import display_article


def save_liked_articles(titles, liked_titles, language):
    if liked_titles:
        os.makedirs("data", exist_ok=True)
        dataset_path = "data/dataset.json"

        if os.path.exists(dataset_path):
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"en": [], "fr": []}

        for title in titles:
            data[language].append({"title": title, "score": 1 if title in liked_titles else 0})

        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    state = SessionState()
    st.set_page_config(page_title="Pedantix Illimité", page_icon="🎮", layout="wide")

    if state.language is None:
        st.markdown(ui.get_language_button(), unsafe_allow_html=True)
        st.markdown("<div style='margin-top: 20vh;'></div>", unsafe_allow_html=True)
        _, col_center, _ = st.columns([1, 2, 1])

        with col_center:
            st.markdown(ui.get_main_menu_text(), unsafe_allow_html=True)

            selected_language = None

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🇫🇷", use_container_width=True):
                    selected_language = "fr"

            with col2:
                if st.button("🇬🇧", use_container_width=True):
                    selected_language = "en"

        if selected_language:

            def updated_spinner(status_text=""):
                st.markdown(ui.get_spinner_effect(status_text), unsafe_allow_html=True)

            updated_spinner()

            success_dict = asyncio.run(load_game(selected_language, updated_spinner))

            if success_dict:
                state.language = selected_language
                state.article = success_dict["article"]
                state.article_words = success_dict["article_words"]
                state.title_words = success_dict["title_words"]
                state.model = success_dict["model"]
                state.titles = success_dict["wikipedia_choices"]

                with open(f"vocab/words_{state.language}.txt", encoding="utf-8") as f:
                    state.all_words = [line.strip() for line in f]

                st.rerun()
            else:
                st.error("Erreur chargement du jeu.")
                state.language = None
            return

    if state.article and state.article_words:
        with st.sidebar:
            st.markdown("#### Mots proposés")

            guesses_html = ""
            if state.guesses:
                for i, guess in reversed(list(enumerate(state.guesses, 1))):
                    guesses_html += f"<div> <b>{i}.</b> {guess}</div>"
            else:
                guesses_html = "<div>Aucune tentative</div>"

            st.markdown(f"""{guesses_html}""", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            language_map = {"en": "anglais", "fr": "français"}
            st.markdown(f"### Jeu en {language_map.get(state.language, state.language)}")

        with col2:
            st.metric("Essais", len(state.guesses))

        with col3:
            revealed_count = len(state.revealed)
            total_unique = len(set(w.normalized for w in state.article_words))
            st.metric(
                "Progression",
                f"{revealed_count}/{total_unique} ({round(revealed_count / total_unique * 100, 1)}%)",
            )

        if state.game_won:
            st.markdown(ui.get_winner_style(), unsafe_allow_html=True)

            st.markdown(
                ui.get_winner_bar(state.article.title, len(state.guesses), state.article.url),
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Rejouer", type="primary", use_container_width=True):
                    save_liked_articles(state.titles, state.liked_titles, state.language)
                    state.language = None
                    state.guesses = []
                    state.revealed = set()
                    state.revealed_end = set()
                    state.game_won = False
                    state.feedback_color = "555"
                    state.feedback_content = "💡 Tapez un mot dans la barre !"
                    state.liked_titles = []
                    state.article = None
                    state.article_words = []
                    state.title_words = []
                    st.rerun()

            with col3:
                if st.button("Afficher tout", use_container_width=True):
                    state.revealed_end.update(
                        word_info.normalized
                        for word_info in state.article_words
                        if word_info.normalized not in state.revealed
                    )

        st.markdown(
            ui.get_text_input(),
            unsafe_allow_html=True,
        )

        def on_guess_change():
            guess = state.guess_input
            state.guess_input = ""

            content, color = process_guess(guess, state)
            state.feedback_content = content
            state.feedback_color = color

        st.text_input(
            "input", key="guess_input", label_visibility="collapsed", on_change=on_guess_change
        )

        # JavaScript to auto-focus and capture keyboard input
        components.html(ui.get_keyboard_focus(), height=0)

        st.markdown(
            ui.get_guess_feedback(state.feedback_color, state.feedback_content),
            unsafe_allow_html=True,
        )

        display_article(state)

        _, col_center, _ = st.columns([2, 1, 2])

        if state.game_won:
            st.markdown("### Note les autres choix potentiels de page :")
            col1, col2 = st.columns(2)
            for i, wiki_title in enumerate(state.titles):
                with col1 if i % 2 == 0 else col2:
                    if st.button(
                        wiki_title,
                        key=f"wiki_{i}",
                        type="primary" if wiki_title in state.liked_titles else "secondary",
                        use_container_width=True,
                    ):
                        if wiki_title in state.liked_titles:
                            state.liked_titles.remove(wiki_title)
                        else:
                            state.liked_titles.append(wiki_title)
                        st.rerun()

        with col_center:
            st.markdown(ui.get_main_menu_button(), unsafe_allow_html=True)

            if st.button("Main menu", use_container_width=True):
                save_liked_articles(state.titles, state.liked_titles, state.language)
                state.language = None
                state.guesses = []
                state.revealed = set()
                state.revealed_end = set()
                state.game_won = False
                state.feedback_color = "555"
                state.feedback_content = "💡 Tapez un mot dans la barre !"
                state.liked_titles = []
                state.article = None
                state.article_words = []
                state.title_words = []
                st.rerun()


if __name__ == "__main__":
    main()
