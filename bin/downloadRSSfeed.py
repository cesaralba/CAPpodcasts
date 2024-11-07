from locale import LC_ALL, setlocale

from configargparse import ArgumentParser

from libs.RSS.feed import FeedRecord


def parse_arguments():
    descriptionTXT = "Prepares a booklet for the next game of a team"

    parser = ArgumentParser(description=descriptionTXT)
    parser.add_argument("-o", "--outfile", dest="outfile", action="store", help="Filename to store result. ",
                        required=False, )

    parser.add_argument("-t", "--title", dest="title", action="store", required=False, default='FeedTitle',
                        help="URL for the RSS feed", )
    parser.add_argument("-u", "--url", dest="url", action="store", required=True,
                        help="URL for the RSS feed", )
    parser.add_argument("-p", "--paged", dest='isPaged', action="store_true", required=False, default=False,
                        help="RSS data is paged or just a single file", )
    parser.add_argument("-m", "--maxPages", dest='maxPages', action="store", type=int, required=False, default=1,
                        help="Max numbers of pages to retrieve, 0 for infinite", )

    parser.add_argument("-n", "--dry-run", dest='dryrun', action="store_true", required=False, default=False,
                        help="Do nothing", )
    result = parser.parse_args()

    return result


def main(args):

    myFeed =FeedRecord(URL=args.url, title=args.title,paged=args.isPaged, maxPages=args.maxPages)

    myItems = myFeed.retrieve(dryRun=args.dryrun)

    if not args.dryrun:
        myItems.dump(args.outfile)

if __name__ == '__main__':
    argsCLI = parse_arguments()
    main(argsCLI)
