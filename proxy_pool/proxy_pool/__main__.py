import logging
import sys

import graypy
import prometheus_client

from proxy_pool import settings, app

prometheus_client.start_http_server(int(settings.PROMETHEUS_PORT))

logging_handlers = []
if settings.GRAYLOG_GELFUDP_LOGGER is not None:
    graylog_handler = graypy.GELFUDPHandler(settings.GRAYLOG_GELFUDP_LOGGER['host'],
                                            int(settings.GRAYLOG_GELFUDP_LOGGER['port']))
    logging_handlers.append(graylog_handler)
if settings.CONSOLE_LOGGER:
    console_handler = logging.StreamHandler(sys.stdout)
    logging_handlers.append(console_handler)

logging.basicConfig(level=int(settings.LOGGING_LEVEL), handlers=logging_handlers, format=settings.LOGGING_FORMAT)

app.bootstrap()
