# import logging
import logging
import os

logging.getLogger("langchain").setLevel(logging.ERROR)

import colorlog

log_level = os.getenv("LOG_LEVEL", "WARNING").upper()

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(name)s: %(reset)s%(message)s")
)

# logger = colorlog.getLogger('example')
# logger.addHandler(handler)

# log_level = os.getenv("LOG_LEVEL", "WARNING").upper()

# # create console handler and set level to debug
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)

# # create formatter
# # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# # add formatter to ch
# ch.setFormatter(formatter)
