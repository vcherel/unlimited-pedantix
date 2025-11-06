# Unlimited Pedantix

This game is an offline version of [Pedantix](https://pedantix.certitudes.org/), a daily word puzzle by [Enigmatix](https://x.com/enigmathix).

In the original, a random Wikipedia page is selected each day. Players guess words, which are revealed if they appear in the article; similar words also provide clues. However, you can only play one page per day.

To overcome this limitation, I created my own version: **Unlimited Pedantix**, offering endless puzzles to solve.

<img src="assets/game.png" alt="Gameplay" style="box-shadow: 4px 4px 10px rgba(0,0,0,0.3); display: block; margin: 0 auto;" width="600">

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

Simply run:
```bash
streamlit run src/main.py
```
A web navigator window will open with the game in it.

## Technical implemantation

To ensure engaging gameplay, the random Wikipedia page is selected through a quality-filtering process to avoids obscure pages while maintaining variety:
- An initial pool of 200 random articles is fetched.
- The system then selects the article with the highest number of visits over the past 30 days.

*The pool size and popularity metric can be adjusted in `src/config.py`.*

To detect semantically similar words, this implementation uses FastText instead of Word2Vec (used in the original game), offering two significant advantages:
- Performance: Faster processing and more efficient memory usage
- Vocabulary Coverage: Handles out-of-vocabulary words through subword embeddings, eliminating vocabulary limitations entirely

Typical FastText models weigh in at around 7GB, which is way too much for the needs of the project. To address this, I use a compressed version from [Zenodo](https://zenodo.org/records/4905385) by Bernhard Liebl. These embeddings were originally obtained from [fasttext.cc](https://fasttext.cc/docs/en/crawl-vectors.html) and compressed using the [compress-fasttext](https://github.com/avidale/compress-fasttext) library. The resulting model is just 20MB and downloads automatically when needed. We do lose some precision, especially on technical pages, but considering it's 350 times smaller than the original, that's a pretty good trade-off.
