from utils.helper import read_file_generator

PROXY = "http://geonode_qOKUkE5MOG-type-residential:b5d0fdc8-f72a-4670-b0da-5a40b6743797@proxy.geonode.io:9000"
KEYWORDS_FILE = list(read_file_generator("data/keywords.txt"))
URLS_FILE = list(read_file_generator("data/dork_urls.txt"))
SHOPPING_DORK = "data/shopping_dork.txt"