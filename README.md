# novel-download-epub
Make it easier to download *free books* available from novelfull or wuxia world. Working to add more download locations and containarizing better.
<br>

# novelfull2epub.py - Most updated
Added load of functions to populate all the epub metadata and make user arguments better. \n
Run file with arguments: -s (start-chapter), -e (end-chapter), -url (actual book url)

## Example python command usage
```bash
python novelfull2epub_final.py -s 1 -e 100 -url "https://novelfull.com/embers-ad-infinitum.html"
```
### OR simpler for all chapters
```bash
python novelfull2epub_final.py -url "https://novelfull.com/embers-ad-infinitum.html"
```

# wuxia2epub.py - To be updated 
Works only on free books, not on locked chapters.
Run file with arguments: -b (book/file name) -s (start-chapter), -e (end-chapter), --base-url (actual book url)

## Example python command usage
```bash
python3 wuxia_cli.py \
 -b "MartialWorld" \
 -s 1 \
 -e 10 \
 --base-url "https://example.com/martial-world/chapter-"


