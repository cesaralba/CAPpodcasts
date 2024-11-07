import logging
import sys
from datetime import datetime
from functools import reduce
from operator import attrgetter
from typing import Optional, Union
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import rfeed

NONENSKEY = "__main"  # Key for items with namespace empty (None)

import bs4
from CAPcore.Web import DownloadedPage
# https://linuxhint.com/parse_xml_python_beautifulsoup/
from bs4.element import NavigableString
from requests import HTTPError

from .OPML import OPMLfeed
from .Utils import feed2URI, readURI, parseXMLContent_BS4, processFeedItuImage, processNestedItem, \
    processFeedItuCategory, processAtLink, processEnclosure, processItuExplicit, processPubDate, processKeywords, \
    extractTagKey, isFileURI, simplifyTagKeys

FEEDTAGS2STORE = {(None, 'title'), ('itunes', 'subtitle'), (None, 'link'), (None, 'description'), (None, 'pubDate'),
                  (None, 'language'), (None, 'image'), (None, 'copyright'), (None, 'generator'), ('itunes', 'type'),
                  ('itunes', 'image'), ('itunes', 'owner'), ('itunes', 'category'), ('itunes', 'author'),
                  ('itunes', 'explicit'), ('itunes', 'keywords'), ('itunes', 'summary'), ('atom', 'link')}
FEEDTAGS2IGNORE = {}
ITEMTAGS2STORE = {(None, 'title'), (None, 'link'), (None, 'description'), (None, 'enclosure'), (None, 'category'),
                  (None, 'pubDate'), (None, 'guid'), ('itunes', 'duration'), ('itunes', 'explicit'),
                  ('itunes', 'keywords'), ('itunes', 'subtitle'), ('itunes', 'image'), ('itunes', 'summary'),
                  ('itunes', 'episode'), ('itunes', 'season'), ('itunes', 'episodeType'), }
ITEMTAGS2IGNORE = {}


class PagingConfiguration:
    def __init__(self, name: str = "offset", isPath: bool = False, changeOnZero: bool = False, drift: int = 0):
        self.paramName = name

        self.pathType = isPath
        self.workOnZero = changeOnZero  # Do something on initial URL
        self.drift = drift  # Add value to initial URL

    def buildURI(self, URI: str, increase=1) -> str:
        URIcomps = urlparse(URI)

        if URIcomps.scheme == "file":
            return URI  # A file URI should not be paginated

        if self.pathType:
            # TODO: Arreglar esto
            return URI

        paramsInQuery = parse_qs(URIcomps.query)
        if self.paramName in paramsInQuery:
            currValue = int(paramsInQuery[self.paramName][0])
        else:
            if increase == 0 and not self.workOnZero:
                return URI
            currValue = self.drift

        paramsInQuery.update({self.paramName: (currValue + increase)})
        newQuery = urlencode(paramsInQuery)

        result = urlunparse(URIcomps._replace(query=newQuery))

        return result


class FeedItemData:
    def __init__(self, **kwargs):
        self.raw = kwargs.get('raw', "")
        self.metadata = kwargs.get('metadata', dict())
        self.infoItem = kwargs.get('infoItem', dict())
        self.guid = self.infoItem[NONENSKEY]['guid']
        self.pubDate = self.infoItem[NONENSKEY]['pubDate']

    def __str__(self):
        sourceStr = self.metadata['source']
        tstampStr = self.metadata['tstamp'].strftime("%Y%m%d-%H%M%S %z")

        result = f"Item guid: '{self.guid}' pubDate: {self.pubDate.strftime("%Y%m%d-%H%M%S %z")} Source: '{sourceStr}'  Seen {tstampStr}"
        return result

    # I know this is not repr's intent, but it is convenient (i.e. ipython)
    __repr__ = __str__

    def __eq__(self, other):
        if self.guid != other.guid:
            return False
        return equalDicts(self.infoItem, other.infoItem)

    def produceRFeedItem(self):
        excludeItunes = {'keywords'}
        excludeInfo = {}
        keyTransInfo = {'category': 'categories'}
        keyTransItunes = {}
        transfItunes = {}
        transfInfo = {'category': rfeed.Category, 'enclosure': lambda a: rfeed.Enclosure(**a._asdict()),
                      'guid': rfeed.Guid, }

        itunesParam = preparaParams(self.infoItem.get('itunes', dict()), exclusions=excludeItunes,
                                    transformers=transfItunes, keyTranslations=keyTransItunes)
        itunes_data = rfeed.iTunesItem(**itunesParam)

        infoParam = preparaParams(self.infoItem.get(NONENSKEY, dict()), exclusions=excludeInfo, transformers=transfInfo,
                                  keyTranslations=keyTransInfo)
        if itunes_data:
            infoParam['extensions'] = [itunes_data]

        result = rfeed.Item(**infoParam)
        return result


