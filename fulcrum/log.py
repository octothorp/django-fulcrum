import logging, sys

FORMAT = '[ %(levelname)s ] :: %(message)s'

def debug(msg, *args, **kwargs):
    logging.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logging.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logging.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logging.error(msg, *args, **kwargs)
    
def critical(msg, *args, **kwargs):
    logging.critical(msg, *args, **kwargs)


def init(config):
    logging.basicConfig(**config)

def basicConfig():
    return {
        'level': logging.DEBUG,
        'format': FORMAT
    }