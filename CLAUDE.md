# unlimited-pedantix

Offline clone of [Pedantix](https://pedantix.certitudes.org/): players guess words from a hidden Wikipedia article, with semantic similarity clues via FastText embeddings. After each game, users rate candidate articles to train an XGBoost/RandomForest classifier that improves future article selection.

## How to run

```bash
uv sync
uv run streamlit run src/web_viewer.py
```

## Key files

- `src/web_viewer.py` — Streamlit entry point, all UI state via `SessionState`
- `src/game/game_logic.py` — article loading (`load_game`) and guess handling (`process_guess`, `handle_guess`)
- `src/game/embedding_utils.py` — FastText tokenization, normalization, cosine similarity
- `src/game/wiki_api.py` — Wikipedia API calls, HTML extraction, LaTeX → plain text
- `src/game/classifier.py` — sentence-transformer embeddings + sklearn/XGBoost models to rank articles
- `src/ui/display_article.py` — HTML rendering of the masked article
- `src/config.py` — all tuneable parameters (article count, similarity threshold, model choice)
- `data/dataset.json` — accumulated user ratings used to train the classifier
- `vocab/words_{fr,en}.txt` — word lists for spell-correction via `difflib`

## Dev

```bash
pre-commit install   # set up ruff lint + format hooks
```
