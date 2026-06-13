"""Test Naver Finance news scraping"""
import requests
from bs4 import BeautifulSoup

def test_naver_news(stock_code='005930'):
    url = f'https://finance.naver.com/item/news_news.nhn?code={stock_code}&page=1'

    print(f"Testing URL: {url}\n")

    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Response status: {response.status_code}\n")

    soup = BeautifulSoup(response.text, 'html.parser')

    # Test multiple selectors
    print("=== Testing selectors ===\n")

    # Test 1: .tb_cont tr
    selector1 = soup.select('.tb_cont tr')
    print(f"1. '.tb_cont tr' found: {len(selector1)} items")

    # Test 2: table.type5 tr
    selector2 = soup.select('table.type5 tr')
    print(f"2. 'table.type5 tr' found: {len(selector2)} items")

    # Test 3: Just table.type5
    selector3 = soup.select('table.type5')
    print(f"3. 'table.type5' found: {len(selector3)} tables\n")

    if selector2:
        print("=== Analyzing table.type5 tr structure ===\n")
        for i, item in enumerate(selector2[:5]):  # First 5 items
            print(f"--- Item {i+1} ---")

            # Try different title selectors
            title1 = item.select_one('.title a')
            title2 = item.select_one('td a')
            title3 = item.select_one('a[href*="news"]')

            print(f"  .title a: {title1.text.strip() if title1 else 'NOT FOUND'}")
            print(f"  td a: {title2.text.strip() if title2 else 'NOT FOUND'}")
            print(f"  a[href*=news]: {title3.text.strip() if title3 else 'NOT FOUND'}")

            # Try date selectors
            date1 = item.select_one('.date')
            date2 = item.select_one('td.date')
            date3 = item.select_one('span.date')

            print(f"  .date: {date1.text.strip() if date1 else 'NOT FOUND'}")
            print(f"  td.date: {date2.text.strip() if date2 else 'NOT FOUND'}")
            print(f"  span.date: {date3.text.strip() if date3 else 'NOT FOUND'}")
            print()

if __name__ == '__main__':
    test_naver_news()
