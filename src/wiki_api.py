from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
import requests
import re

from config import USER_AGENT, MAX_PARAGRAPHS

def fetch_random_title(language):
    url = f"https://{language}.wikipedia.org/api/rest_v1/page/random/summary"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['title']

def fetch_page_views(language, title):
    try:
        encoded_title = quote(title)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{language}.wikipedia/all-access/all-agents/{encoded_title}/daily/{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return sum(item.get('views', 0) for item in response.json().get('items', []))
        return 0
    except:
        return 0

def fetch_wikipedia_content(title, language):
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {'action': 'parse', 'format': 'json', 'page': title, 'prop': 'text', 'redirects': 1}
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    if 'error' in data:
        raise Exception(f"Page not found: {data['error']['info']}")
    parse_obj = data['parse']
    return {
        'title': parse_obj['title'],
        'html': parse_obj['text']['*'],
        'url': f"https://{language}.wikipedia.org/wiki/{quote(parse_obj['title'])}"
    }

def extract_first_paragraphs(html_content, max_paragraphs=MAX_PARAGRAPHS):
    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup.find_all(['style', 'script', 'sup']):
        tag.decompose()
    for tag in soup.find_all('a'):
        if tag.get('href', '').startswith('#cite'):
            tag.decompose()
    paragraphs = []
    for p in soup.find_all('p'):
        text = re.sub(r'\s+', ' ', re.sub(r'\[\d+\]|\[citation needed\]', '', p.get_text(), flags=re.IGNORECASE)).strip()
        if len(text) > 50:
            paragraphs.append(text)
        if len(paragraphs) >= max_paragraphs:
            break
    return ' '.join(paragraphs)
