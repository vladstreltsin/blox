import typing as tp


class EnumeratedMemo:
    """ Implemets a memo for lookup in a list of items where each has a unique name """

    def __init__(self, container_fn: tp.Callable, name_fn: tp.Callable, filter_fn: tp.Optional[tp.Callable]):
        """

        Parameters
        ----------
        container_fn
            A callable that returns the container (list) where to search
        name_fn
            A callable that returns the associated name for each object in the container
        filter_fn
            An optional filter to ignore certain objects in the container
        """
        self._container_fn = container_fn
        self._memo = {}
        self._filter_fn = filter_fn
        self._name_fn = name_fn

    def __contains__(self, item) -> bool:
        """ Check whether self.block contains item as one of its children, where item can be
        either a string or an instance of Block.
        """

        # Get the container instance
        container = self._container_fn()

        # This will check whether the container actually contains the object 'itm' at position 'idx'
        def container_contains(idx, itm):
            return idx < len(container) and \
                   self._filter_fn(container[idx]) and \
                   self._name_fn(container[idx]) == itm

        if isinstance(item, str):

            child_idx = self._memo.get(item, None)

            # This is the case that the memo finds something
            if (child_idx is not None) and container_contains(child_idx, item):
                return True

            # Otherwise, look-up the child one by one and update the memo
            for child_idx, child in enumerate(container):
                if container_contains(child_idx, item):
                    self._memo[item] = child_idx
                    return True

            return False

        return False

    def __getitem__(self, item):
        """ Get a sub-block by name """

        if not isinstance(item, str):
            raise TypeError(f"Unsupported key type {type(item)}")

        # Get the container instance
        container = self._container_fn()

        if item in self:
            # This line IS a bit hacky. We trust the __contains__ method to update self.__children_name_memo
            # in case item is actually one of block's children
            return container[self._memo[item]]

        else:
            raise KeyError(item)
