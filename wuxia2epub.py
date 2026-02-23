#python3 wuxia_cli.py \
#  -b "MartialWorld" \
#  -s 1 \
#  -e 10 \
#  --base-url "https://example.com/martial-world/chapter-"

import argparse
import requests
from bs4 import BeautifulSoup
from ebooklib import epub


def fetch_chapter(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    content_div = soup.find("div", class_="chapter-content")
    if not content_div:
        raise Exception("Could not find chapter content")

    # REMOVE ALL BUTTONS
    for button in content_div.find_all("button"):
        button.decompose()

    # REMOVE aria-hidden spans (the wrapper around button)
    for span in content_div.find_all("span", attrs={"aria-hidden": "true"}):
        span.decompose()

    return content_div.prettify()


def create_epub(book_name, chapters):
    book = epub.EpubBook()
    book.set_title(book_name)
    book.set_language("en")

    epub_chapters = []

    for i, (title, content) in enumerate(chapters):
        c = epub.EpubHtml(title=title, file_name=f"chap_{i}.xhtml")
        c.content = content
        book.add_item(c)
        epub_chapters.append(c)

    book.toc = tuple(epub_chapters)
    book.spine = ["nav"] + epub_chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(f"{book_name}.epub", book)
    print(f"\nSaved as {book_name}.epub")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--book", required=True)
    parser.add_argument("-s", "--start", type=int, required=True)
    parser.add_argument("-e", "--end", type=int, required=True)
    parser.add_argument("--base-url", required=True,
                        help="Base URL like https://site.com/book/chapter-")

    args = parser.parse_args()

    chapters = []

    for i in range(args.start, args.end + 1):
        url = f"{args.base_url}{i}"
        print(f"Fetching Chapter {i}...")

        try:
            content = fetch_chapter(url)
            chapters.append((f"Chapter {i}", content))
        except Exception as e:
            print(f"Failed at Chapter {i}: {e}")
            break

    create_epub(args.book, chapters)


if __name__ == "__main__":
    main()
