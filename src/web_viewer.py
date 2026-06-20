import asyncio
import json
import os

import streamlit as st
from streamlit_searchbox import st_searchbox

import ui.ui_components as ui
from classes import SessionState
from config import NB_ARTICLES_CLASSIFIER
from game.game_logic import (
    build_game_from_title,
    fetch_ranked_candidates,
    load_game,
    process_guess,
    warmup_imports,
)
from game.wiki_api import search_wikipedia_titles
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


def _spinner(status_text=""):
    st.markdown(ui.get_spinner_effect(status_text), unsafe_allow_html=True)


def reset_game(state):
    """Return to the language menu, clearing all per-game state."""
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
    state.titles = []
    state.batch_titles = []
    state.language = None
    state.phase = "language"


def start_game(state, game, choices=None):
    """Install a loaded game dict into the session and switch to the play screen.

    `choices` are the candidate titles to rate after winning (solo mode only);
    pass-and-play leaves it empty so the article stays hidden from the player.
    """
    state.article = game["article"]
    state.article_words = game["article_words"]
    state.title_words = game["title_words"]
    state.model = game["model"]
    state.titles = choices or []

    with open(f"vocab/words_{state.language}.txt", encoding="utf-8") as f:
        state.all_words = [line.strip() for line in f]

    state.phase = "play"


def render_language_menu(state):
    # Preload heavy ML imports in the background while the user picks a language,
    # so the first game load doesn't stall on them.
    warmup_imports()

    st.markdown(ui.get_language_button(), unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 20vh;'></div>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(ui.get_main_menu_text(), unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🇫🇷", use_container_width=True):
                state.language = "fr"
                state.phase = "mode"
                st.rerun()
        with col2:
            if st.button("🇬🇧", use_container_width=True):
                state.language = "en"
                state.phase = "mode"
                st.rerun()


def render_mode_menu(state):
    st.markdown(ui.get_main_menu_button(), unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 15vh;'></div>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            "<h1 style='text-align: center; margin-bottom: 20px;'>Choisis un mode :</h1>",
            unsafe_allow_html=True,
        )

        if st.button("🎲 Solo (page aléatoire)", use_container_width=True):
            _spinner()
            game = asyncio.run(load_game(state.language, _spinner))
            if game:
                start_game(state, game, choices=game.get("wikipedia_choices"))
                st.rerun()
            else:
                st.error("Erreur chargement du jeu.")

        if st.button("👥 À deux (quelqu'un choisit la page)", use_container_width=True):
            state.phase = "choose"
            st.rerun()

        if st.button("⬅ Changer de langue", use_container_width=True):
            reset_game(state)
            st.rerun()


def _load_and_start(state, title):
    _spinner("Récupération de l'article...")
    game = build_game_from_title(title, state.language, _spinner)
    if game:
        state.batch_titles = []
        start_game(state, game)  # no choices: keep the picked article hidden
        st.rerun()
    else:
        st.error("Impossible de charger cette page.")


def render_chooser(state):
    st.markdown("### 👥 Choix de la page")

    if st.button("⬅ Retour"):
        state.phase = "mode"
        st.rerun()

    tab_search, tab_batch = st.tabs(["🔍 Tape une page", "🎲 Choisis dans un lot"])

    with tab_search:
        selected = st_searchbox(
            lambda term: search_wikipedia_titles(term, state.language),
            key="page_search",
            placeholder="Titre d'une page Wikipédia...",
        )
        if selected:
            _load_and_start(state, selected)

    with tab_batch:
        if st.button("🎲 Tirer un lot d'articles populaires", use_container_width=True):
            _spinner("Récupération d'articles aléatoires...")
            candidates = asyncio.run(fetch_ranked_candidates(state.language, _spinner))
            state.batch_titles = [t for t, _ in candidates[:NB_ARTICLES_CLASSIFIER]]
            st.rerun()

        if state.batch_titles:
            st.markdown("#### Choisis une page :")
            col1, col2 = st.columns(2)
            for i, title in enumerate(state.batch_titles):
                with col1 if i % 2 == 0 else col2:
                    if st.button(title, key=f"batch_{i}", use_container_width=True):
                        _load_and_start(state, title)


def render_game(state):
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
                reset_game(state)
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

    # JavaScript to auto-focus and capture keyboard input. Rendered inline
    # (not iframed) so the script reaches the Streamlit input directly;
    # st.components.v1.html is deprecated.
    st.html(ui.get_keyboard_focus(), unsafe_allow_javascript=True)

    st.markdown(
        ui.get_guess_feedback(state.feedback_color, state.feedback_content),
        unsafe_allow_html=True,
    )

    display_article(state)

    _, col_center, _ = st.columns([2, 1, 2])

    if state.game_won and state.titles:
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
            reset_game(state)
            st.rerun()


def main():
    state = SessionState()
    st.set_page_config(page_title="Pedantix Illimité", page_icon="🎮", layout="wide")

    if state.phase == "language":
        render_language_menu(state)
    elif state.phase == "mode":
        render_mode_menu(state)
    elif state.phase == "choose":
        render_chooser(state)
    elif state.article and state.article_words:
        render_game(state)


if __name__ == "__main__":
    main()
