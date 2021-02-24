from .base import PersisterBackend, PersisterError
import shelve


class Shelve(PersisterBackend):

    def __init__(self, filepath):
        self.filepath = filepath
        self._shelve_instance = None

    def __enter__(self):
        self._shelve_instance = shelve.open(self.filepath)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._shelve_instance.close()

    def __check_init(self):
        if self._shelve_instance is None:
            raise PersisterError("Shelve instance must be opened first")

    def __contains__(self, item):
        self.__check_init()
        return item in self._shelve_instance

    def __setitem__(self, key, value):
        self.__check_init()
        self._shelve_instance[key] = value

    def __getitem__(self, item):
        self.__check_init()
        return self._shelve_instance[item]
