import requests
from bs4 import BeautifulSoup
from readability import Document


def get_article_content(url):
    response = requests.get(url)
    doc = Document(response.text)
    soup = BeautifulSoup(doc.summary(), "html.parser")
    title = doc.title()
    text = soup.get_text()
    return text, title
