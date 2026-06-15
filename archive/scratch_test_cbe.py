import logging
logging.basicConfig(level=logging.DEBUG)
from services.providers.cbe_provider import CbeProvider
provider = CbeProvider()
res = provider._fetch_live()
print(res)
