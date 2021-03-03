from __future__ import annotations
import typing as tp
from abc import ABC, abstractmethod
from itertools import takewhile
from anytree import NodeMixin
from blox_old.core.exceptions import PersisterError
from typing import TYPE_CHECKING
import logging
from blox_old.core.exceptions import PersisterError


# The cool way to avoid circular imports but still use type annotations
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PersisterNodeMixin:

    # This method must be implemented (provided by NamedNodeMixin)
    def iter_path_reverse(self) -> tp.Iterable[PersisterNodeMixin]:
        raise NotImplementedError

    @property
    def persisters(self):
        """ An iterable of persisters associated with the node """
        return {}

    def get_persistent_value(self, *args, **kwargs):
        """ Get the value to be persisted in the persister """
        pass

    def set_persistent_value(self, value, *args, **kwargs):
        """ Set the persisted value to a persister """
        pass

    def save(self, *args, **kwargs):
        """ Persist the value of the current node using the first persister that can do it """

        success = False
        for node in self.iter_path_reverse():
            for persiter_name, persister in node.persisters.items():

                if not persister.can_save(self, *args, **kwargs):
                    continue

                try:
                    persister.save(self, *args, **kwargs)
                    success = True

                except PersisterError as e:
                    logger.warning(e)
                    continue

                if persister.final:
                    return

        if not success:
            raise PersisterError(f"Could not save {self} since no capable persister was found")

    def load(self, *args, **kwargs):

        # Do chain-of-responsibility: find the first persister that gets the job done
        for node in self.iter_path_reverse():
            for persiter_name, persister in node.persisters.items():

                if not persister.can_load(self, *args, **kwargs):
                    continue

                try:
                    return persister.load(self, *args, **kwargs)

                except PersisterError as e:
                    logger.warning(e)
                    continue

        raise PersisterError(f"Could not load {self} since no capable persister was found")
