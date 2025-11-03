from __future__ import annotations

from typing import TYPE_CHECKING, List

from classes import WordInfo, SimilarityResult, session_state
import unicodedata
import numpy as np
import re

from config import SIMILARITY_THRESHOLD

if TYPE_CHECKING:
    import fasttext


def normalize_word(word: str) -> str:
    """Put word to normalized format (no accent, no capital letter)"""
    word = word.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', word) if unicodedata.category(c) != 'Mn')

def tokenize_text(text, model) -> List[WordInfo]:
    """Transform words to WordInfo objects, computing embeddings"""
    # Match sequences of letters (including accented) and/or numbers
    # \w matches letters, numbers, and underscore; \b ensures word boundaries
    pattern = r'\b\w+\b'
    words = []
    for match in re.finditer(pattern, text, re.UNICODE):
        word = match.group()
        # Skip words that contain underscores
        if "_" in word:
            continue
        words.append(WordInfo(word, embed_word(word, model), normalize_word(word), match.start(), match.end()))
    return words

def words_match(guess: str, target: str) -> bool:
    """Check if two words match"""
    guess_norm, target_norm = normalize_word(guess), normalize_word(target)
    if guess_norm == target_norm:
        return True
    # Simple plural handling
    for suffix in ['s', 'es', 'x']:
        if guess_norm.endswith(suffix) and guess_norm[:-len(suffix)] == target_norm:
            return True
        if target_norm.endswith(suffix) and target_norm[:-len(suffix)] == guess_norm:
            return True
    return False

def embed_word(text:str, model: fasttext.FastText._FastText) -> np.ndarray:
    """Transform a word into an embedding"""
    words = text.split()
    vectors = []
    for word in words:
        vectors.append(model.get_word_vector(word))
    if vectors:
        return np.mean(vectors, axis=0)
    else:
        return np.zeros(model.get_dimension())

def compute_similarity(guess_vec: np.ndarray, words: List[WordInfo]) -> List[SimilarityResult]:
    """Compute similarity between the guess vector and the words from the text"""
    similarities: List[SimilarityResult] = []

    for idx, word_info in enumerate(words):
        # Skip words that are marked as already revealed
        if word_info.normalized in session_state.revealed:
            continue

        # Compute cosine similarity
        word_vec = word_info.embedding
        if np.all(word_vec == 0):
            print(f"Warning: Zero word vector for: {word_info.word}")
        similarity = np.dot(guess_vec, word_vec) / (np.linalg.norm(guess_vec) * np.linalg.norm(word_vec))

        similarities.append(SimilarityResult(word=word_info.word, similarity=float(similarity), index=idx))

    similarities.sort(key=lambda x: x.similarity, reverse=True)

    # Return similar words above the threshold
    return [s for s in similarities if s.similarity > SIMILARITY_THRESHOLD]
