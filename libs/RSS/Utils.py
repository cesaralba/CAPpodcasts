from collections import namedtuple
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import bs4
import validators
from validators.uri import uri
from CAPcore.Files import readFile
from CAPcore.Web import downloadRawPage
from bs4 import BeautifulSoup as bs


def feed2URI(URL: str):
    """
    Converts URL to URI format if it is not yet (URLs are URI already). Useful for files

    Notice it is just about format, URL may point to nowhere or file may not exist
    :param URL: location of the feed. It may be a URL, a file URI (a URL with file scheme) or a file location (abs or rel)
    :return: correct URL/URI for the feed
    """
    if URL is None:
        raise ValueError(f"feed2URI: '{URL}' invalid value")

    try:
        if validators.url(URL, simple_host=True):  # Actual URL (http[s])
            return URL
        elif uri(URL):  # It is already a URI with schema file
            return URL
        else:
            result = Path(URL).resolve().as_uri()
            return result
    except validators.ValidationError:
        print(f"Provided URL '{URL}' can not be processed")  # We assume it is a file (Path is able to handle File URIs)

def isFileURI(URI:str)->bool:
    URIcomps = urlparse(URI)
    return URIcomps.scheme == 'file'


def readURI(URI):
    URIcomps = urlparse(URI)
    dataFeed = readFile(URIcomps.path) if isFileURI(URI) else downloadRawPage(dest=URI)
    return dataFeed


def parseXMLContent_BS4(content):
    bs_content = bs(content, features="xml")

    return bs_content


EnclosureData = namedtuple('enclosure', field_names=[ "type", "url","length"], defaults=[None])


def processShow(itemData: bs4.element.Tag):
    """
    Generic functiopn to show structure of field in order to build the function
    :param itemData: item to show
    :return: None
    """
    itKey = extractTagKey(itemData)
    print(f"processShow: {itKey}  -> #{str(itemData)}#")
    return None


def processFeedItuImage(itemData: bs4.element.Tag) -> str:
    result = itemData['href']
    return result


def processNestedItem(itemData: bs4.element.Tag) -> dict:
    result = { extractTagKey(it):it.getText() for it in itemData.children if not isinstance(it,bs4.element.NavigableString)}
    return result


def processFeedItuCategory(itemData: bs4.element.Tag) -> str:
    result = itemData['text']
    return result


def processAtLink(itemData: bs4.element.Tag) -> dict:
    result = dict()
    result.update(**(itemData.attrs))
    return result


def processEnclosure(itemData: bs4.element.Tag) -> EnclosureData:
    result = EnclosureData(**(itemData.attrs))
    return result


def processItuExplicit(itemData: bs4.element.Tag) -> Optional[bool]:
    itText= itemData.getText().lower()
    if itText in {'no','clean','false'}:
        return False
    elif itText in {'yes','true'}:
        return True

    print(f"processItuExplicit[{extractTagKey(itemData)}] unknown value #{itText}#")
    return None


def processPubDate(itemData: bs4.element.Tag):
    # 'Mon, 22 Jul 2024 08:36:19 GMT'
    # https://stackoverflow.com/a/45558386
    result = parsedate_to_datetime(itemData.getText())
    return result


def processKeywords(itemData: bs4.element.Tag):
    result = set(map(lambda x: x.strip(), itemData.getText().split(',')))
    return result


def extractTagKey(item: bs4.element.Tag) -> tuple:
    return item.prefix, item.name

def simplifyTagKeys(data:dict) -> dict:
    result = {k[1]:v for k,v in data.items()}

    return result
