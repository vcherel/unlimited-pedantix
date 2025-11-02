import streamlit as st

from config import SIMILARITY_THRESHOLD
from game_logic import load_game, handle_guess
from text_utils import words_match
from classes import session_state


def display_text():
    """Display the article text with revealed/similar words shown"""
    if not session_state.words:
        return
    
    # Build the display text
    html_parts = []
    current_pos = 0
    
    for word_info in session_state.words:
        # Add any text before this word
        html_parts.append(session_state.article.text[current_pos:word_info.start])
        
        # Determine what to show for this word
        if word_info.normalized in session_state.revealed:
            # Word is revealed - show the actual word (no box)
            html_parts.append(f"<span style='color: #27AE60; font-weight: bold;'>{word_info.word}</span>")
        elif word_info.best_guess:
            # Word has a similar guess - show the guess on top of the box
            norm_similarity = (word_info.best_similarity - SIMILARITY_THRESHOLD) / (1 - SIMILARITY_THRESHOLD)
            norm_similarity = max(0, min(norm_similarity, 1))  # clamp to [0,1]
            
            if norm_similarity < 0.5:
                # Dark Red -> Yellow
                ratio = norm_similarity / 0.5
                red_tone = 210
                red = int(red_tone + (254 - red_tone) * ratio)  # Red goes from 128 (dark) to 255
                green = int(255 * ratio)      # Green goes from 0 to 255
            else:
                # Yellow -> Green
                ratio = (norm_similarity - 0.5) / 0.5
                red = int(255 * (1 - ratio))
                green = 255

            color = f"rgb({red},{green},0)"
                        # Box adapts to the guess length
            guess_length = max(len(word_info.best_guess), len(word_info.word))
            box_width = f"{guess_length * 0.6}em"
            # Create a box with the guess displayed on top
            html_parts.append(f"""<span style='position: relative; display: inline-block; 
                                            background-color: #2c3e50; width: {box_width}; 
                                            height: 1.2em; border-radius: 4px; vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                <span style='position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); 
                             color: {color}; font-weight: bold; white-space: nowrap; font-size: 0.85em;'>{word_info.best_guess}</span>
            </span>""")
        else:
            # Beautiful black box
            word_length = len(word_info.word)
            # Use approximate character width to size the box
            box_width = f"{word_length * 0.6}em"
            html_parts.append(f"""<span style='display: inline-block; background-color: #2c3e50; 
                                            width: {box_width}; height: 1.2em; border-radius: 4px; 
                                            vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'></span>""")
        
        current_pos = word_info.end
    
    # Add any remaining text
    html_parts.append(session_state.article.text[current_pos:])
    
    # Display with better styling
    st.markdown(f"""
    <div style='font-size: 1.1em; line-height: 2.2; padding: 20px; 
                background-color: #ecf0f1; border-radius: 10px; 
                font-family: Georgia, serif; white-space: pre-line;'>
        {''.join(html_parts)}
    </div>
    """, unsafe_allow_html=True)

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
                if st.button("🇫🇷", use_container_width=True, key="btn_fr"):
                    selected_language = 'fr'

            with col2:
                if st.button("🇬🇧", use_container_width=True, key="btn_en"):
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
                height: 120vh;
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
    if session_state.article and session_state.words:
        # Header stats
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### Language: {session_state.language.upper()}")
        with col2:
            st.metric("Guesses", len(session_state.guesses))
        with col3:
            revealed_count = len(session_state.revealed)
            total_unique = len(set(w.normalized for w in session_state.words))
            st.metric("Revealed", f"{revealed_count}/{total_unique}")

        # Win condition
        if session_state.game_won:
            st.balloons()
            st.success(f"Congratulations! Article: **{session_state.article.title}**")
            st.markdown(f"**Total guesses:** {len(session_state.guesses)}")
            st.markdown(f"[View on Wikipedia]({session_state.article.url})")
            if st.button("Play Again"):
                session_state.language = None
                st.rerun()
            return

        st.markdown("---")
        st.markdown("### Make a Guess:")
        with st.form(key='guess_form', clear_on_submit=True):
            guess = st.text_input("Type a word:", key="guess_input", label_visibility="collapsed")
            submitted = st.form_submit_button("Submit Guess", use_container_width=True)
            
            if submitted and guess:
                if " " in guess:
                    st.error("Spaces are not allowed in your guess!")
                else:
                    handle_guess(guess)
                    st.rerun()        

        # Feedback for last guess
        if session_state.guesses:
            last_guess = session_state.guesses[-1]

            # Check if the word was already proposed (excluding the last entry itself)
            if session_state.guesses.count(last_guess) > 1:
               st.markdown(
                    f"""
                    <div style="
                        background-color:#fff3cd;
                        color:#856404;
                        padding:10px 15px;
                        border-radius:5px;
                        border:1px solid #ffeeba;
                    ">
                        ⚠️ <b>{last_guess}</b> a déjà été proposé
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:
                found = any(words_match(last_guess, w.word) for w in session_state.words)

                if found:
                    st.success(f"✅  {last_guess}")
                else:
                    similarity = session_state.last_similarity
                    if similarity > 0:
                        # Count how many words were updated with this guess
                        updated_count = sum(1 for w in session_state.words if w.best_guess == last_guess)
                        st.info(f"🔍  {updated_count} nouveaux indices")
                    else:
                        st.warning(f"❌  {last_guess}")

        # Article display
        st.markdown("### Article Text:")
        # TODO: remplacer mots même quand c'est trouvé
        display_text()

        st.markdown("---")
        if st.button("Main menu", use_container_width=True):
            session_state.language = None
            st.rerun()


if __name__ == "__main__":
    main()
