import streamlit as st

from game_logic import load_game, handle_guess
from text_utils import words_match
from classes import session_state


def display_text():
    """Display the text with revealed/hidden words."""
    if not session_state.words or not session_state.full_text:
        st.warning("No text to display")
        return
    
    text = session_state.full_text
    words = session_state.words
    revealed = session_state.revealed
    
    # Build HTML output
    html_parts = []
    last_pos = 0
    
    for word_info in words:
        # Add text before this word (spaces, punctuation)
        between = text[last_pos:word_info.start]
        html_parts.append(between)
        
        # Add word (revealed or hidden)
        if word_info.normalized in revealed:
            html_parts.append(f"<span style='color: #27ae60; font-weight: bold;'>{word_info.word}</span>")
        else:
            # Black box - display as inline block with fixed character
            word_length = len(word_info.word)
            boxes = '█' * word_length  # Use block character
            html_parts.append(f"<span style='color: #34495e; background-color: #34495e; user-select: none;'>{boxes}</span>")
        
        last_pos = word_info.end
    
    # Add remaining text
    html_parts.append(text[last_pos:])
    
    # Display with better styling
    full_html = ''.join(html_parts)
    st.markdown(f"""
    <div style='font-size: 1.1em; line-height: 2.0; padding: 20px; 
                background-color: #ecf0f1; border-radius: 10px; 
                font-family: Georgia, serif; white-space: pre-wrap;'>
        {full_html}
    </div>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Pedantix amélioré", page_icon="🎮", layout="wide")

    # Language selection
    if session_state.language is None:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🇫🇷", use_container_width=True):
                session_state.language = 'fr'
                # TODO: show where we are in the loading
                with st.spinner("Chargement..."):
                    if load_game('fr'):
                        st.rerun()
                    else:
                        st.error("Erreur chargement du jeu.")
                        session_state.language = None
        with col2:
            if st.button("🇬🇧", use_container_width=True):
                session_state.language = 'en'
                with st.spinner("Chargement..."):
                    if load_game('en'):
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
            st.success(f"Congratulations! Article: **{session_state.article['title']}**")
            st.markdown(f"**Total guesses:** {len(session_state.guesses)}")
            st.markdown(f"[View on Wikipedia]({session_state.article['url']})")
            if st.button("Play Again"):
                session_state.language = None
                st.rerun()
            return

        st.markdown("---")
        st.markdown("### Make a Guess:")
        with st.form(key='guess_form'):  # Keep input on submit
            guess = st.text_input("Type a word:", key="guess_input", label_visibility="collapsed")
            submitted = st.form_submit_button("Submit Guess", use_container_width=True)
            
            # TODO: keep all content in that case
            if submitted and guess:
                if " " in guess:
                    st.error("Spaces are not allowed in your guess!")
                else:
                    handle_guess(guess)
                    st.rerun()

        # Feedback for last guess
        if session_state.guesses:
            last_guess = session_state.guesses[-1]
            found = any(words_match(last_guess, w.word) for w in session_state.words)
            if found:
                st.success(f"✅ Found '{last_guess}'!")
            else:
                similarity = getattr(session_state, 'last_similarity', 0)
                if similarity > 0:
                    st.info(f"🔍 '{last_guess}' is similar to hidden words ({similarity:.2%})")
                else:
                    st.warning(f"❌ '{last_guess}' not found")

        # Guess history
        if session_state.guesses:
            with st.expander(f"Guess History ({len(session_state.guesses)})"):
                for i, g in enumerate(session_state.guesses, 1):
                    st.text(f"{i}. {g}")

        # Article display
        st.markdown("### Article Text:")
        display_text()

        st.markdown("---")
        if st.button("Main menu", use_container_width=True):
            session_state.language = None
            st.rerun()


if __name__ == "__main__":
    main()