class FeedData:
    def __init__(self, **kwargs):
        self.infoChannel = kwargs.get('infoChannel', dict())
        self.items = kwargs.get('items', [])
        self.metadata = {k: kwargs.get(k) for k in {'rssVersion', 'source', 'tstamp'} if k in kwargs}

    def __str__(self):
        """
        Notice either there is metadata or it is None
        :return:
        """
        sourceStr = self.metadata['source'] if self else "None"
        lenStr = f"{len(self.items):4}" if self else "None"
        tstampStr = {self.metadata['tstamp'].strftime("%Y%m%d-%H%M%S %z")} if self else "None"

        result = f"FeedRecord Source: {sourceStr} Items: {lenStr} Downloaded @{tstampStr}"
        return result

    __repr__ = __str__

    def __len__(self):
        return len(self.items)

    def __neg__(self):
        return bool(self.metadata)

    @classmethod
    def mergeObjects(cls, a, b):
        if not isinstance(a, (cls, None)) and not isinstance(b, (cls, None)):
            raise TypeError(f"Arguments provided not of type {cls}")
        elif not a and not b:
            return cls()
        elif a == b:
            return a
        elif not a:
            return b
        elif not b:
            return a

        older = a if a.metadata['tstamp'] < b.metadata['tstamp'] else b
        newer = a if a.metadata['tstamp'] > b.metadata['tstamp'] else b

        resultingData = dict()
        resultingData['items'] = list()
        resultingData['infoChannel'] = dict()

        resultingData.update(older.metadata)
        resultingData['infoChannel'].update(newer.infoChannel)

        resultingData['items'] = sorted(mergeItemList(older.items, newer.items), key=attrgetter('pubDate'),
                                        reverse=True)

        result = cls(**resultingData)
        return result

    def produceRFeedChannel(self):
        excludeItunes = {'keywords'}
        excludeInfo = {}
        keyTransInfo = {}
        keyTransItunes = {'category': 'categories'}
        transfItunes = {'owner': lambda a: rfeed.iTunesOwner(**simplifyTagKeys(a)), }
        transfInfo = {'image': lambda a: rfeed.Image(**simplifyTagKeys(a)),
                      'owner': lambda a: rfeed.Owner(**simplifyTagKeys(a)),

                      }  # {'category': Category}

        itunesParam = preparaParams(self.infoChannel.get('itunes', dict()), exclusions=excludeItunes,
                                    transformers=transfItunes, keyTranslations=keyTransItunes)
        itunes_data = rfeed.iTunes(**itunesParam)

        infoParam = preparaParams(self.infoChannel.get(NONENSKEY, dict()), exclusions=excludeInfo,
                                  transformers=transfInfo, keyTranslations=keyTransInfo)
        if itunes_data:
            infoParam['extensions'] = [itunes_data]

        items = [it.produceRFeedItem() for it in self.items]

        infoParam['items'] = items

        result = rfeed.Feed(**infoParam)
        return result

    def dump(self, filename: Optional[str]=None):
        # https://mchartigan.github.io/blog/20220118.html
        # https://github.com/egorsmkv/rfeed
        feed = self.produceRFeedChannel()
        rss = feed.rss()

        # write RSS feed to feed.xml
        with (sys.stdout if filename is None else open(filename, "w")) as fileHdl:
            fileHdl.write(rss)


