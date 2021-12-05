#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

# standard libraries
import sys
import os
import re
import string
import optparse
import locale

# non-standard libraries
import lxml.etree # pip install lxml

# Marek Schmidt 2007, David Smejkal 2008.
  # Extraction of plain text from wikidumps (cca 10GB xml files).
  # Extraction of links/categories.

# XML OUTPUT FORMAT
  #<article>
  #<id>ID</id>
  #<title>TITLE</title>
  #<text>PLAINTEXT</text>
  #</article>
  #<article>
  #...

# extended:
#   ru-sib,
LANG_ARRAY = set(\
['aa', 'ab', 'af', 'ak', 'aln', 'als', 'am', 'an', 'ang', 'ar', 'arc', 'arn', 'arz', 'as', 'ast', 'av', 'avk', 'ay', 'az', 'ba', 'bar', 'bat-smg', 'bcc', 'bcl', 'be', 'be-tarask', 'be-x-old', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'bpy', 'br', 'bs', 'bto', 'bug', 'bxr', 'ca', 'cbk-zam', 'cdo', 'ce', 'ceb', 'ch', 'cho', 'chr', 'chy', 'co', 'cr', 'crh', 'crh-latn', 'crh-cyrl', 'cs', 'csb', 'cu', 'cv', 'cy', 'da', 'de', 'de-formal', 'diq', 'dk', 'dsb', 'dv', 'dz', 'ee', 'el', 'eml', 'en', 'en-gb', 'eo', 'es', 'et', 'eu', 'ext', 'fa', 'ff', 'fi', 'fiu-vro', 'fj', 'fo', 'fr', 'frc', 'frp', 'fur', 'fy', 'ga', 'gag', 'gan', 'gd', 'gl', 'glk', 'gn', 'got', 'grc', 'gsw', 'gu', 'gv', 'ha', 'hak', 'haw', 'he', 'hi', 'hif', 'hif-deva', 'hif-latn', 'hil', 'ho', 'hr', 'hsb', 'ht', 'hu', 'hy', 'hz', 'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'ike-cans', 'ike-latn', 'ilo', 'inh', 'io', 'is', 'it', 'iu', 'ja', 'jbo', 'jut', 'jv', 'ka', 'kaa', 'kab', 'kg', 'ki', 'kj', 'kk', 'kk-arab', 'kk-cyrl', 'kk-latn', 'kk-cn', 'kk-kz', 'kk-tr', 'kl', 'km', 'kn', 'ko', 'kr', 'kri', 'krj', 'ks', 'ksh', 'ku', 'ku-latn', 'ku-arab', 'kv', 'kw', 'ky', 'la', 'lad', 'lb', 'lbe', 'lez', 'lfn', 'lg', 'li', 'lij', 'lld', 'lmo', 'ln', 'lo', 'loz', 'lt', 'lv', 'lzz', 'mai', 'map-bms', 'mdf', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'mus', 'mwl', 'my', 'myv', 'mzn', 'na', 'nah', 'nan', 'nap', 'nb', 'nds', 'nds-nl', 'ne', 'new', 'ng', 'niu', 'nl', 'nn', 'no', 'nov', 'nrm', 'nso', 'nv', 'ny', 'oc', 'om', 'or', 'os', 'pa', 'pag', 'pam', 'pap', 'pdc', 'pdt', 'pfl', 'pi', 'pih', 'pl', 'plm', 'pms', 'pnt', 'ps', 'pt', 'pt-br', 'qu', 'rif', 'rm', 'rmy', 'rn', 'ro', 'roa-rup', 'roa-tara', 'ru', 'ru-sib', 'ruq', 'ruq-cyrl', 'ruq-grek', 'ruq-latn', 'rw', 'sa', 'sah', 'sc', 'scn', 'sco', 'sd', 'sdc', 'se', 'sei', 'sg', 'sh', 'shi', 'si', 'simple', 'sk', 'sl', 'sm', 'sma', 'sn', 'so', 'sq', 'sr', 'sr-ec', 'sr-el', 'srn', 'ss', 'st', 'stq', 'su', 'sv', 'sw', 'szl', 'ta', 'te', 'tet', 'tg', 'tg-cyrl', 'tg-latn', 'th', 'ti', 'tk', 'tl', 'tlh', 'tn', 'to', 'tokipona', 'tp', 'tpi', 'tr', 'ts', 'tt', 'tt-cyrl', 'tt-latn', 'tum', 'tw', 'ty', 'tyv', 'tzm', 'udm', 'ug', 'uk', 'ur', 'uz', 've', 'vec', 'vi', 'vls', 'vo', 'wa', 'war', 'wo', 'wuu', 'xal', 'xh', 'xmf', 'ydd', 'yi', 'yo', 'yue', 'za', 'zea', 'zh', 'zh-classical', 'zh-cn', 'zh-hans', 'zh-hant', 'zh-hk', 'zh-min-nan', 'zh-mo', 'zh-my', 'zh-sg', 'zh-tw', 'zh-yue', 'zu', 'simple'])


#--------------------------------<CLASSES>-------------------------------------#

#List of classes used in this script:
  #class cArbiter
  #class cParser(cArbiter)



class WikiData:
  """Object containing plaintext links and categories."""
  def __init__(self):
      self.plainText = None
      self.redirect = None
      self.linkList = []
      self.categoryList = []



class cArbiter:
  """Helper / handler of this script. Handles parsing of parameter, printing of progress bar, etc."""

  def GetParams(self):
    """This function is self-explained."""
    parser = optparse.OptionParser(
              usage = "usage: %prog [options]",
              version = "%prog 2.4.1")

    parser.add_option("-i", "--input-file",
                      dest="input", metavar="FILE",
                      help="take xml input from FILE otherwise from STDIN")
    parser.add_option("-o", "--output-file",
                      dest="output", metavar="FILE",
                      help="output parsed articles to FILE otherwise to STDOUT")
    parser.add_option("-n", "--no-text", action="store_false",
                      dest="text", default=False,
                      help="don't parse text (designed for use with -r -l -c options)")
    parser.add_option("-t", "--text", action="store_true",
                      dest="text", default=True,
                      help="produce plaintext (DEFAULT)")
    parser.add_option("-s", "--skip",
                      dest="skip", metavar="NUMBER",
                      help="skip (resume after) NUMBER of articles (and append to files)")
    parser.add_option("-q", "--quiet", action="store_false",
                      dest="verbose", default=True,
                      help="stop making noise")
    parser.add_option("-R", "--references", action="store_true",
                      dest="references", default=False,
                      help="retain references in text (links and categories)")
    parser.add_option("-r", "--redirects",
                      dest="redirects_file", metavar="FILE",
                      help="outsource redirect articles to the FILE")
    parser.add_option("-l", "--links",
                      dest="links_file", metavar="FILE",
                      help="capture articles' links in the FILE")
    parser.add_option("-c", "--categories",
                      dest="categories_file", metavar="FILE",
                      help="capture articles' categories in the FILE")
    parser.add_option("-T", "--test", action="store_true",
                      dest="test", default=False,
                      help="parse input from STDIN (use Ctrl + D to end input)")
    (options, args) = parser.parse_args()

    self.arg_text = options.text

    self.arg_skip = False
    try:
      if options.skip != None:
        self.arg_skip = int(options.skip)
    except:
      sys.stderr.write("\nWARNING: Skip argument not integer (not skipping).\n")
      self.arg_skip = False

    self.arg_verbose = options.verbose
    if self.arg_verbose:
      locale.setlocale(locale.LC_ALL, "C")

    self.arg_references = options.references

    if options.input != None:
      self.arg_input_name = options.input
      self.arg_input = open(options.input, "r")
    else:
      self.arg_skip = False
      self.arg_input_name = "stdin"
      self.arg_input = sys.stdin

    if options.output != None:
      if self.arg_text:
        self.arg_output_name = options.output
        if self.arg_skip:
          self.arg_output = open(options.output, "a+")
        else:
          self.arg_output = open(options.output, "w")
      else:
        self.arg_output_name = None
        self.arg_output = None
    else:
      if self.arg_text:
        self.arg_skip = False
        self.arg_output_name = "stdout"
        self.arg_output = sys.stdout
      else:
        self.arg_output_name = None
        self.arg_output = None

    self.arg_redirects_file = options.redirects_file

    self.arg_links_file = options.links_file

    self.arg_categories_file = options.categories_file

    self.arg_test = options.test
    if self.arg_test:
      self.arg_text = True


  def GetFileSize(self, file):
    """Self explained."""
    self.arg_input.seek(0, os.SEEK_END)
    size = self.arg_input.tell()
    self.arg_input.seek(0, os.SEEK_SET)
    return size


  def PrintProgress(self, fileSize, size, oldReturn):
    """Prints progress to stdout."""
    progressPer = "%.2f" % (float(size) / fileSize * 100)

    if oldReturn[0] != progressPer:

      progressStr = "%s MB  of  %s MB" % \
        (locale.format("%0.2f", (float(size) / 1000000), True), \
        locale.format("%d", (fileSize / 1000000), True))
      progressStr += " (" + progressPer + " %)"

      #print "x"
      for i in range(oldReturn[1]):
        sys.stdout.write('\b')
      sys.stdout.write(progressStr)
      sys.stdout.flush()

      return progressPer, len(progressStr)

    return progressPer, oldReturn[1]



class cParser(cArbiter):
  """Most important class... it does the actual parsing."""

  def __init__(self):
    self.repeat = 1 # flag needed for nested elements
    self.wikiData = WikiData()
    # REGULAR EXPRESSIONS PATTERNS FOR PARSING
    self.wikiRedRE = re.compile(r"(?i)#redirect\s*\[\[(.*?)\]\].*", re.DOTALL)
    self.wikiLanRE = re.compile(r"(.*\[\[Category:.*?\]\]).*", re.DOTALL)
    #self.wikiQuoRE = re.compile(r"\{\{cquote\|.*?\}\}", re.DOTALL)
    self.wikiCurRE = re.compile(r"\{\{.*?\}\}", re.DOTALL)
    #self.wikiClaRE = re.compile(r"\{\{lang\|([^{]*?(?:!\{\{)*?)\}\}", re.DOTALL)
    self.wikiTabRE = re.compile(r"\{\|.*?\|\}", re.DOTALL)
    self.wikiBrtRE = re.compile(r"(?:<|(?:&lt;))/?(?:(?:br)|(?:BR)).*?/?\s*(?:>|(?:&gt;))", re.DOTALL)
    self.wikiBlqRE = re.compile(r"(?:<|(?:&lt;))blockquote(?:>|(?:&gt;))(.*?)(?:<|(?:&lt;))/blockquote(?:>|(?:&gt;))", re.DOTALL)
    self.wikiComRE = re.compile(r"(?:<|(?:&lt;))!--.*?--(?:>|(?:&gt;))", re.DOTALL)
    self.wikiTttRE = re.compile(r"(?:<|(?:&lt;))(?:[tT]{2})(?:>|(?:&gt;))(.*?)(?:<|(?:&lt;))/(?:[tT]{2})(?:>|(?:&gt;))", re.DOTALL)
    #r"(?:<|(?:&lt;))[^/]*?(?!&gt;)/(?:>|(?:&gt;))"
    #<abc asdaaa="aa" />
    self.wikiCtaRE = re.compile(r"(?:<|(?:&lt;))(.*?)/(?:>|(?:&gt;))", re.DOTALL)
    self.wikiOtaRE = re.compile(r"(?i)((?:<|(?:&lt;))\s*(?P<tagname>\w+)(?:[^/]*?)(?:>|(?:&gt;)))(.*?)(?:<|(?:&lt;))\s*/\s*(?P=tagname)\s*(?:>|(?:&gt;))", re.DOTALL)
    self.wikiStaRE = re.compile(r"(?i)(?:<|(?:&lt;))\s*/?\s*(?:div|center|p|small|b|sub|s|blockquote|font|ref|i|gallery|del|sicsic|sup|div\s.*?|noinclude|table|tr|tr\s.*?|li|hr|td|math)\s*/?\s*(?:>|(?:&gt;))", re.DOTALL)
    self.wikiSMaRE = re.compile(r"&[a-z]+;")
    self.wikiSChRE = re.compile(r"(?!:(?:<|(?:&lt;))(?:(?:tt)|(?:TT))(?:>|(?:&gt;)))&amp;#[0-9]+;(?!:(?:<|(?:&lt;))/(?:(?:tt)|(?:TT))(?:>|(?:&gt;)))", re.DOTALL)
    self.wikiRefRE = re.compile(r"(?i)\[\[(?!category:)[\s_]*:?[\s_]*([^[]*?(?:!\[\[)*?)\]\]", re.DOTALL)
    #self.repaRefRE = re.compile(r"(?i)(^:category:\s*)(.)(.*)", re.DOTALL)
    # remove trailing spaces (used to repair title)
    self.repaTraRE = re.compile(r"^[\s_:]+")
    # repair spaces with "_" (used to repair categories, links and titles)
    self.repaBlaRE = re.compile(r"[\s_]+")
    self.wikiCatRE = re.compile(r"(?i)\[\[(category:[^[]*?(?:!\[\[)*?)\]\]", re.DOTALL)
    self.repaCatRE = re.compile(r"(?i)(^:?category:[\s_]*)(.)(.*)")
    self.wikiImgRE = re.compile(r"\[\[:?(Image|File):.*?\]\]", re.DOTALL)
    #[[(http | https | ftp) :// ...] ...] or [(http | https | ftp) :// ...]
    self.wikiHttRE = re.compile(r"(?:(?:\[\[(?:(?:http[s]?)|(?:ftp))://.*?\].*?\])|(?:\[(?:(?:http[s]?)|(?:ftp))://.*?\]))", re.DOTALL)
    self.wikiBolRE = re.compile(r"'''.*?'''", re.DOTALL)
    self.wikiItaRE = re.compile(r"''.*?''", re.DOTALL)
    self.wikiIteRE = re.compile(r"\n[*#(?:;)(?:#)]+[\ ]*")
    self.wikiEolRE = re.compile(r"(?:\n){2,}")
    self.wikiWhiRE = re.compile(r"(?:\s){2,}") # detects clusters of 2 or more white spaces
    self.wikiBraRE = re.compile(r"\(\)")
    self.wikiHeaRE = re.compile(r"[=]{2,4}.*?[=]{2,4}")


  def ParseLanguageReferences(self, matchObj):
    """Cuts language references from text."""
    #print "ParseLanguageReferences"
    return matchObj.group(1)


  def ParseSpecialChar(self, matchObj):
    """Returns html-ascii-decimal-character's unicode representation."""
    #print "MATCH", matchObj.group(0)
    #print "ParseSpecialChar char"
    try:
      ret = unichr(int(matchObj.group(0)[2:-1]))
    except:
      return ""
    return ret


  def ParseSpecialMark(self, matchObj):
    """Returns '<', '>', '&' or '"'."""
    #print "ParseSpecialMark"
    if matchObj.group(0) == "&lt;":
      return '<'
    elif matchObj.group(0) == "&gt;":
      return '>'
    elif matchObj.group(0) == "&amp;":
      return '&'
    elif matchObj.group(0) == "&quot;":
      return '\"'


  def ParseTable(self, matchObj):
    """Parsing table.. if tables are nested get rid of most nested and repeat."""
    #print "ParseTable"
    index = matchObj.group(0)[2:].rfind("{|")
    if index == -1:
      return ""
    else:
      self.repeat = 1
      return matchObj.group(0)[:index+2]


  def ParseQuotation(self, matchObj):
    """Returns unformated quotation."""
    #print "ParseQuotation"
    #index = matchObj.group(0).rfind("cquote|")
    #if index == -1:
      #return ""
    #else:
    return matchObj.group(0)[9:-2]


  def ParseCurlyLang(self, matchObj):
    """Returns unformated text."""
    #print "ParseCurlyLang"
    index = matchObj.group(1).rfind("|")
    return matchObj.group(1)[index+1:]


  def ParseCurly(self, matchObj):
    """Parse curly bracket.. if nested get rid of most nested and repeat."""
    #print "ParseCurly"

    deepestIndex = matchObj.group(0).rfind("{{") # start index of last nested element
    if deepestIndex != -1:
      self.repeat = 1 # nested element found, setting repeat flag
    else:
      deepestIndex = 0 # no nested elements

    # parsing double curly brackets differs acording to text before separator
    # {{lang|de|Ostereich}} is different from {{cquote|Kant is monster...}}
    separatorIndex = matchObj.group(0)[deepestIndex:].find("|")
    if separatorIndex != -1:
      separatorIndex += + deepestIndex
    else:
      #print "regular"
      # {{ ... }} (no "|" separator)
      return matchObj.group(0)[:deepestIndex]

    if matchObj.group(0)[deepestIndex+2:separatorIndex] == "cquote":
      #print "cquote|"
      # {{cquote|Kant is monster...}}
      return matchObj.group(0)[:deepestIndex] + matchObj.group(0)[separatorIndex+1:-2]
    elif matchObj.group(0)[deepestIndex+2:separatorIndex] == "lang":
      #print "lang|"
      # {{lang|de|Ostereich}}
      langSeparatorIndex = matchObj.group(0)[separatorIndex+1:-2].rfind("|")
      if langSeparatorIndex != -1:
        return matchObj.group(0)[:deepestIndex] + matchObj.group(0)[separatorIndex+1+langSeparatorIndex+1:-2]
      else:
        return matchObj.group(0)[:deepestIndex] + matchObj.group(0)[separatorIndex+1:-2]
    elif matchObj.group(0)[deepestIndex+2:separatorIndex] == "main":
      #print "main|"
      # {{main|History of anarchism}}
      return "Main article: " + matchObj.group(0)[separatorIndex+1:-2]
    else:
      #print "unknown|"
      # {{...|...}}
      return matchObj.group(0)[:deepestIndex]



  def ParseBlockQuote(self, matchObj):
    """Returns block quote tag content."""
    #print "ParseBlockQuote"
    return matchObj.group(1)


  def ParseClosedTag(self, matchObj):
    """Parse tags.. if nested get rid of the deepest element and repeat."""
    #print "closedTag"
    #ff = re.compile(r"(?:<|(?:&lt;))", re.DOTALL)
    #if matchObj.group(1).find("<"):
      #return matchObj.group(0)
    #else:
    return ""
    #print "0:", matchObj.group(0)
    #print "1:", matchObj.group(1)
    #return ""


  def ParseOpennedTag(self, matchObj):
    """Parse tags.. if nested get rid of the deepest element and repeat."""
    #print "opennedTag"
    #return ""
    # matchObj.group(0) text with tags "<p>aa</p>"
    # matchObj.group(1) opening tag "<p>"
    # matchObj.group(2) tag name
    #print "MATCH:", matchObj.group(0)
    #print "SEARCH IN:", matchObj.group(3) #text without tags "aa"
    #print "TAGNAME:", matchObj.group("tagname")
    #print "ot:", matchObj.group("otag")
    #print "ct:", matchObj.group("ctag")
    regex = r"(?i)(?:<|(?:&lt;))\s*"
    regex += matchObj.group("tagname")
    regex += r"\s*(?:.*?)(?<!/)(?:>|(?:&gt;))"
    ff = re.compile(regex, re.DOTALL)
    ret = ""
    for i in ff.findall(matchObj.group(3)):
      #print matchObj.group(3)
      ret += matchObj.group(1)
    if ret != "":
      self.repeat = 1
    return ret


  def ParseSoup(self, matchObj):
    """Removes that stinky tag soup."""
    #print "ParseSoup"
    ## test whether we are parsing something that's not a tag soup
    #if len(matchObj.group(0)) > 100:
      #print matchObj.group(0)
    return ""

  def ParseImageText(self, matchObj):
    """Returns unformated reference text."""
    #print "ParseImageText"
    lastNested = matchObj.group(0)[2:].rfind("[[") # start index of last nested element
    if lastNested == -1: # if not nested
      return ""
    else:
      self.repeat = 1
      return matchObj.group(0)[:lastNested+2]


  def RepairCategory(self, matchObj):
    """Repairs bad categories (i.e. \"category:xxx\", \"Category: xxx\")."""

    return "Category:" + matchObj.group(2).capitalize() + matchObj.group(3)


  def RepairArticleName(self, articleName):
    """Repairs bad formated category/link/title."""
    if len(articleName) > 0:
      articleName = self.repaCatRE.sub(self.RepairCategory, articleName)
      articleName = self.repaBlaRE.sub("_", articleName)
      articleName = self.repaTraRE.sub("_", articleName)
      articleName = articleName[0].upper() + articleName[1:]
    return articleName


  def ParseCategory(self, matchObj):
    """ """
    #print "ParseCategory"
    if self.arg_references or self.arg_categories_file:
      index = matchObj.group(1).find('|')
      if index == -1:
          category = self.RepairArticleName(matchObj.group(1))
      else:
          category = self.RepairArticleName(matchObj.group(1)[:index])
      self.wikiData.categoryList.append(category)

    return ""


  #def RepairReference(self, matchObj):
    #"""Repairs bad categories (i.e. \"category:xxx\", \"Category: xxx\")."""


    #return "Category:" + matchObj.group(2).capitalize()


  def ParseReference(self, matchObj):
    """Returns unformated reference text."""
    #print "ParseReference"
    annotation = matchObj.group(1)
    retStr = "<annotation "

    if annotation[:7] == "http://":
      return ""

    #if annotation[:2] == "s:":
      #retStr += "source=\"wikisource\" "
      #annotation = annotation[2:]
    #elif annotation[:2] == "q:":
      #retStr += "source=\"wikiquote\" "
      #annotation = annotation[2:]
    #elif annotation[:2] == "m:":
      #retStr += "source=\"wikimedia\" "
      #annotation = annotation[2:]
    #elif annotation[:annotation.find(':')] in LANG_ARRAY:
      #return ""

    langSeparator = annotation.find(':')
    if langSeparator != -1 and annotation[:annotation.find(':')] in LANG_ARRAY:
      return ""

    linkSeparator = annotation.find('|')


    if linkSeparator == -1: # self reference (e.g. [[aaa]])
      if self.arg_links_file:
        link = self.RepairArticleName(annotation)
        self.wikiData.linkList.append(link)
      if not self.arg_references:
        return annotation
      retStr += "target=\"" + annotation + "\">" + annotation
    else:
      if self.arg_links_file or self.arg_references:
        link = self.RepairArticleName(annotation[:linkSeparator])
        self.wikiData.linkList.append(link)
      if not self.arg_references:
        return annotation[linkSeparator+1:]
      retStr += "target=\"" + link + "\">" + annotation[linkSeparator+1:]
    retStr += "</annotation>"
    return retStr


  def ParseHttp(self, matchObj):
    """Returns text from html reference."""
    #print "ParseHttp"
    spaceIndex = matchObj.group(0).find(' ')
    bracketIndex = matchObj.group(0).find(']')
    if spaceIndex == -1:
      return ""
    else:
      return matchObj.group(0)[spaceIndex+1:bracketIndex]+matchObj.group(0)[bracketIndex+1:-1]


  def ParseBold(self, matchObj):
    """Unbolds."""
    #print "ParseBold"
    return matchObj.group(0)[3:-3]


  def ParseItallic(self, matchObj):
    """Unitallics."""
    #print "ParseItallic"
    return matchObj.group(0)[2:-2]


  def ParseHeading(self, matchObj):
    """Returns parsed heading."""
    #print "ParseHeading"
    return re.sub(r"[=]+[\ ]*", "\n",matchObj.group(0))


  def ParseItemList(self, matchObj):
    """Returns parsed item list (replaces '*' with '\t' in item list)."""
    #print "ParseItemList"
    return matchObj.group(0).replace(' ','').replace(':','').replace(';','').replace('*','\t').replace('#','\t')


  def ParseTagTT(self, matchObj):
    """This tag is used for displaying speciel marks as text."""
    #print "ParseTagTT"
    return matchObj.group(1)


  def GetPlainTextLinksCategoriesFromWikiDump(self, text):
    """Returns plain text from xml text tag content."""

    wikiData = WikiData()

    # redirected pages (articles), i.e. #REDIRECT
    # redirection is handeled befor this method ... in xml parsing
    if self.arg_references:
      if text[:9].upper() == "#REDIRECT":
        self.wikiData.plainText = "<redirect target=\"" + self.wikiRedRE.sub("\g<1>", text) + "\"/>"
        return

    if self.arg_redirects_file:
      if text[:9].upper() == "#REDIRECT":
        self.wikiData.redirect = self.RepairArticleName(self.wikiRedRE.sub("\g<1>", text))
        return

    ### DELETING
    ## GOOD TO PARSE AS FIRST (commented tags can make a mess)
    # comments, i.e. &lt;!-- ... --&gt;
    text = self.wikiComRE.sub("", text)

    ### DELETING
    # br tags, i.e. &lt;br&gt;
    # &lt; or '<' are the same but it depends on how you get the input
    # both will be used for safety reasons
    text = self.wikiBrtRE.sub("", text)

    ### DELETING / REPLACING
    # other curly brackets (even nested ones, like Infobox), i.e. {{ ... }}
    while self.repeat:
      self.repeat = 0 # if no nested elements than don't repeat
      text = self.wikiCurRE.sub(self.ParseCurly, text)
    self.repeat = 1

    ### DELETING
    # some sort of wiki table, i.e. {| ... |}
    while self.repeat:
      self.repeat = 0 # if no nested elements than don't repeat
      text = self.wikiTabRE.sub(self.ParseTable, text)
    self.repeat = 1

    ### REPLACING
    # wiki images, i.e. [[Image:...]]
    # wiki files, i.e. [[File:...]]
    # wiki references are sometimes nested in image comments,
    # e.g. [[abc|...[[defg|[[...]]...]]]]
    while self.repeat:
      self.repeat = 0 # if no nested elements than don't repeat
      text = self.wikiImgRE.sub(self.ParseImageText, text)
    self.repeat = 1

    ### REPLACING
    ## MUST GO BEFORE ALL TAGS PARSING
    # blocks of guotes, i.e. <blockquote>...</blockquote>
    text = self.wikiBlqRE.sub(self.ParseBlockQuote, text)

    ## MUST GO BEFORE TT TAGS PARSING
    # html ascii decimal characters, i.e. &#230
    text = self.wikiSChRE.sub(self.ParseSpecialChar, text)
    ## MUST GO BEFORE ALL TAGS PARSING
    # tt tags, i.e. <tt>&amp;amp;#230</tt>
    text = self.wikiTttRE.sub(self.ParseTagTT, text)

    ### DELETING
    # openned tags, i.e. <abc>...</(abc)>
    while self.repeat:
      self.repeat = 0 # if no nested elements than don't repeat
      text = self.wikiOtaRE.sub(self.ParseOpennedTag, text)
    self.repeat = 1

    ### DELETING
    ## MUST GO AFTER OPENNED TAGS PARSING
    # closed tags, i.e. <abc ... />
    text = self.wikiCtaRE.sub(self.ParseClosedTag, text)

    ### DELETING
    ## MUST GO AFTER OPENNED AND CLOSED TAGS PARSING
    # tag soup (bad tags)
    text = self.wikiStaRE.sub(self.ParseSoup, text)

    ### DELETING
    if self.arg_text or self.arg_categories_file: # if parsing text, categories need to be cut away
      # wiki categories, i.e. [[Category:Anarchism| ]]
      text = self.wikiCatRE.sub(self.ParseCategory, text)

    ### REPLACING
    # wiki http reference, i.e. [http://abc/ ...]
    text = self.wikiHttRE.sub(self.ParseHttp, text)

    ### REPLACING
    # wiki references, i.e. [[aa|bb]]
    text = self.wikiRefRE.sub(self.ParseReference, text)

    # no need to continue if only categories and/or links are being parsed
    if not self.arg_text:
      return
      #return wikiData

    ### REPLACING
    # &gt &lt &amp etc.
    text = self.wikiSMaRE.sub(self.ParseSpecialMark, text)

    ### REPLACING
    # bold, i.e. '''...'''
    text = self.wikiBolRE.sub(self.ParseBold, text)

    ### REPLACING
    # itallic, i.e. ''...''
    text = self.wikiItaRE.sub(self.ParseItallic, text)

    ### REPLACING
    # wiki item listing, i.e. "* ..." or "# ..." or ":; ..." or ":# ..."
    text = self.wikiIteRE.sub(self.ParseItemList, text)

    ### REPLACING
    # EOL formating
    text = self.wikiEolRE.sub('\n', text)

    ### REPLACING
    # whitespace formating (removes clusters of more than 2 whitespaces)
    text = self.wikiWhiRE.sub(' ', text)

    ### REPLACING
    # remove empty brackets
    text = self.wikiBraRE.sub("", text)

    ### REPLACING
    # headings, i.e. ===...===
    text = self.wikiHeaRE.sub(self.ParseHeading, text)

    self.wikiData.plainText = text

    return


  def get_etree_and_namespace(self, xml_file):
      """Designed to grab the namespace from the first element of the xml file. Unfortunately it has to start parsing and so it returns both namespace and etree."""
      events = ("start", "start-ns", "end")
      root = None
      namespaces = {}
      context = lxml.etree.iterparse(xml_file, events)
      context = iter(context)
      event, elem = context.next()
      if event == "start-ns":
          if elem[0] in namespaces and namespaces[elem[0]] != elem[1]:
              # NOTE: It is perfectly valid to have the same prefix refer
              #     to different URI namespaces in different parts of the
              #     document. This exception serves as a reminder that this
              #     solution is not robust.    Use at your own peril.
              raise KeyError("Duplicate prefix with different URI found.")
          namespaces[elem[0]] = "%s" % elem[1]
      elif event == "start":
          if root is None:
              root = elem
      
      return context, namespaces[''] if '' in namespaces else namespaces


  def ParseWiki(self):
    """Parse text, links, categories from a wikidump."""
    
    # getting file size
    if self.arg_input != sys.stdin and self.arg_output != sys.stdout and self.arg_verbose:
      inputFileSize = self.GetFileSize(self.arg_input)
      oldRet = ("",0)

    try: # to initialize wiki2xml parser
      context, ns = self.get_etree_and_namespace(self.arg_input)
      #context = lxml.etree.iterparse(self.arg_input, events = ("start", "end"))
      #context = iter(context)
      event, root = context.next()
    except:
      raise
      sys.stderr.write("\nERROR: Bad input file (not a wikidump), try \"-T\" for testing purposes.\n")

    # setting skip
    count = 0
    if self.arg_skip:
      count = self.arg_skip

    # skipping N number of articles
    if self.arg_skip:
      try:
        for i in range(count):
          event, element = context.next()
          # percentage
          if self.arg_input != sys.stdin and self.arg_output != sys.stdout and self.arg_verbose:
            currentFileSize = self.arg_input.tell()
            oldRet = self.PrintProgress(inputFileSize, currentFileSize, oldRet)
          if event == "end":
            element.clear()
          while element.getprevious() is not None:
            del element.getparent()[0]

      except StopIteration:
        if self.arg_input != sys.stdin and self.arg_output != sys.stdout:
          sys.stdout.write("\nINFO: Whole wikidump skipped.\n")
        sys.exit(0)

    # prepare namespace variables (later used identifying elements of the tree)
    nsdict = {'ns' : ns}
    ns = '{%s}' % ns

    # prepare links file
    if self.arg_links_file:
      if self.arg_skip:
        self.arg_lnkFile = open(self.arg_links_file, "a")
      else:
        self.arg_lnkFile = open(self.arg_links_file, "w")

    # prepare categories file
    if self.arg_categories_file:
      if self.arg_skip:
        self.arg_catFile = open(self.arg_categories_file, "a")
      else:
        self.arg_catFile = open(self.arg_categories_file, "w")

    # prepare redirects file
    if self.arg_redirects_file:
      if self.arg_skip:
        self.arg_redFile = open(self.arg_redirects_file, "a")
      else:
        self.arg_redFile = open(self.arg_redirects_file, "w")

    for event, element in context:

      try:

        count += 1

        self.wikiData.__init__()
        # percentage
        if self.arg_input != sys.stdin and self.arg_output != sys.stdout and self.arg_verbose:
          currentFileSize = self.arg_input.tell()
          oldRet = self.PrintProgress(inputFileSize, currentFileSize, oldRet)

        if element.tag == (ns + "page") and event == "end":

          titles = element.xpath (u"ns:title/text()", namespaces=nsdict)
          ids = element.xpath (u"ns:id/text()", namespaces=nsdict)
          texts = element.xpath (u"ns:revision/ns:text/text()", namespaces=nsdict)

          if len(titles) != 1:
            continue

          if len(ids) != 1:
            continue

          title = titles[0]
          id = ids[0]

          wiki = "".join(texts)

          ##if ref flag was not found
          ##ignore redirected pages (articles), i.e. #REDIRECT or #redirect
          #if (wiki[:9] == "#REDIRECT" or wiki[:9] == "#redirect") and not self.arg_references or :
            #element.clear()
            #continue

          self.GetPlainTextLinksCategoriesFromWikiDump(wiki)
          linkText = None
          categoryText = None
          redirectText = None
          repairedTitle = self.RepairArticleName(title)

          if self.arg_links_file:
            linkText = ""
            for i in self.wikiData.linkList:
              linkText += repairedTitle + '\t' + i + '\n'

          if self.arg_categories_file:
            categoryText = ""
            for i in self.wikiData.categoryList:
              categoryText += repairedTitle + '\t' + i + '\n'

          if self.arg_redirects_file:
            if self.wikiData.redirect is not None:
              redirectText = repairedTitle + '\t' + self.wikiData.redirect + '\n'

          # write to *.edg files
          if linkText is not None:
            self.arg_lnkFile.write(linkText.encode("utf-8"))
          if categoryText is not None:
            self.arg_catFile.write(categoryText.encode("utf-8"))
          if redirectText is not None:
            self.arg_redFile.write(redirectText.encode("utf-8"))


          # write text
          if self.wikiData.plainText is not None:

            # xml output
            if self.arg_text:
              pageEl = lxml.etree.Element ( "article" )
              idEl = lxml.etree.SubElement ( pageEl, "id" )
              idEl.text = id
              titleEl = lxml.etree.SubElement ( pageEl, "title" )
              titleEl.text = title
              textEl = lxml.etree.SubElement ( pageEl, "text" )
              textEl.text = self.wikiData.plainText
              if self.arg_references:
                categoriesEl = lxml.etree.SubElement ( pageEl, "categories" )
                categoriesText = ""
                for i in self.wikiData.categoryList:
                  categoriesText += "<category target=\"" + i + "\"/>"
                categoriesEl.text = categoriesText

              lxml.etree.ElementTree(pageEl).write(self.arg_output, encoding='utf-8')

          # free every page element (otherwise the RAM would overflow eventually)
          element.clear()
          while element.getprevious() is not None:
            del element.getparent()[0]

      except KeyboardInterrupt:
        sys.stderr.write("\nWARNING: Prematurely aborted parsing (not all articles have been processed).\n")
        if self.arg_input != sys.stdin and self.arg_output != sys.stdout:
          sys.stderr.write("WARNING: To resume parsing run the same command again with additional \"-s "+str(count)+"\" option.\n")
        element.clear()
        while element.getprevious() is not None:
          del element.getparent()[0]
        if self.arg_links_file:
          self.arg_lnkFile.close()
        if self.arg_categories_file:
          self.arg_catFile.close()
        if self.arg_redirects_file:
          self.arg_redFile.close()
        break

      except IOError:
        sys.stderr.write("\nERROR: Input/Output filesystem related problem (File too large, No such file or directory, etc.).\n")
        if self.arg_input != sys.stdin and self.arg_output != sys.stdout:
          sys.stderr.write("WARNING: To resume parsing run the same command again with additional \"-s "+str(count)+"\" option.\n")
        element.clear()
        while element.getprevious() is not None:
          del element.getparent()[0]
        if self.arg_links_file:
          self.arg_lnkFile.close()
        if self.arg_categories_file:
          self.arg_catFile.close()
        if self.arg_redirects_file:
          self.arg_redFile.close()
        break

      except:
        raise
        # Unknown error... continue in parsing.
        sys.stderr.write("\WARNING: Error in parsing, skipping article.\n")
        element.clear()
        while element.getprevious() is not None:
          del element.getparent()[0]
        continue

    else:
      element.clear()
      while element.getprevious() is not None:
        del element.getparent()[0]
      if self.arg_links_file:
        self.arg_lnkFile.close()
      if self.arg_categories_file:
        self.arg_catFile.close()
      if self.arg_redirects_file:
        self.arg_redFile.close()

#-------------------------------</CLASSES>-------------------------------------#


if __name__ == "__main__":

  # create parser object
  parser = cParser()

  # evaluate startup parameters
  parser.GetParams()

  # testing? (input from stdin)
  if parser.arg_test:
    print "INPUT:"
    inputStr = parser.arg_input.read() # use Ctrl + D to signify end of input
    print "\nOUTPUT:"
    parser.GetPlainTextLinksCategoriesFromWikiDump(inputStr)
    print parser.wikiData.plainText
    sys.exit(0)

  # do the actual parsing as long as some output is expected to be produced
  if parser.arg_text or parser.arg_links_file or parser.arg_categories_file or parser.arg_redirects_file:
    parser.ParseWiki()
  else:
    if parser.arg_verbose:
      sys.stdout.write("\nINFO: Exectured with options that didn't result in any parsed output. Try to use some other option combination.\n")

  del parser

# END OF SCRIPT
