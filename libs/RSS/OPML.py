from collections import namedtuple
from bs4 import NavigableString

from libs.RSS.Utils import feed2URI, parseXMLContent_BS4, readURI, processPubDate

OPMLfeed = namedtuple('OPMLfeed',field_names=['title','text','xmlUrl','type','unlisted'],defaults={'unlisted': dict()})


class OPMLfile:
    def __init__(self,**kwargs):
        for k,v in kwargs.items():
            self.__setattr__(k,v)

    @classmethod
    def readOPMLdata(cls, filename:str):
        URI=feed2URI(filename)

        fileContents = readURI(URI)

        fileData = parseXMLContent_BS4(fileContents.data)

        builderArgs = {'source':URI,'feeds':list()}

        builderArgs.update(processOPMLhead(fileData))

        for ch in fileData.find('body').children:

            if isinstance(ch, NavigableString):
                continue
            itemName = ch.name
            if itemName == 'outline':
                params={'unlisted':dict()}
                for k,v  in ch.attrs.items():
                    if k in OPMLfeed._fields:
                        params[k]=v
                    else:
                        params['unlisted'][k]=v

                newFeed = OPMLfeed(**params)
                builderArgs['feeds'].append(newFeed)
            else:
                print(f"OPMLfile.readOPMLdata: unknown field {itemName}: {str(ch)}")

        return cls(**builderArgs)

def processOPMLhead(fileData):
    result = dict()
    for ch in fileData.find('head').children:
        if isinstance(ch, NavigableString):
            continue

        itemName = ch.name
        if itemName == 'title':
            result[itemName] = ch.getText().strip()
        elif itemName == 'dateCreated':
            result[itemName] = processPubDate(ch)
        else:
            print(f"OPMLfile.readOPMLdata: unknown field {itemName}: {str(ch)}")

    return result


#TODO: folders (from Akregator exports)