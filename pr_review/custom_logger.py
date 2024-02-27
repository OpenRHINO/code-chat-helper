# custom_logger.py
import logging
from gunicorn.glogging import Logger

class CustomLogger(Logger):
    def access(self, resp, req, environ, request_time):
        if req.path != '/healthz':
            super().access(resp, req, environ, request_time)
