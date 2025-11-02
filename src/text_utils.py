import unicodedata
import numpy as np
import fasttext
import re


def normalize_word(word: str):
    word = word.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', word) if unicodedata.category(c) != 'Mn')

def tokenize_text(text):
    pattern = r'\b[\w\'-]+\b'
    words = []
    for match in re.finditer(pattern, text):
        word = match.group()
        if len(word) > 1 or word.isalpha():
            words.append({'text': word, 'normalized': normalize_word(word), 'start': match.start(), 'end': match.end()})
    return words

def words_match(guess, target):
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

def embed_text(text:str, model: fasttext.FastText._FastText):
    words = text.split()  # simple tokenization; you can use more sophisticated tokenizer
    vectors = []
    for word in words:
        vectors.append(model.get_word_vector(word))
    if vectors:
        return np.mean(vectors, axis=0)
    else:
        return np.zeros(model.get_dimension())

def compute_similarity(guess, words, model: fasttext.FastText._FastText, threshold=0.4):
    if not words or model is None:
        return []

    try:
        # TODO: keep embeddings in memory
        guess_vec = embed_text(guess, model)
        sims = []
        for idx, word_info in enumerate(words):
            # Skip revealed words
            if word_info['normalized'] in getattr(model, 'revealed', set()):
                continue

            word_vec = embed_text(word_info['text'], model)
            similarity = np.dot(guess_vec, word_vec) / (np.linalg.norm(guess_vec) * np.linalg.norm(word_vec))
            sims.append({'word': word_info['text'], 'similarity': float(similarity), 'index': idx})

        sims.sort(key=lambda x: x['similarity'], reverse=True)
        return [s for s in sims[:3] if s['similarity'] > threshold]

    except Exception as e:
        print("Error:", e)
        return []
