import logging
import os

LOGGING_FORMAT = '[%(asctime)s][%(name)s][%(levelname)s] %(message)s'
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', logging.DEBUG)

GRAYLOG_GELFUDP_LOGGER = {
    'host': os.getenv('GRAYLOG_GELFUDP_LOGGER_HOST', 'localhost'),
    'port': os.getenv('GRAYLOG_GELFUDP_LOGGER_PORT', 12201),
}

CONSOLE_LOGGER = os.getenv('CONSOLE_LOGGER', 'true') == 'true'

POSTGRES = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'example'),
    'database': os.getenv('POSTGRES_DB', 'database'),
}

REQUESTS_PROXY = {
    'http': os.getenv('REQUESTS_PROXY_HTTP', 'socks5://localhost:9050'),
    'https': os.getenv('REQUESTS_PROXY_HTTPS', 'socks5://localhost:9050'),
}

WORKERS_COUNT = os.getenv('WORKERS_COUNT', '10')
PROMETHEUS_PORT = os.getenv('PROMETHEUS_PORT', '8000')

JOB_LOCK_PREFIX = 10000

SKIP_PROXY = [
    'feeds.buzzsprout.com',
    'feed.podbean.com'
]
