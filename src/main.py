import streamlit as st
import streamlit.components.v1 as components

from game_logic import load_game, handle_guess
from embedding_utils import words_match
from classes import session_state
from ui_utils import display_article


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
            st.empty()
            spinner_placeholder = st.empty()
            def update_spinner(status_text=""):
                spinner_html = f"""
                <style>
                .spinner-container {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    z-index: 9999;
                    background-color: rgba(255, 255, 255, 0.95);
                }}
                .spinner {{
                    border: 8px solid #f3f3f3;
                    border-top: 8px solid #3498db;
                    border-radius: 50%;
                    width: 80px;
                    height: 80px;
                    animation: spin 1s linear infinite;
                    margin-bottom: 30px;
                }}
                .status-text {{
                    font-size: 18px;
                    color: #333;
                    font-weight: 500;
                    text-align: center;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                </style>
                <div class="spinner-container">
                    <div class="spinner"></div>
                    <div class="status-text">{status_text}</div>
                </div>
                """
                spinner_placeholder.markdown(spinner_html, unsafe_allow_html=True)
            
            update_spinner()
            success = load_game(selected_language, update_spinner)
            spinner_placeholder.empty()
            
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

        # Winner interface
        if session_state.game_won:
            st.balloons()
            st.markdown(
                """
                <style>
                .winbar {
                    background: linear-gradient(135deg, #66ff99, #33cc7a); /* softer green */
                    border-radius: 20px;
                    padding: 1.2rem 2rem;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 2rem;
                    box-shadow: 0 8px 24px rgba(102,255,153,0.4); /* softer shadow */
                    margin-bottom: 2rem;
                }
                .winbar .big {
                    font-size: 2.2rem;
                    font-weight: 800;
                    color: #fff;
                    text-shadow: 0 2px 4px rgba(0,0,0,.25);
                }
                .winbar a.wiki {
                    font-size: 1.6rem;
                    color: #fff;
                    text-decoration: none;
                    border: 2px solid #fff;
                    border-radius: 12px;
                    padding: .4rem 1rem;
                    transition: .25s;
                }
                .winbar a.wiki:hover {
                    background: #fff;
                    color: #33cc7a;
                }
                """,
                unsafe_allow_html=True,
            )

            bar = st.container()
            with bar:
                st.markdown(
                    f"""
                    <div class="winbar">
                        <div class="big">🎉 Bravo !!! L'article était : <b>{st.session_state.article.title}</b></div>
                        <div class="big">Essais : {len(st.session_state.guesses)}</div>
                        <a class="wiki" href="{st.session_state.article.url}" target="_blank">Voir sur Wikipédia</a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Rejouer", type="primary", use_container_width=True):
                    session_state.language = None
                    st.rerun()

            with col3:
                if st.button("Afficher tout", use_container_width=True):
                    session_state.revealed_end.update(
                        word_info.normalized for word_info in session_state.article_words
                        if word_info.normalized not in session_state.revealed
                    )
        
        def on_guess_change():
            guess = st.session_state.guess_input
            if guess:  # Only process if there's actual input
                handle_guess(guess)
                # Clear the input after processing
                st.session_state.guess_input = ""

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
                padding: 8px 12px !important;
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
            """<script>
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
                    const allowed = /^[a-zA-Z0-9]$/;
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
            font-size: 1rem;
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

        feedback_content = ""

        if session_state.guesses:
            last_guess = session_state.guesses[-1]

            if session_state.guesses.count(last_guess) > 1:
                feedback_content = f"⚠️ <b>{last_guess}</b> a déjà été proposé"
                color = "orange"
            else:
                found_count = sum(1 for w in session_state.article_words if words_match(last_guess, w.word))
                updated_count = sum(1 for w in session_state.article_words if w.best_guess == last_guess)

                if found_count == 0 and updated_count == 0:
                    feedback_content = f"❌ <b>{last_guess}</b> : 🟥"
                    color = "red"
                elif found_count == 0:
                    feedback_content = f"🟠 <b>{last_guess}</b> : {'🟧' * updated_count}"
                    color = "orange"
                else:
                    feedback_content = f"✅ <b>{last_guess}</b> : {'🟩' * found_count}{'🟧' * updated_count}"
                    color = "green"
        else:
            feedback_content = "💡 Tapez un mot dans la barre !"
            color = "#555"

        # Inject the floating feedback box
        st.markdown(feedback_html.format(content=f"<p style='color:{color}'>{feedback_content}</p>"), unsafe_allow_html=True)

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
