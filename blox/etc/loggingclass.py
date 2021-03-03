from __future__ import annotations
import logging
from blox.etc.utils import get_dynamic_attribute


class LoggerMixin:

    @property
    def logger(self) -> logging.Logger:
        return get_dynamic_attribute(self, '_logger',
                                     default=logging.getLogger(f'{self.__class__.__module__}.'
                                                               f'{self.__class__.__name__}'))
