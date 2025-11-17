import streamlit.components.v1 as components
import streamlit as st
import asyncio

import ui.ui_components as ui
from classes import SessionState
from ui.display_article import display_article
from game.game_logic import load_game, process_guess


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

            success_dict = asyncio.run(
                load_game(selected_language, updated_spinner, state)
            )
            
            if success_dict:
                state.language = selected_language
                state.article = success_dict['article']
                state.article_words = success_dict['article_words']
                state.title_words = success_dict['title_words']
                state.model = success_dict['model']

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
            st.balloons()
            st.markdown(ui.get_winner_style(), unsafe_allow_html=True)

            st.markdown(
                ui.get_winner_bar(state.article.title, len(state.guesses), state.article.url), unsafe_allow_html=True,)

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Rejouer", type="primary", use_container_width=True):
                    state.reset()
                    st.rerun()

            with col3:
                if st.button("Afficher tout", use_container_width=True):
                    state.revealed_end.update(
                        word_info.normalized for word_info in state.article_words
                        if word_info.normalized not in state.revealed
                    )
        
        def on_guess_change():
            guess = state.guess_input
            state.guess_input = ""
            if not guess:
                return
            content, color = process_guess(guess, state)
            state.feedback_content = content
            state.feedback_color = color

        # Text input with on_change callback (triggers on Enter key)
        st.markdown(
            """
            <style>
            /* Fix text input at bottom */
            div[data-testid="stTextInput"] {
                position: fixed !important;
                bottom: 1.5rem !important;
                left: 12% !important;
                transform: translateX(-50%) !important;
                z-index: 999999 !important;
                padding: 10px 12px !important;
                border-radius: 12px !important;
                background: white !important;
                box-shadow: 0 6px 18px rgba(0,0,0,0.15) !important;
                width: 350px !important;
            }

            /* Input field styling */
            div[data-testid="stTextInput"] input {
                font-size: 18px !important;
                padding: 10px 14px !important;
                background: white !important;
                border-radius: 10px !important;
            }

            /* Leave space at bottom so content isn't hidden */
            .appview-container, .block-container, .main {
                padding-bottom: 120px !important;
            }
            /* Hide "Press Enter to Apply" */
            div[data-testid="InputInstructions"] > span:nth-child(1) {
                visibility: hidden !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.text_input(
            "input",
            key="guess_input",
            label_visibility="collapsed",
            on_change=on_guess_change
        )
        
        # JavaScript to auto-focus and capture keyboard input
        components.html(
            r"""<script>
            const setupAutoFocus = () => {
                const parentDoc = window.parent.document;
                const input = parentDoc.querySelector('input[aria-label="input"]');
                
                if (!input) {
                    setTimeout(setupAutoFocus, 100);
                    return;
                }
                
                // Focus immediately
                input.focus();
                
                // Capture keyboard events
                parentDoc.addEventListener('keydown', (e) => {
                    // Skip if modifier keys are pressed
                    if (e.ctrlKey || e.metaKey || e.altKey) return;
                    
                    const active = parentDoc.activeElement;
                    if (active && active !== input && 
                        (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || 
                        active.tagName === 'BUTTON' || active.isContentEditable)) {
                        return;
                    }
                    
                    // Allow only letters and numbers
                    const allowed = /^\p{L}|\p{N}$/u;
                    if (e.key.length === 1 && !allowed.test(e.key)) {
                        e.preventDefault(); // Block the key
                    } else if (e.key === 'Backspace' || e.key === 'Delete') {
                        // Allow deletion
                        input.focus();
                    } else if (e.key.length === 1) {
                        input.focus();
                    }
                }, true);
                
                // Keep refocusing
                setInterval(() => {
                    const active = parentDoc.activeElement;
                    if (!active || (active.tagName !== 'INPUT' && active.tagName !== 'BUTTON' && 
                                    active.tagName !== 'TEXTAREA')) {
                        input.focus();
                    }
                }, 500);
            };

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', setupAutoFocus);
            } else {
                setupAutoFocus();
            }
            </script>
            """,
            height=0,
        )
        
        # Feedback for last guess
        feedback_html = """
        <style>
        .feedback-box {{
            position: fixed;
            bottom: 1.5rem;
            left: 400px;
            max-width: 1500px;
            z-index: 999999;
            background: rgba(255,255,255,0.95);
            padding: 0.95rem 1.2rem;
            border-radius: 12px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.15);
            font-size: 1.2rem;
            font-weight: 500;
            min-height: 50px;
        }}
        .feedback-box p {{
            margin: 0;
        }}
        </style>
        <div class="feedback-box">
            {content}
        </div>
        """

        # Inject the floating feedback box
        st.markdown(feedback_html.format(content=f"<p style='color:{state.feedback_color}'>{state.feedback_content}</p>"), unsafe_allow_html=True)

        # Article display
        display_article(state)

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
                state.reset()
                st.rerun()


if __name__ == "__main__":
    main()
