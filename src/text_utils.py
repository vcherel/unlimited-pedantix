import unicodedata
import numpy as np
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

def compute_similarity(guess, words, model, threshold=0.4):
    if not words or model is None:
        return []
    try:
        guess_embedding = model.encode([guess])[0]
        sims = []
        for word_info in words:
            if word_info['normalized'] not in getattr(model, 'revealed', set()):
                word_embedding = model.encode([word_info['text']])[0]
                similarity = np.dot(guess_embedding, word_embedding) / (np.linalg.norm(guess_embedding) * np.linalg.norm(word_embedding))
                sims.append({'word': word_info['text'], 'similarity': float(similarity), 'index': words.index(word_info)})
        sims.sort(key=lambda x: x['similarity'], reverse=True)
        return [s for s in sims[:3] if s['similarity'] > threshold]
    except:
        return []
