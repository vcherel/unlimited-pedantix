from __future__ import annotations

from typing import List, TYPE_CHECKING 
import streamlit as st

from config import SIMILARITY_THRESHOLD
from classes import session_state

if TYPE_CHECKING:
    from classes import WordInfo


def display_article():
    """Display the article text with revealed/similar words shown"""
    
    def build_display_parts(word_list: List[WordInfo], source_text):
        """Build HTML parts for displaying text with revealed/similar words"""
        parts = []
        current_pos = 0
        
        for word_info in word_list:
            # Add any text before this word
            parts.append(source_text[current_pos:word_info.start])
            
            # Determine what to show for this word
            if word_info.normalized in session_state.revealed:
                # Word is revealed - show the actual word (no box)
                parts.append(f"<span style='color: #27AE60; font-weight: bold;'>{word_info.word}</span>")
            elif word_info.best_guess:
                # Word has a similar guess - show the guess on top of the box
                norm_similarity = (word_info.best_similarity - SIMILARITY_THRESHOLD) / (1 - SIMILARITY_THRESHOLD)
                norm_similarity = max(0, min(norm_similarity, 1))  # clamp to [0,1]
                if norm_similarity < 0.5:
                    # Dark Red -> Yellow
                    ratio = norm_similarity / 0.5
                    red_tone = 210
                    red = int(red_tone + (254 - red_tone) * ratio)
                    green = int(255 * ratio)
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
                parts.append(f"""<span style='position: relative; display: inline-block; 
                                            background-color: #2c3e50; width: {box_width}; 
                                            height: 1.2em; border-radius: 4px; vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                    <span style='position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); 
                                 color: {color}; font-weight: bold; white-space: nowrap; font-size: 0.85em;'>{word_info.best_guess}</span>
                </span>""")
            else:
                # Beautiful black box
                word_length = len(word_info.word)
                box_width = f"{word_length * 0.6}em"
                parts.append(f"""<span style='display: inline-block; background-color: #2c3e50; 
                                            width: {box_width}; height: 1.2em; border-radius: 4px; 
                                            vertical-align: middle; 
                                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);'></span>""")
            current_pos = word_info.end
        
        # Add any remaining text
        parts.append(source_text[current_pos:])
        return ''.join(parts)
    
    # Build title and text displays
    title_html = build_display_parts(session_state.title_words, session_state.article.title)
    text_html = build_display_parts(session_state.article_words, session_state.article.text)
    
    # Display with better styling - title and text in same box
    st.markdown(f"""
        <div style='font-size: 1.1em; line-height: 1.8; padding: 16px 20px; 
                    background-color: #ecf0f1; border-radius: 10px; 
                    font-family: Georgia, serif; white-space: pre-line;'>
            <div style='font-size: 1.3em; font-weight: bold; margin: 0 0 8px 0; line-height: 1.3;'>{title_html}</div>
            <div>{text_html}</div>
        </div>
        """, unsafe_allow_html=True)
