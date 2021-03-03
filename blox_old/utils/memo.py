import typing as tp


class EnumeratedMemo:
    """ Implemets a memo for lookup in a list of items each having a name """

    def __init__(self, container_fn: tp.Callable, name_fn: tp.Callable, filter_fn: tp.Optional[tp.Callable]):
        self.__container_fn = container_fn
        self.__memo = {}
        self.__filter_fn = filter_fn
        self.__name_fn = name_fn

    def __contains__(self, item) -> bool:
        """ Check whether self.block contains item as one of its children, where item can be
        either a string or an instance of Block.
        """

        # Get the container instance
        container = self.__container_fn()

        def contains(idx, itm):
            return idx < len(container) and self.__filter_fn(container[idx]) and self.__name_fn(container[idx]) == itm

        # This is the case when we refer to sub-blocks by their names
        # We'll use a memo here since this kind of check will be used often
        if isinstance(item, str):

            child_idx = self.__memo.get(item, None)

            # This is the case that the memo finds something
            if child_idx is not None and contains(child_idx, item):
                return True

            # Otherwise, look-up the child one by one and update the memo
            for child_idx, child in enumerate(container):
                if contains(child_idx, item):
                    self.__memo[item] = child_idx
                    return True

            return False

        return False

    def __getitem__(self, item):
        """ Get a sub-block by name """

        if not isinstance(item, str):
            raise TypeError(f"Unsupported key type {type(item)}")

        # Get the container instance
        container = self.__container_fn()

        if item in self:
            # This line IS a bit hacky. We trust the __contains__ method to update self.__children_name_memo
            # in case item is actually one of block's children
            return container[self.__memo[item]]

        else:
            raise KeyError(item)
