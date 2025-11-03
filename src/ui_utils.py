from __future__ import annotations

from typing import List, TYPE_CHECKING 
import streamlit as st

from config import SIMILARITY_THRESHOLD
from classes import session_state
from embedding_utils import words_match

if TYPE_CHECKING:
    from classes import WordInfo


def display_article():
    """Display the article text with revealed/similar words shown"""
    
    def build_display_parts(word_list: List[WordInfo], source_text, last_guess: str = None):
        """Build HTML parts for displaying text with revealed/similar words"""
        parts = []
        current_pos = 0
        
        for word_info in word_list:
            parts.append(source_text[current_pos:word_info.start])
            
            # Determine if this word is affected by the last guess
            is_last_guess = (word_info.best_guess == last_guess)
            # Check if the word was just fully revealed by the last guess
            just_revealed = (word_info.normalized in session_state.revealed and words_match(last_guess, word_info.word))
            
            if just_revealed:
                # Strong green box + white text for newly revealed words
                word_length = len(word_info.word)
                box_width = f"{word_length * 0.6 + 1.6}em"
                parts.append(f"""<span style='position: relative; display: inline-block; 
                                            background-color: #27AE60; width: {box_width}; height: 1.2em; 
                                            border-radius: 4px; vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                    <span style='position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
                                color: #fff; font-weight: bold; white-space: nowrap;'>{word_info.word}</span>
                    <span style='position: absolute; right: 3px; bottom: -1px; font-size: 0.55em; color: #bdc3c7;'>{word_length}</span>
                </span>""")
            
            elif word_info.normalized in session_state.revealed:
                # Previously revealed words: normal green bold text
                parts.append(f"<span style='color: #27AE60; font-weight: bold;'>{word_info.word}</span>")
            
            # Check for revealed_end words that haven't been fully guessed/revealed yet
            elif word_info.normalized in session_state.revealed_end:
                word_length = len(word_info.word)
                box_width = f"{word_length * 0.6 + 1.6}em"
                color = "#D67DDF" # Purple color for revealed_end
                parts.append(f"""<span style='position: relative; display: inline-block; 
                                            background-color: #2c3e50; width: {box_width}; height: 1.2em; 
                                            border-radius: 4px; vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                    <span style='position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
                                color: {color}; font-weight: bold; white-space: nowrap;'>{word_info.word}</span>
                    <span style='position: absolute; right: 3px; bottom: -1px; font-size: 0.55em; color: #bdc3c7;'>{word_length}</span>
                </span>""")

            # Words with a guess (that are NOT fully revealed or revealed_end)
            elif word_info.best_guess:
                # Word has a guess
                norm_similarity = (word_info.best_similarity - SIMILARITY_THRESHOLD) / (1 - SIMILARITY_THRESHOLD)
                norm_similarity = max(0, min(norm_similarity, 1))
                
                guess_length = max(len(word_info.best_guess), len(word_info.word))
                box_width = f"{guess_length * 0.6 + 1.6}em"
                
                if is_last_guess:
                    # Most recent guess: gradient for similar, green for exact
                    if norm_similarity >= 1:  # exact match
                        color = "#27AE60"
                    else:  # similar guess
                        if norm_similarity < 0.5:
                            ratio = norm_similarity / 0.5
                            red_tone = 210
                            red = int(red_tone + (254 - red_tone) * ratio)
                            green = int(255 * ratio)
                        else:
                            ratio = (norm_similarity - 0.5) / 0.5
                            red = int(255 * (1 - ratio))
                            green = 255
                        color = f"rgb({red},{green},0)"
                else:
                    # Previous guesses: grayscale
                    gray = int(80 + 200 * norm_similarity)
                    color = f"rgb({gray},{gray},{gray})"
                
                parts.append(f"""<span style='position: relative; display: inline-block; 
                                            background-color: #2c3e50; width: {box_width}; height: 1.2em; 
                                            border-radius: 4px; vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                    <span style='position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
                                color: {color}; font-weight: bold; white-space: nowrap;'>{word_info.best_guess}</span>
                    <span style='position: absolute; right: 3px; bottom: -1px; font-size: 0.55em; color: #bdc3c7;'>{len(word_info.word)}</span>
                </span>""")

            else:
                # Not guessed yet
                word_length = len(word_info.word)
                box_width = f"{word_length * 0.6 + 1.1}em"
                parts.append(f"""<span style='position: relative; display: inline-block; background-color: #2c3e50; 
                                            width: {box_width}; height: 1.2em; border-radius: 4px; 
                                            vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                    <span style='position: absolute; right: 3px; bottom: -1px; font-size: 0.55em; color: #bdc3c7;'>{word_length}</span>
                </span>""")
            
            current_pos = word_info.end

        parts.append(source_text[current_pos:])
        return ''.join(parts)

    # Build title and text displays
    last_guess = session_state.guesses[-1] if session_state.guesses else None
    title_html = build_display_parts(session_state.title_words, session_state.article.title, last_guess)
    text_html = build_display_parts(session_state.article_words, session_state.article.text, last_guess)
    
    # Display with better styling - title and text in same box
    st.markdown(f"""
        <div style='font-size: 1.1em; line-height: 1.8; padding: 16px 20px; 
                    background-color: #ecf0f1; border-radius: 10px; 
                    font-family: Georgia, serif; white-space: pre-line;'>
            <div style='font-size: 1.3em; font-weight: bold; margin: 0 0 8px 0; line-height: 1.3;'>{title_html}</div>
            <div>{text_html}</div>
        </div>
        """, unsafe_allow_html=True)