class FeedRecord:
    def __init__(self, URL: str, title: str, descr: Optional[str] = None, typeFeed: Optional[str] = None,
                 paged: bool = False, maxPages: Optional[int] = None, isOffset: bool = True,
                 pagingConf: Optional[PagingConfiguration] = None):
        self.URL: str = feed2URI(URL)
        self.title: str = title
        self.descr: str = descr
        self.type: str = typeFeed
        self.lastUpdated: Optional[datetime] = None
        self.paged: bool = paged  # The feed does paging (it doesn't get all items at once)
        self.offsetType = isOffset  # true (offset) = number of items to skip, false (paged) = paginated
        self.maxPages: Optional[int] = maxPages  # Number of pages to download
        self.confPages: Optional[PagingConfiguration] = pagingConf

    def retrieve(self, dryRun: bool = False):
        RSSdownloaded = []
        if self.paged and not isFileURI(self.URL):
            logging.debug(f"Retrieving {self} {"[DRYRUN]" if dryRun else ""}")

            if self.confPages is None:
                self.confPages = PagingConfiguration()
            pageCounter = 0
            itemCounter = 0

            if not dryRun:
                while (self.maxPages is None) or (self.maxPages == 0) or (pageCounter < self.maxPages):
                    newIndexParam = itemCounter if self.offsetType else pageCounter
                    currURL = self.confPages.buildURI(self.URL, newIndexParam)

                    data = self.getFeed(actURI=currURL)
                    try:
                        numNewItems = len(data)
                        if numNewItems == 0:
                            break  # No more things to process
                        itemCounter += numNewItems
                    except IndexError as exc:
                        logging.debug(f"FeedRecord '{self.title}' with no Items.", exc)
                        break
                    RSSdownloaded.append(data)
                    pageCounter += 1

        else:
            logging.debug(f"Retrieving {self} {"[DRYRUN]" if dryRun else ""}")
            if not dryRun:
                data = self.getFeed()
                RSSdownloaded.append(data)

        result = reduce(FeedData.mergeObjects, RSSdownloaded)
        return result

    @classmethod
    def feedFromOPML(cls, feedData: OPMLfeed):
        if feedData.unlisted:
            print(f"UNLISTED {feedData.title} [{feedData.xmlUrl}]")
        result = cls(URL=feedData.xmlUrl, title=feedData.title, descr=feedData.text, typeFeed=feedData.type)
        return result

    def __repr__(self):
        return f"FeedRecord(title='{self.title}', URL='{self.URL}')"

    def getFeed(self, actURI: Optional[str] = None):
        """
        Retrieves the RSS (or file for that matter) feed and returns the parsing of it
        :param actURI: [Optional] URI to use. Uses the one of the feed if not provided
        :return:
        """
        UNKNOWNKEYS = dict()

        URI2use = self.URL if actURI is None else actURI
        try:
            dataFeed = readURI(URI2use)
            result = parseFeed(dataFeed, UNMANAGEDKEYS=UNKNOWNKEYS)
            if (len(UNKNOWNKEYS.get('feed', dict())) + len(UNKNOWNKEYS.get('feed', dict()))):
                print("Unknown keys: ", UNKNOWNKEYS)

            return result
        except HTTPError as exc:
            print(exc)

    def switchPaged(self):
        self.paged = not self.paged
        return self.paged


def addDictIfNotPresent(data, dictKey):
    if dictKey not in data:
        data[dictKey] = dict()
    return data


def parseFeed(fileData: DownloadedPage, UNMANAGEDKEYS: Optional[dict] = None):
    FEEDELHANDLERS = {(None, 'pubDate'): processPubDate,  # (None, 'enclosure'): processEnclosure,
                      # ('itunes', 'keywords'): processKeywords,
                      (None, 'image'): processNestedItem,  # Process
                      ('itunes', 'image'): processFeedItuImage, ('itunes', 'owner'): processNestedItem,  # Process
                      ('itunes', 'category'): processFeedItuCategory, ('itunes', 'explicit'): processItuExplicit,
                      # Process,
                      ('itunes', 'keywords'): processKeywords,  # Process,

                      # TOTHINK: ('itunes','duration'),
                      ('atom', 'link'): processAtLink, }

    data = dict()
    parsedData = parseXMLContent_BS4(fileData.data)

    data['rssVersion'] = parsedData.find('rss')['version']
    data['source'] = fileData.source
    data['tstamp'] = fileData.timestamp
    data['infoChannel'] = dict()
    data['items'] = list()

    channel = parsedData.find('channel')
    for item in channel:
        if isinstance(item, NavigableString):
            continue

        itemName = item.name
        if itemName == 'item':
            # print(type(item))
            dataItem = parseFeedItem(item, feedMetadata=data, UNMANAGEDKEYS=UNMANAGEDKEYS)
            if dataItem:
                data['items'].append(dataItem)
        else:
            chKey = extractTagKey(item)

            if chKey in FEEDTAGS2IGNORE:
                continue
            elif chKey in FEEDTAGS2STORE:
                targetValue = FEEDELHANDLERS[chKey](item) if chKey in FEEDELHANDLERS else item.getText()
                auxPrimKey, secKey = chKey
                primKey = auxPrimKey or NONENSKEY
                if primKey not in data['infoChannel']:
                    data['infoChannel'][primKey] = dict()
                data['infoChannel'][primKey][secKey] = targetValue
            else:
                if UNMANAGEDKEYS:
                    if 'feed' not in UNMANAGEDKEYS:
                        UNMANAGEDKEYS['feed'] = dict()
                    UNMANAGEDKEYS['feed'].get(chKey, []).append(str(item))

    result = FeedData(**data)

    return result  # print(channel)


