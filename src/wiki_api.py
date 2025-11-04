from datetime import datetime, timedelta
import traceback
from urllib.parse import quote
from bs4 import BeautifulSoup
import requests
import re

from classes import WikipediaPage
from config import EXCLUDE_STARTS, MIN_WORDS, NB_DAYS


headers = {"User-Agent": "PedantixGame/1.0"}

def fetch_random_title(language):
    """Fetch a random Wikipedia page title for a given language"""
    url = f"https://{language}.wikipedia.org/api/rest_v1/page/random/summary"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['title']

def fetch_page_views(language, title):
    """Get total page views in the last NB_DAYS days for a Wikipedia page"""
    try:
        # Constructe url
        encoded_title = quote(title)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=NB_DAYS)
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{language}.wikipedia/all-access/all-agents/{encoded_title}/daily/{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # Sum daily views to get total views for last NB_DAYS days
            return sum(item.get('views', 0) for item in response.json().get('items', []))
        return 0

    except Exception as e:
        print(f"Error in load_game: {e}")
        traceback.print_exc()
        return 0

def fetch_wikipedia_content(title, language):
    """Fetch the HTML content of a Wikipedia page"""
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {'action': 'parse', 'format': 'json', 'page': title, 'prop': 'text', 'redirects': 1}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    if 'error' in data:
        raise Exception(f"Page not found: {data['error']['info']}")
    parse_obj = data['parse']
    title = parse_obj['title']
    clean_title = re.sub(r'\s*\(.*?\)', '', title)

    return WikipediaPage(
        title=clean_title,
        text=parse_obj['text']['*'],
        url=f"https://{language}.wikipedia.org/wiki/{quote(parse_obj['title'])}"
        )

def is_good_paragraph(p):
    text: str = p.get_text().strip()
    word_count = len(text.split())

    # Basic checks
    if word_count < 10:
        return False

    # Exclude any paragraph inside an infobox, sidebar, navbox, or metadata table
    if p.find_parent(["table", "div"], class_=re.compile(r"(infobox|navbox|metadata|vcard|sidebar)")):
        return False

    # Exclude common unwanted starts
    if any(text.lower().startswith(start.lower()) for start in EXCLUDE_STARTS):
        return False

    # Skip "redirige ici" notes
    if "redirige ici. Pour" in text:
        return False

    # Skip audio/Écouter links
    if any(a.get_text().strip() == "Écouter" for a in p.find_all("a")):
        return False

    return True


def extract_first_paragraphs(html_content, min_words=MIN_WORDS):
    """Extract text from the first paragraphs of HTML content until reaching MIN_WORDS"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove unwanted tags
    for tag in soup.find_all(['style', 'script', 'sup']):
        tag.decompose()
    for tag in soup.find_all('a'):
        if tag.get('href', '').startswith('#cite'):
            tag.decompose()
    
    paragraphs = []
    total_words = 0

    for p in soup.find_all('p'):
        if is_good_paragraph(p):
            text = re.sub(r'\s+', ' ', re.sub(r'\[\d+\]|\[citation needed\]', '', p.get_text(), flags=re.IGNORECASE)).strip()
            word_count = len(text.split())
            paragraphs.append(text)
            total_words += word_count
            
            if total_words >= min_words:
                break
    
    text = '\n'.join(paragraphs)
    print(f"{text}")
    return text
