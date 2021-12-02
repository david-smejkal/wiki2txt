# wiki2txt

**ANNOUNCEMENT:** v0.3.1 isn't parsing latest wikidumps with python v2.7 for some reason this problem is worked on and will be fixed asap.

A tool to extract plaintext, links and categories from `wikidumps` (https://dumps.wikimedia.org/enwiki/).<br />
Designed to prepare "digestible food" (cleaner data) for AI learning software.<br />

Written in Python, utilizes `lxml` parser and leans heavily on the powers of the `re` (regex) library.

# Installation
Optional: Use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to create your virtual environment
```csharp
$ mkproject --python="`which python2`" wiki2txt
$ workon wiki2txt
(wiki2txt) $ pip install -r requirements.txt
```

# Usage
```csharp
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
  -T, --test                      Parse arbitrary text from stdin. Use Ctrl + D to signify end of input.
```

# Output Format
```xml
<article>
  <id>ID</id>
  <title>TITLE</title>
  <text>PLAINTEXT</text>
  <categories>CATEGORIES</categories>
</article>
```

# Examples

## Quick example
```console
(wiki2txt) $ wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles1.xml-p1p41242.bz2 # Download: 234 MB
(wiki2txt) $ bzip2 -d enwiki-latest-pages-articles1.xml-p1p41242.bz2 # Decompress: 893 MB
(wiki2txt) $ wiki2txt.py -t -i enwiki-latest-pages-articles1.xml-p1p41242.bz2 -o latest-pages-articles1-parsed.xml
```

## Download
**HINT:** add `--continue` parameter if you need to resume the download
```csharp
$ wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2
```

## Decompress
**HINT:** add `-k` parameter if you want to preserve the original archive
```console
$ bzip2 -d enwiki-latest-pages-articles.xml.bz2
```

## Parse
```shell-session
(wiki2txt) $ python wiki2txt.py -t -i enwiki-latest-pages-articles.xml -o latest-food.xml
```

# v0.3.1 vanilla release
As delivered in 2008. Works with Python v2.
