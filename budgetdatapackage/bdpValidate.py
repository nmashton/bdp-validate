from metadataValidate import validateMetadata
from csvValidate import resourceToCSVValidator
import json
import csv
import urllib
import sys
if sys.version_info[0] < 3:
    import urlparse
    urllib.parse = urlparse
    urllib.request = urllib
    next = lambda x: x.next()
    bytes = str
    str = unicode
else:
    import urllib.request

SCHEMA = json.loads(open("./schema.json","r").read())

def validate(uri, deep=True):
    """
    Validates a budget data package.
    """
    # function aliases to open URIs
    join = urllib.parse.urljoin
    opener = lambda d: urllib.request.urlopen(join(uri,d))

    # the descriptor
    datapackage = json.loads(opener("datapackage.json").read())

    # validate the descriptor
    validateMetadata(datapackage,SCHEMA)

    # validate each of its resources
    missing = []
    for r in datapackage["resources"]:
        v = resourceToCSVValidator(r,deep)
        try:
            d = csv.reader(opener(r["path"]))
            v.validate(d)
        except IOError:
            missing.append(r["path"])
            pass
    if missing:
        raise ValueError("ValueError: missing data resources (" + (", ".join(missing)) + ")")