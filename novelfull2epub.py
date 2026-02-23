## Command to download the book - 
# python novelfull2epub_final.py -url "https://novelfull.com/embers-ad-infinitum.html"
#Who let him cultivate - wuxia world
#Only at the Mahayana Stage Does the Reversal System Appear Novel


import argparse
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
import re
import time
from urllib.parse import urljoin

# ---------------- SESSION ---------------- #

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://novelfull.com/",
    "Connection": "keep-alive",
})

# ---------------- HELPERS ---------------- #

def get_book_info(novel_main_url):
    """Fetch book title, author, and all genres from the novel page."""
    response = session.get(novel_main_url, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # --- Title ---
    title_tag = soup.select_one("div.desc > h3.title")
    book_title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

    # --- Author ---
    author_name = "Unknown Author"
    author_section = soup.select_one("div.info")
    if author_section:
        for div in author_section.find_all("div"):
            h3 = div.find("h3")
            if h3 and "Author" in h3.get_text():
                a = div.find("a")
                if a:
                    author_name = a.get_text(strip=True)

    # --- Genres (multiple) ---
    genres = []
    if author_section:
        # find the div where h3 contains "Genre"
        for div in author_section.find_all("div"):
            h3 = div.find("h3")
            if h3 and "Genre" in h3.get_text():
                for a in div.find_all("a"):
                    genres.append(a.get_text(strip=True))
                break

    return book_title, author_name, genres

# def get_book_name(novel_main_url):
#     """Fetch book name/title from the main novel page."""
#     response = session.get(novel_main_url, timeout=15)
#     response.raise_for_status()
#     soup = BeautifulSoup(response.text, "html.parser")

#     # novelfull.com usually has <h3 class="novel-title">Book Name</h3>
#     title_tag = soup.select_one("h3.title")
#     if title_tag:
#         return title_tag.get_text(strip=True)

#     raise Exception("Could not detect book title from URL.")


def extract_chapter_number(url):
    match = re.search(r"chapter-(\d+)", url)
    if match:
        return int(match.group(1))
    return None


def get_total_pages(novel_main_url):
    response = session.get(novel_main_url, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    last_link = soup.select_one("ul.pagination li.last a")

    if last_link and "page=" in last_link["href"]:
        match = re.search(r"page=(\d+)", last_link["href"])
        if match:
            return int(match.group(1))

    return 1  # if no pagination


def get_all_chapter_links(novel_main_url):
    print("Collecting all chapter links (handling pagination)...")

    total_pages = get_total_pages(novel_main_url)
    print(f"Detected {total_pages} chapter list pages.")

    all_chapters = []

    for page in range(1, total_pages + 1):
        if page == 1:
            page_url = novel_main_url
        else:
            page_url = f"{novel_main_url}?page={page}"

        print(f"Reading page {page}...")

        response = session.get(page_url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.select("ul.list-chapter li a")

        for link in links:
            title = link.get_text(strip=True)
            full_url = urljoin(novel_main_url, link["href"])
            number = extract_chapter_number(full_url)

            if number:
                all_chapters.append((number, title, full_url))

    if not all_chapters:
        raise Exception("No chapters found.")

    # Remove duplicates safely
    unique = {}
    for number, title, url in all_chapters:
        unique[number] = (title, url)

    sorted_chapters = sorted(unique.items(), key=lambda x: x[0])
    # print (sorted_chapters) ##

    return [(num, data[0], data[1]) for num, data in sorted_chapters]


def fetch_chapter(url):
    response = session.get(url, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    content_div = soup.find("div", id="chapter-content")

    if not content_div:
        raise Exception("Could not find chapter content")

    # Clean unwanted elements
    for tag in content_div(["button", "script", "style"]):
        tag.decompose()

    for span in content_div.find_all("span", attrs={"aria-hidden": "true"}):
        span.decompose()

    return content_div.prettify()


def create_epub(book_name, chapters, author_name="Unknown", genres=None):
    book = epub.EpubBook()
    book.set_title(book_name)
    book.set_language("en")
    book.add_author(author_name)

    # add each genre as a Dublin Core 'subject'
    if genres:
        for g in genres:
            book.add_metadata('DC', 'subject', g)

    epub_chapters = []
    for i, (title, content) in enumerate(chapters):
        c = epub.EpubHtml(title=title, file_name=f"chap_{i}.xhtml")
        c.content = f"<h2>{title}</h2>{content}"
        book.add_item(c)
        epub_chapters.append(c)

    book.toc = tuple(epub_chapters)
    book.spine = ["nav"] + epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(f"{book_name}.epub", book)
    print(f"\nSaved as {book_name}.epub by {author_name} (Genres: {', '.join(genres)})")


# ---------------- MAIN ---------------- #

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", type=int, required=False, default = 1, help="Chapter start # (default = 1")
    parser.add_argument("-e", "--end", type=int, required=False)
    parser.add_argument("-url", "--base-url", required=True,
                        help="Base URL like https://novelfull.com/48-hours-a-day.html")

    args = parser.parse_args()

    # Derive main novel page
    novel_main_url = args.base_url
    start = args.start
    end = args.end

    #Book Title info
    book_name, author_name, genres = get_book_info(novel_main_url)
    print(f"Detected book title: {book_name}")
    print(f"Detected author: {author_name}")
    print(f"Detected genres: {genres}")
    
    

    # Fetch all chapter links
    chapters = []
    all_chapters = get_all_chapter_links(args.base_url)
    
    # Filter by start/end
    filtered = [
        (num, title, url)
        for num, title, url in all_chapters
        if num >= start and (end is None or num <= end)
    ]
    
    if not filtered:
        print("No chapters found in selected range.")
        return
    
    print(f"\nDownloading from Chapter {filtered[0][0]} to {filtered[-1][0]}")
    
    for num, title, url in filtered:
        print(f"Fetching Chapter {title}...")
    
        try:
            content = fetch_chapter(url)
            chapters.append((title, content))
        except Exception as e:
            print(f"Failed at Chapter {num}: {e}")
            break

    create_epub(book_name, chapters, author_name, genres)


if __name__ == "__main__":
    main()