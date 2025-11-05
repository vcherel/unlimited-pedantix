from __future__ import annotations

from classes import WordInfo, SimilarityResult, session_state
from typing import TYPE_CHECKING, List, Tuple
import unicodedata
import numpy as np
import regex

from config import SIMILARITY_THRESHOLD

if TYPE_CHECKING:
    import fasttext


def normalize_word(word: str) -> str:
    """Put word to normalized format (no accent, no capital letter)"""
    word = word.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', word) if unicodedata.category(c) != 'Mn')

def get_batch_embeddings(model, filtered_words):
    """
    Optimized word vector retrieval using ID lookup for in-vocabulary words
    and standard get_word_vector for OOV words.
    """
    embeddings = []

    for word in filtered_words:
        word_id = model.get_word_id(word)

        if word_id >= 0:
            # Use the faster direct input vector retrieval for in-vocabulary words
            vector = model.get_input_vector(word_id)
        else:
            # Fall back to the standard (slower) method for OOV words
            # which correctly computes the vector from subwords (n-grams)
            vector = model.get_word_vector(word)

        embeddings.append(vector)

    return np.array(embeddings)

def tokenize_text(text: str, model) -> List['WordInfo']:
    """Transform words to WordInfo objects, computing embeddings in batch, keeping accented Latin letters"""
    
    # Word Matching and Filtering
    # Match any Latin letter (including accents) and digits
    pattern = r'\b[\p{Latin}0-9]+\b'
    matches = [m for m in regex.finditer(pattern, text)]
    
    words = []
    filtered_words = []
    filtered_indices: List[Tuple[int, int]] = []
    
    # Preprocess words and filter out those with underscores
    for m in matches:
        word = m.group().replace("œ", "oe").replace("Œ", "Oe")
        if "_" not in word:
            filtered_words.append(word)
            filtered_indices.append((m.start(), m.end()))
    
    # Batch Compute Embeddings
    if not filtered_words:
        return []
    embeddings = get_batch_embeddings(model, filtered_words)
    
    # Build WordInfo objects
    for i, word in enumerate(filtered_words):
        start, end = filtered_indices[i]
        words.append(WordInfo(word, embeddings[i], normalize_word(word), start, end))
    
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

    guess_norm = np.linalg.norm(guess_vec)
    if guess_norm == 0:
        print("Warning: Zero guess vector — skipping similarity computation.")
        return []

    for idx, word_info in enumerate(words):
        if word_info.normalized in session_state.revealed:
            continue

        if word_info.word.isdigit():
            similarity = 0.0
        else:
            word_vec = word_info.embedding
            word_norm = np.linalg.norm(word_vec)

            if word_norm == 0:
                print(f"Warning: Zero word vector for: {word_info.word}")
                similarity = 0.0
            else:
                similarity = np.dot(guess_vec, word_vec) / (guess_norm * word_norm)

        similarities.append(SimilarityResult(word=word_info.word, similarity=float(similarity), index=idx))

    similarities.sort(key=lambda x: x.similarity, reverse=True)

    return [s for s in similarities if s.similarity > SIMILARITY_THRESHOLD]
