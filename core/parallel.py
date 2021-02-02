class Batch:
    def __init__(self, data):
        self._data = data

    def __len__(self):
        return len(self._data)


