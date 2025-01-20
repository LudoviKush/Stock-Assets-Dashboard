import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scrape_soldionline():
    news_items = []
    url = 'https://www.soldionline.it/'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'html.parser')
        approfondimenti_section = soup.find('div', class_='approfondimenti')
        if approfondimenti_section:
            links = approfondimenti_section.find_all('a', href=True)
            for link in links:
                title = link.get_text(strip=True)
                href = urljoin(url, link['href'])
                if title:  # Check if title is not empty
                    news_items.append({'title': title, 'link': href, 'source': 'Soldionline'})
    except requests.exceptions.RequestException as e:
        print(f"Error scraping Soldionline: {e}")
    return news_items

def scrape_milanofinanza():
    news_items = []
    url = 'https://www.milanofinanza.it/'
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all divs with class 'correlated-articles'
        correlated_articles_sections = soup.find_all('div', class_='correlated-articles')
        
        for section in correlated_articles_sections:
            # Find all links within each 'correlated-articles' section
            links = section.find_all('a', href=True)
            for link in links:
                title = link.get_text(strip=True)
                href = urljoin(url, link['href'])
                if title:
                    news_items.append({'title': title, 'link': href, 'source': 'Milanofinanza'})

    except requests.exceptions.RequestException as e:
        print(f"Error scraping Milanofinanza: {e}")
    return news_items

def scrape_ilsole24ore():
    news_items = []
    url = 'https://www.ilsole24ore.com/sez/finanza'
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all elements with class 'aprev-title'
        aprev_title_elements = soup.find_all(class_='aprev-title')

        for element in aprev_title_elements:
            link = element.find('a', href=True)  # Find the <a> tag within
            if link:
                title = link.get_text(strip=True)
                href = urljoin(url, link['href'])
                if title:
                    news_items.append({'title': title, 'link': href, 'source': 'IlSole24Ore'})

    except requests.exceptions.RequestException as e:
        print(f"Error scraping IlSole24Ore: {e}")
    return news_items

if __name__ == '__main__':
    soldionline_news = scrape_soldionline()
    milanofinanza_news = scrape_milanofinanza()
    ilsole24ore_news = scrape_ilsole24ore()

    print("Soldionline News:")
    for news in soldionline_news:
        print(f"  Title: {news['title']}")
        print(f"  Link: {news['link']}")
        print(f"  Source: {news['source']}")
        print("-" * 20)

    print("\nMilanofinanza News:")
    for news in milanofinanza_news:
        print(f"  Title: {news['title']}")
        print(f"  Link: {news['link']}")
        print(f"  Source: {news['source']}")
        print("-" * 20)

    print("\nIlSole24Ore News:")
    for news in ilsole24ore_news:
        print(f"  Title: {news['title']}")
        print(f"  Link: {news['link']}")
        print(f"  Source: {news['source']}")
        print("-" * 20)
