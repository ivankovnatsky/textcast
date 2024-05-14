import requests
from bs4 import BeautifulSoup
from readability import Document


def fetch_article(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def extract_main_content(html):
    doc = Document(html)
    soup = BeautifulSoup(doc.summary(), "html.parser")
    paragraphs = soup.find_all("p")
    content = " ".join(p.get_text() for p in paragraphs)
    return content


def get_article_content(url):
    html = fetch_article(url)
    main_content = extract_main_content(html)
    return main_content
