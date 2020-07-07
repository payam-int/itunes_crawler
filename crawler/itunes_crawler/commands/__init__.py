import logging

from itunes_crawler import settings

logging.basicConfig(level=int(settings.LOGGING_LEVEL), format=settings.LOGGING_FORMAT)
