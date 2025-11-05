from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
import traceback
import requests
import aiohttp
import re

from classes import WikipediaPage
from config import EXCLUDE_STARTS, MIN_WORDS, NB_DAYS


headers = {"User-Agent": "PedantixGame/1.0"}

async def fetch_random_title(session: aiohttp.ClientSession, language: str) -> str:
    """Fetch a random Wikipedia page title asynchronously for a given language."""
    url = f"https://{language}.wikipedia.org/api/rest_v1/page/random/summary"
    
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        data = await response.json()
        return data['title']

async def fetch_page_views(session: aiohttp.ClientSession, language: str, title: str) -> int:
    """Get total page views in the last NB_DAYS days for a Wikipedia page asynchronously."""
    try:
        encoded_title = quote(title, safe='')
        end_date = datetime.now()
        start_date = end_date - timedelta(days=NB_DAYS)
        
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"{language}.wikipedia/all-access/all-agents/{encoded_title}/daily/"
            f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"
        )

        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return sum(item.get('views', 0) for item in data.get('items', []))
            return 0
    except Exception:
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

def latex_to_plain(text):
    """Convert LaTeX mathematical expressions to readable plain text"""
    
    # Remove display style commands
    text = re.sub(r'\\displaystyle\s*', '', text)
    text = re.sub(r'\\textstyle\s*', '', text)
    text = re.sub(r'\\scriptstyle\s*', '', text)
    
    # Handle fractions: \frac{a}{b} or \dfrac{a}{b} -> (a/b)
    def replace_frac(match):
        num = match.group(1)
        den = match.group(2)
        return f"({num}/{den})"
    text = re.sub(r'\\d?frac\{([^{}]+)\}\{([^{}]+)\}', replace_frac, text)
    
    # Handle square roots: \sqrt{x} -> √x or sqrt(x)
    text = re.sub(r'\\sqrt\{([^{}]+)\}', r'√\1', text)
    
    # Handle superscripts: x^{2} or x^2 -> x²
    superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', 
                       '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
                       'n': 'ⁿ', 'i': 'ⁱ', '+': '⁺', '-': '⁻', '=': '⁼'}
    def replace_superscript(match):
        exp = match.group(1).strip('{}')
        if len(exp) == 1 and exp in superscript_map:
            return superscript_map[exp]
        return f"^({exp})"
    text = re.sub(r'\^(\{[^{}]+\}|\S)', replace_superscript, text)
    
    # Handle subscripts: x_{i} or x_i -> xᵢ
    subscript_map = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
                     '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
                     'i': 'ᵢ', 'j': 'ⱼ', 'n': 'ₙ', 'a': 'ₐ', 'e': 'ₑ',
                     'o': 'ₒ', 'x': 'ₓ'}
    def replace_subscript(match):
        sub = match.group(1).strip('{}')
        if len(sub) == 1 and sub in subscript_map:
            return subscript_map[sub]
        return f"_({sub})"
    text = re.sub(r'_(\{[^{}]+\}|\S)', replace_subscript, text)
    
    # Greek letters
    greek_map = {
        'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε',
        'zeta': 'ζ', 'eta': 'η', 'theta': 'θ', 'iota': 'ι', 'kappa': 'κ',
        'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ', 'pi': 'π',
        'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'phi': 'φ', 'chi': 'χ',
        'psi': 'ψ', 'omega': 'ω',
        'Gamma': 'Γ', 'Delta': 'Δ', 'Theta': 'Θ', 'Lambda': 'Λ', 'Xi': 'Ξ',
        'Pi': 'Π', 'Sigma': 'Σ', 'Phi': 'Φ', 'Psi': 'Ψ', 'Omega': 'Ω'
    }
    for latex, unicode in greek_map.items():
        text = re.sub(r'\\' + latex + r'\b', unicode, text)
    
    # Common math symbols
    text = re.sub(r'\\infty\b', '∞', text)
    text = re.sub(r'\\sum\b', '∑', text)
    text = re.sub(r'\\prod\b', '∏', text)
    text = re.sub(r'\\int\b', '∫', text)
    text = re.sub(r'\\partial\b', '∂', text)
    text = re.sub(r'\\nabla\b', '∇', text)
    text = re.sub(r'\\cdot\b', '·', text)
    text = re.sub(r'\\times\b', '×', text)
    text = re.sub(r'\\pm\b', '±', text)
    text = re.sub(r'\\leq\b', '≤', text)
    text = re.sub(r'\\geq\b', '≥', text)
    text = re.sub(r'\\neq\b', '≠', text)
    text = re.sub(r'\\approx\b', '≈', text)
    text = re.sub(r'\\equiv\b', '≡', text)
    text = re.sub(r'\\in\b', '∈', text)
    text = re.sub(r'\\subset\b', '⊂', text)
    text = re.sub(r'\\subseteq\b', '⊆', text)
    text = re.sub(r'\\cup\b', '∪', text)
    text = re.sub(r'\\cap\b', '∩', text)
    text = re.sub(r'\\emptyset\b', '∅', text)
    text = re.sub(r'\\forall\b', '∀', text)
    text = re.sub(r'\\exists\b', '∃', text)
    text = re.sub(r'\\rightarrow\b', '→', text)
    text = re.sub(r'\\Rightarrow\b', '⇒', text)
    text = re.sub(r'\\leftarrow\b', '←', text)
    text = re.sub(r'\\Leftarrow\b', '⇐', text)
    
    # Remove remaining backslashes and braces
    text = re.sub(r'\\[a-zA-Z]+\s*', '', text)
    text = re.sub(r'[{}]', '', text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def extract_first_paragraphs(html_content, min_words=MIN_WORDS):
    """Extract text from the first paragraphs of HTML content until reaching MIN_WORDS"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted tags
    for tag in soup.find_all(['style', 'script', 'sup']):
        tag.decompose()
    for tag in soup.find_all('a'):
        if tag.get('href', '').startswith('#cite'):
            tag.decompose()
    
    # Handle math formulas in spans with class 'mwe-math-element'
    for math_span in soup.find_all('span', class_='mwe-math-element'):
        # Try to get the LaTeX from img alt text or annotation
        latex_text = ''
        img = math_span.find('img')
        if img and img.get('alt'):
            latex_text = img.get('alt')
        elif math_span.find('annotation'):
            latex_text = math_span.find('annotation').get_text()
        
        if latex_text:
            plain_math = latex_to_plain(latex_text)
            math_span.replace_with(plain_math)
    
    paragraphs = []
    total_words = 0
    for p in soup.find_all('p'):
        if is_good_paragraph(p):
            text = p.get_text()
            # Remove citation markers
            text = re.sub(r'\[\d+\]|\[citation needed\]', '', text, flags=re.IGNORECASE)
            # Apply additional LaTeX cleanup in case there's any remaining
            text = latex_to_plain(text)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            word_count = len(text.split())
            paragraphs.append(text)
            total_words += word_count
            
            if total_words >= min_words:
                break
    
    text = '\n'.join(paragraphs)
    print(f"{text}")
    return text
