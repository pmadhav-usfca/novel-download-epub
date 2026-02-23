#pyinstaller --onefile --noconsole --name "NovelDownloader" ../GUI_test.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
import re
from urllib.parse import urljoin

# --- SCRAPER LOGIC (Modified from your file) ---

class NovelScraper:
    def __init__(self, log_widget):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://novelfull.com/",
        })
        self.log_widget = log_widget

    def log(self, message):
        """Helper to push text to the GUI log window."""
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.see(tk.END)

    def get_book_info(self, url):
        response = self.session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.select_one("div.desc > h3.title").get_text(strip=True) if soup.select_one("div.desc > h3.title") else "Unknown"
        
        author = "Unknown"
        genres = []
        info_section = soup.select_one("div.info")
        if info_section:
            for div in info_section.find_all("div"):
                h3 = div.find("h3")
                if h3 and "Author" in h3.get_text():
                    author = div.find("a").get_text(strip=True) if div.find("a") else "Unknown"
                if h3 and "Genre" in h3.get_text():
                    genres = [a.get_text(strip=True) for a in div.find_all("a")]
        return title, author, genres

    def get_total_pages(self, url):
        response = self.session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        last_link = soup.select_one("ul.pagination li.last a")
        if last_link and "page=" in last_link["href"]:
            match = re.search(r"page=(\d+)", last_link["href"])
            return int(match.group(1)) if match else 1
        return 1

    def get_all_chapter_links(self, url):
        total_pages = self.get_total_pages(url)
        all_chapters = []
        for page in range(1, total_pages + 1):
            page_url = url if page == 1 else f"{url}?page={page}"
            self.log(f"Reading chapter list page {page}...")
            res = self.session.get(page_url, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            for link in soup.select("ul.list-chapter li a"):
                title = link.get_text(strip=True)
                full_url = urljoin(url, link["href"])
                match = re.search(r"chapter-(\d+)", full_url)
                if match:
                    all_chapters.append((int(match.group(1)), title, full_url))
        
        unique = {num: (t, u) for num, t, u in all_chapters}
        return sorted([(n, d[0], d[1]) for n, d in unique.items()], key=lambda x: x[0])

    def fetch_chapter(self, url):
        res = self.session.get(url, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        content_div = soup.find("div", id="chapter-content")
        for tag in content_div(["button", "script", "style"]): tag.decompose()
        return content_div.prettify()

# --- GUI APPLICATION ---

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("NovelFull to EPUB Downloader")
        self.root.geometry("600x500")

        # UI Elements
        frame = ttk.Frame(root, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Novel URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(frame, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, pady=5)

        ttk.Label(frame, text="Start Chapter:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.start_entry = ttk.Entry(frame, width=10)
        self.start_entry.insert(0, "1")
        self.start_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(frame, text="End Chapter:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.end_entry = ttk.Entry(frame, width=10)
        self.end_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="(Leave blank for all)").grid(row=2, column=2, sticky=tk.W)

        self.btn_run = ttk.Button(frame, text="Download Novel", command=self.start_download)
        self.btn_run.grid(row=3, column=0, columnspan=3, pady=20)

        self.log_area = scrolledtext.ScrolledText(frame, height=15, state='normal')
        self.log_area.grid(row=4, column=0, columnspan=3, sticky=tk.NSEW)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(4, weight=1)

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid URL")
            return
        
        # Run in a thread so the UI doesn't freeze
        self.btn_run.config(state=tk.DISABLED)
        threading.Thread(target=self.process, daemon=True).start()

    def process(self):
        scraper = NovelScraper(self.log_area)
        try:
            url = self.url_entry.get().strip()
            start = int(self.start_entry.get() or 1)
            end = int(self.end_entry.get()) if self.end_entry.get() else None

            scraper.log(f"Starting process for: {url}")
            book_name, author, genres = scraper.get_book_info(url)
            scraper.log(f"Found: {book_name} by {author}")

            all_chapters = scraper.get_all_chapter_links(url)
            filtered = [c for c in all_chapters if c[0] >= start and (end is None or c[0] <= end)]

            if not filtered:
                scraper.log("No chapters found in that range.")
                return

            scraper.log(f"Downloading {len(filtered)} chapters...")
            
            epub_book = epub.EpubBook()
            epub_book.set_title(book_name)
            epub_book.add_author(author)
            for g in genres: epub_book.add_metadata('DC', 'subject', g)

            epub_chapters = []
            for i, (num, title, c_url) in enumerate(filtered):
                scraper.log(f"Fetching Chapter {num}: {title}")
                content = scraper.fetch_chapter(c_url)
                
                c = epub.EpubHtml(title=title, file_name=f"chap_{i}.xhtml")
                c.content = f"<h2>{title}</h2>{content}"
                epub_book.add_item(c)
                epub_chapters.append(c)

            epub_book.toc = tuple(epub_chapters)
            epub_book.spine = ["nav"] + epub_chapters
            epub_book.add_item(epub.EpubNcx())
            epub_book.add_item(epub.EpubNav())

            # --- FIXED SECTION FOR PYTHON 3.11 ---
            # We clean the filename first, then use it in the f-string
            clean_name = re.sub(r'[^\w\s-]', '', book_name).strip()
            filename = f"{clean_name}.epub"
            # -------------------------------------

            epub.write_epub(filename, epub_book)
            scraper.log(f"\nSUCCESS! Saved as {filename}")
            messagebox.showinfo("Done", f"Ebook saved as {filename}")

        except Exception as e:
            scraper.log(f"CRITICAL ERROR: {str(e)}")
        finally:
            self.btn_run.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()