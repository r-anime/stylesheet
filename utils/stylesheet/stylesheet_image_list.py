"""Provide the StylesheetImageList class."""
import collections

from stylesheet import StylesheetImage


class StylesheetImageList(collections.UserList):
    """A list of Reddit Stylesheet Images that facilitates custom sorting and
    filtering.
    """

    @property
    def by_filename(self):
        """Provide a shallow copy of this object and set sorting by `filename`.
        """
        return self._sorted_by(lambda x: x.filename)

    @property
    def by_reddit_name(self):
        """Provide a shallow copy of this object and set sorting by
        `reddit_name`.
        """
        return self._sorted_by(lambda x: (len(x.reddit_name), x.reddit_name))

    @property
    def by_usage_count(self):
        """Provide a shallow copy of this object and set sorting by
        `usage_count`.
        """
        return self._sorted_by(lambda x: x.usage_count)

    @property
    def desc(self):
        """Provide a shallow copy of this object and set a descending order for
        sorting.
        """
        return self._sorted_by(self._sort_key, True)

    @property
    def removed(self):
        """Provide a shallow copy of this object and filter the images with the
        `is_removed` property 'True'.
        """
        return self._filtered_by(lambda x: x.is_removed)

    @property
    def new(self):
        """Provide a shallow copy of this object and filter the images with the
        `is_new` property 'True'.
        """
        return self._filtered_by(lambda x: x.is_new)

    @property
    def unchanged(self):
        """Provide a shallow copy of this object and filter the images with the
        `is_new` property 'False'.
        """
        return self._filtered_by(lambda x: not x.is_new)

    @property
    def unnamed(self):
        """Provide a shallow copy of this object and filter the images with the
        `reddit_name` property 'None'.
        """
        return self._filtered_by(lambda x: x.reddit_name is None)

    def __init__(self, initlist=None, sort_key=None, sort_reverse=False,
                 condition=None):
        """Construct an instance of the StylesheetImageList object."""
        super().__init__(initlist)
        self._sort_key = sort_key
        self._sort_reverse = sort_reverse
        self._condition = condition

    def __iter__(self):
        """Provide a generator that applies the given condition and sorting of
        the underlying list of images.
        """
        if self._condition:
            data = filter(self._condition, self.data)
        else:
            data = self.data

        if self._sort_key:
            data = sorted(data, key=self._sort_key, reverse=self._sort_reverse)

        for item in data:
            yield item

    def __len__(self):
        """Return a count of the underlying list of images after applying the
        given condition and sorting.
        """
        if self._condition:
            data = [item for item in self.data if self._condition(item)]
        else:
            data = self.data

        return len(data)

    def _filtered_by(self, condition):
        """Provide a shallow copy of this object while applying the provided
        condition.
        """
        return self.__class__(
            initlist=self.data,
            sort_key=self._sort_key,
            sort_reverse=self._sort_reverse,
            condition=condition
        )

    def _sorted_by(self, sort_key, sort_reverse=None):
        """Provide a shallow copy of this object while applying the provided
        sorting configuration.
        """
        if sort_reverse is None:
            sort_reverse = self._sort_reverse

        return self.__class__(
            initlist=self.data,
            sort_key=sort_key,
            sort_reverse=sort_reverse,
            condition=self._condition
        )

    def find(self, **kwargs) -> StylesheetImage:
        """Return the `StylesheetImage` from the underlying list of images
        whose attributes are matching with provided arguments.
        """
        if self._condition:
            data = filter(self._condition, self.data)
        else:
            data = self.data

        for image in data:
            if all(getattr(image, key) == value
                   for key, value in kwargs.items()):
                return image

        return None
