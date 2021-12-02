# wiki2txt
A tool to extract plaintext, links and categories from `wikidumps` (https://dumps.wikimedia.org/enwiki/).<br />
Designed to prepare "digestible food" (cleaner data) for AI learning software.<br />

Written in Python, utilizes `lxml` parser and leans heavily on the powers of the `re` (regex) library.

# Installation
Optional: Use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to create your virtual environment
```
$ mkproject --python="`which python2`" wiki2txt
$ workon wiki2txt
(wiki2txt) $ pip install -r requirements.txt
```

# Usage
```
(wiki2txt) $ python wiki2txt.py --help
Usage: wiki2txt.py [options]

Options:
  --version                       show program's version number and exit
  -h, --help                      show this help message and exit
  -i FILE, --input-file=FILE      Intput xml text will come from FILE otherwise from STDIN.
  -o FILE, --output-file=FILE     Output text will go to FILE otherwise to STDOUT.
  -t, --text                      Parse text from wikidump (xml output format).
  -n, --no-text                   Don't parse text from wikidump (DEFAULT).
  -s NUMBER, --skip=NUMBER        Skip NUMBER articles.
  -q, --quiet                     Don't make noise.
  -R, --references                Print references in text (links and categories).
  -r PREFIX, --redirects=PREFIX   Parse redirects (make "PREFIX.edg" file).
  -l PREFIX, --links=PREFIX       Parse links (make "PREFIX.edg" file).
  -c PREFIX, --categories=PREFIX  Parse categories (make "PREFIX.edg" file).
  -T, --test                      Parse arbitrary text from stdin.
```

# Examples

## Download the latest wiki dump
HINT: add `--continue` parameter if you need to resume the download
```
$ wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2
```

## Decompress a bz2 wiki dump
HINT: add `-k` parameter if you want to preserve the original archive
```
$ bzip2 -d enwiki-latest-pages-articles.xml.bz2
```

## Parse a wiki dump to get food for AI
```
(wiki2txt) $ python wiki2txt -i enwiki-latest-pages-articles.xml -o latest-food.xml
```

# v0.3.1 vanilla release
As delivered in 2008. Works with Python v2.