# TODO: Currently only fields for podcasts, original idea of all this was for RSS from
#       news sources so there will be missing fields

def parseFeedItem(dataItem: bs4.element.Tag, feedMetadata: dict, UNMANAGEDKEYS: Optional[dict] = None) -> FeedItemData:
    MetadataKeys2Use = {'source', 'tstamp'}
    ITEMELHANDLERS = {(None, 'enclosure'): processEnclosure, (None, 'pubDate'): processPubDate,
                      ('itunes', 'keywords'): processKeywords,  # TOTHINK: ('itunes','duration'),
                      }

    resultDict = dict()
    resultDict['raw'] = str(dataItem)
    resultDict['metadata'] = {k: feedMetadata.get(k, None) for k in MetadataKeys2Use}
    resultDict['infoItem'] = dict()
    if dataItem.name != "item":
        return None

    for ch in dataItem.children:
        if isinstance(ch, NavigableString):
            continue
        chKey = extractTagKey(ch)

        if chKey in ITEMTAGS2IGNORE:
            continue
        elif chKey in ITEMTAGS2STORE:
            targetValue = ITEMELHANDLERS[chKey](ch) if chKey in ITEMELHANDLERS else ch.getText()
            auxPrimKey, secKey = chKey
            primKey = auxPrimKey or NONENSKEY
            if primKey not in resultDict['infoItem']:
                resultDict['infoItem'][primKey] = dict()
            resultDict['infoItem'][primKey][secKey] = targetValue
        else:
            if UNMANAGEDKEYS:
                if 'item' not in UNMANAGEDKEYS:
                    UNMANAGEDKEYS['item'] = dict()
                UNMANAGEDKEYS['item'].get(chKey, []).append(str(dataItem))

    # print(resultDict)
    result = FeedItemData(**resultDict)
    return result


def equalDicts(a: dict, b: dict) -> bool:
    # Comparable items
    chDataA = {it for it in a.items() if not isinstance(it[1], (dict, set))}
    chDataB = {it for it in b.items() if not isinstance(it[1], (dict, set))}

    if (chDataA - chDataB) or (chDataB - chDataA):
        return False

    for k, v in a.items():
        if not isinstance(v, (dict, set)):
            continue
        elif isinstance(v, (dict)):
            if not equalDicts(v, b.get(k, dict())):
                return False
        elif isinstance(v, (set)):
            if v.symmetric_difference(b.get(k, set())):
                return False

    return True


def mergeItemList(older: list[FeedItemData], newer: list[FeedItemData]) -> list[FeedItemData]:
    dictA = {(it.guid, it.pubDate): it for it in older}
    dictB = {(it.guid, it.pubDate): it for it in newer}

    resultDict = dict()
    resultDict.update(dictA)
    resultDict.update(dictB)

    return list(resultDict.values())


def preparaParams(data: dict, exclusions: Union[list, set, None], transformers: Optional[dict],
                  keyTranslations: Optional[dict]) -> dict:
    actExclusions = exclusions or set()
    actTranslations = keyTranslations or dict()

    result = {actTranslations.get(k, k): transformers.get(k, lambda x: x)(v) for k, v in data.items() if
              k not in actExclusions}
    return result
