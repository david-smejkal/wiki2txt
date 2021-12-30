# wiki2txt
A tool to extract plain (unformatted) text, redirects, links and categories from wikipedia backups (dumps).<br />
Designed to prepare clean training data for AI training / Machine Learning software.<br />

Written in Python, utilizes `lxml` SAX (memory efficient) parser and leans heavily on the powers of the `re` library.<br /><br />
![wiki2txt demo](https://smejkal.software/img/wiki2txt-demo.gif)

[Wiki XML dumps](https://dumps.wikimedia.org/backup-index-bydb.html):
- [https://dumps.wikimedia.org/enwiki/](https://dumps.wikimedia.org/enwiki/) (English)
- [https://dumps.wikimedia.org/ruwiki/](https://dumps.wikimedia.org/ruwiki/) (Russian)
- [https://dumps.wikimedia.org/zhwiki/](https://dumps.wikimedia.org/zhwiki/) (Chinese)

# Installation
Supported Python versions: `2.7+`, `3.4+`<br />
```csharp
$ mkproject wiki2txt
(wiki2txt) $ git clone https://github.com/david-smejkal/wiki2txt.git .
(wiki2txt) $ pip install -r requirements.txt
```
*Optional: Install and configure [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to use `mkproject` to create your virtual environment.*

# Usage
```csharp
(wiki2txt) $ python wiki2txt.py --help
Usage: wiki2txt.py [options]

Options:
  --version                    show program's version number and exit
  -h, --help                   show this help message and exit
  -i FILE, --input-file=FILE   take xml input from FILE otherwise from STDIN
  -o FILE, --output-file=FILE  output parsed articles to FILE otherwise to STDOUT
  -n, --no-text                don't parse text (designed for use with -r -l -c options)
  -t, --text                   produce plain (unformatted) text (DEFAULT)
  -s NUMBER, --skip=NUMBER     skip (resume after) NUMBER of articles (appends to output files)
  -q, --quiet                  stop making noise
  -R, --references             retain references in text (links and categories)
  -r FILE, --redirects=FILE    outsource redirect articles to the FILE
  -l FILE, --links=FILE        capture articles' links in the FILE
  -c FILE, --categories=FILE   capture articles' categories in the FILE
  -T, --test                   test by parsing directly from STDIN (bypasses lxml parser)
```

# Output Format
```xml
<article>
  <id>12</id>
  <title>Anarchism</title>
  <text>Anarchism is a political philosophy ...</text>
</article>
```

# Performance
> Tested with one core of Intel i7 1.8 GHz processor

`Python v3.9` - Wikidump data processing speed of `7.6 MB/s`<br />
`Python v2.7` - Wikidump data processing speed of `5.2 MB/s`<br />
*NOTICE: Processing with Python `v3` is about 46% faster than with `v2`.* <br />

Based on above it should take roughly 3 hours to process the latest `en` wikidump (81GB of decompressed data).

# Examples

## Download => Decompress => Parse
```console
(wiki2txt) $ wget -O articles1.xml.bz2 https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles1.xml-p1p41242.bz2 # 234 MB
(wiki2txt) $ bzip2 --decompress articles1.xml.bz2 # 893 MB
(wiki2txt) $ python wiki2txt.py -i articles1.xml -o parsed.xml -r redirects.edg # 400 MB
```

## Download latest complete wikidump
```csharp
$ wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2 # 18 GB
```
**HINT:** add `--continue` parameter if you need to resume the download

## Decompress
```console
$ bzip2 --decompress enwiki-latest-pages-articles.xml.bz2 # 81 GB
```
**HINT:** add `-k` parameter if you want to preserve the original archive

## Parse
```shell-session
(wiki2txt) $ python wiki2txt.py -i enwiki-latest-pages-articles.xml -o clean-data.xml
```
