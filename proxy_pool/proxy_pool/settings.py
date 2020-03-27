import logging
import os

LOGGING_FORMAT = '[%(asctime)s][%(name)s][%(levelname)s] %(message)s'
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', logging.DEBUG)

GRAYLOG_GELFUDP_LOGGER = {
    'host': os.getenv('GRAYLOG_GELFUDP_LOGGER_HOST', 'localhost'),
    'port': os.getenv('GRAYLOG_GELFUDP_LOGGER_PORT', 12201),
}

CONSOLE_LOGGER = os.getenv('CONSOLE_LOGGER', 'true') == 'true'

PROMETHEUS_PORT = os.getenv('PROMETHEUS_PORT', '8000')
