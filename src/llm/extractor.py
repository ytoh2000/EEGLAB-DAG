"""
Text extraction from PDFs and URLs for the LLM pipeline builder.

Provides functions to extract article text from:
- Local PDF files (via PyMuPDF)
- Web URLs (via requests + BeautifulSoup)
- Methods section detection (heuristic keyword search)
"""
import re


def extract_from_pdf(path: str) -> str:
    """Extract all text from a PDF file.
    
    Args:
        path: Path to the PDF file.
    Returns:
        Full text content of the PDF.
    Raises:
        ImportError: If PyMuPDF is not installed.
        FileNotFoundError: If path does not exist.
    """
    import fitz  # PyMuPDF
    
    doc = fitz.open(path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return '\n'.join(pages)


def extract_from_url(url: str) -> str:
    """Extract article text from a URL.
    
    Args:
        url: URL of the article.
    Returns:
        Extracted text content.
    Raises:
        ImportError: If requests/bs4 not installed.
        requests.RequestException: On network errors.
    """
    import requests
    from bs4 import BeautifulSoup
    
    headers = {'User-Agent': 'Mozilla/5.0 (EEGLAB-DAG Research Tool)'}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove scripts, styles, nav, footer
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    # Try to find article body
    article = soup.find('article') or soup.find('div', class_=re.compile(r'article|content|paper|main', re.I))
    if article:
        return article.get_text(separator='\n', strip=True)
    
    # Fallback: just get body text
    body = soup.find('body')
    if body:
        return body.get_text(separator='\n', strip=True)
    return soup.get_text(separator='\n', strip=True)


# Common section header patterns in EEG papers
_METHODS_PATTERNS = [
    r'(?:^|\n)\s*(?:\d+\.?\s*)?(?:Materials?\s*(?:and|&)\s*)?Methods?\s*\n',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?EEG\s+(?:Pre)?processing\s*\n',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?Data\s+(?:Analysis|Acquisition|Processing)\s*\n',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?Signal\s+Processing\s*\n',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?Experimental\s+(?:Setup|Procedure|Design)\s*\n',
]

_END_PATTERNS = [
    r'(?:^|\n)\s*(?:\d+\.?\s*)?Results?\s*\n',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?Discussion\s*\n',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?Figures?\s*\n',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?Acknowledgement',
    r'(?:^|\n)\s*(?:\d+\.?\s*)?References?\s*\n',
]


def extract_methods_section(full_text: str) -> str:
    """Extract the Methods / EEG Processing section from article text.
    
    Uses heuristic keyword matching to find the section boundaries.
    Falls back to returning the full text if no methods section is found.
    
    Args:
        full_text: Full article text.
    Returns:
        Extracted methods section text, or full text as fallback.
    """
    # Find the start of the methods section
    best_start = -1
    for pattern in _METHODS_PATTERNS:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            if best_start == -1 or match.start() < best_start:
                best_start = match.start()
    
    if best_start == -1:
        # No methods section found — return full text
        return full_text
    
    methods_text = full_text[best_start:]
    
    # Find the end of the methods section (start of next major section)
    best_end = len(methods_text)
    for pattern in _END_PATTERNS:
        match = re.search(pattern, methods_text, re.IGNORECASE)
        if match and match.start() > 50:  # Skip if too close to start
            if match.start() < best_end:
                best_end = match.start()
    
    return methods_text[:best_end].strip()
