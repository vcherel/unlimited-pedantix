"""Parameters"""

NB_ARTICLES = 100                # Number of articles we fetch in total for one game (the best one is kept)
NB_ARTICLES_CLASSIFIER = 10      # Number of top articles from which the classifier will choose
NB_DAYS = 30                     # Number of days we will count the views
MIN_WORDS = 250                  # Minimum number of words in an article
SIMILARITY_THRESHOLD = 0.4       # Minimum similarity to show clue

# Words to exclude at the beginning of wikipedia paragraph
EXCLUDE_STARTS = [
    "Vous lisez un",
    "Cet article est une",
    "Pour les articles",
    "modifier",
    "Cet article ne",
    "Si vous disposez",
    "Pour des articles plus généraux",
    "Pour un article plus général",
    "Cet article est orphelin",
    "Ne pas confondre avec",
    "Ne doit pas être confondu avec",
    "Cet article concerne",
    "N.B."
]

if NB_ARTICLES < NB_ARTICLES_CLASSIFIER:
    raise Exception("NB_ARTICLES should be bigger than NB_ARTICLES_CLASSIFIER")