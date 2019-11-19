import logging
import os

from logging.handlers import RotatingFileHandler

#: Log line format
LOG_FORMAT = '%(asctime)-15s [%(name)s] [%(levelname)s] %(message)s'


class LoggerFactory:
    initialized = False

    def __init__(self, folder: str = '.', filename: str = 'application.log',
                 console_level: str = "INFO", file_level: str = "INFO"):
        if not self.initialized:
            self.initialized = True
            self._log_folder = folder
            self._log_filename = folder + os.sep + filename
            if not os.path.exists(self._log_folder):
                os.mkdir(self._log_folder)
            should_roll_over = os.path.isfile(self._log_filename)
            self._formatter = logging.Formatter(LOG_FORMAT)
            self._console_handler = logging.StreamHandler()
            self._console_handler.setLevel(LoggerFactory._translate_level(console_level))
            self._console_handler.setFormatter(self._formatter)
            self._file_handler = RotatingFileHandler(
                self._log_filename, mode='a', backupCount=50)
            self._file_handler.setLevel(LoggerFactory._translate_level(file_level))
            self._file_handler.setFormatter(self._formatter)
            if should_roll_over:
                self._file_handler.doRollover()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_inst'):
            cls._inst = super(LoggerFactory, cls).__new__(cls)
        return cls._inst

    @staticmethod
    def _translate_level(level):
        lv = logging.INFO
        if level == "DEBUG":
            lv = logging.DEBUG
        elif level == "WARNING":
            lv = logging.WARNING
        elif level == "ERROR":
            lv = logging.ERROR
        elif level == "CRITICAL":
            lv = logging.CRITICAL
        return lv

    def get_new_logger(self, name: str):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self._console_handler)
        logger.addHandler(self._file_handler)
        return logger
