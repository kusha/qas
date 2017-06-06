#!/usr/bin/env python3

"""
Logging module.

Used for both regular logging and Websocket based UI reporting.
"""

import logging
import coloredlogs

logging.getLogger('requests').setLevel(logging.CRITICAL)


class InterfaceHandler(logging.Handler):
    """
    Modified logging handler, which pushes results to
    the specified multiprocessing queue.
    """
    def __init__(self, queue, *args, **kwargs):
        super(InterfaceHandler, self).__init__(*args, **kwargs)
        self.queue = queue  # assign queue

    def emit(self, record):
        log_entry = self.format(record)
        self.queue.put(log_entry)  # push formatted queue


class LoggingService():
    """
    Question answering system inherits logging service.

    .log attribute is main output spot of th system.
    """
    def __init__(self, logging_queue=None, debug=False):
        # self.regular_formatter = logging.Formatter(logging.BASIC_FORMAT)

        self.json_formatter = logging.Formatter('\
{"time": "%(asctime)s", "level": "%(levelname)s", "data": "%(message)s"}')

        # initalize logging if isn't initialized yet
        if not hasattr(self, 'log'):
            self.log = logging.getLogger(self.__class__.__name__)

            # initialize regular logger
            # handler = logging.StreamHandler()
            # handler.setFormatter(self.regular_formatter)
            # self.log.addHandler(handler)
            level = 'DEBUG' if debug else 'INFO'
            coloredlogs.install(level=level)

            # initialize webui communication
            if logging_queue is not None:
                interface_handler = InterfaceHandler(logging_queue)
                interface_handler.setFormatter(self.json_formatter)
                self.log.addHandler(interface_handler)

            # self.log.setLevel(logging.DEBUG)

    def add_output_queue(self, logging_queue):
        """
        Add another output queue.

        Allows logging on question answering systems to multiple channels.
        """
        interface_handler = InterfaceHandler(logging_queue)
        interface_handler.setFormatter(self.json_formatter)
        self.log.addHandler(interface_handler)
