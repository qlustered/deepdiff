from collections import OrderedDict, defaultdict
from threading import Lock
from deepdiff.helper import SetOrdered, not_found


class DistanceCache:
    """
    Bounded LRU cache used by DeepDiff's distance calculations.

    Built on ``collections.OrderedDict`` so DeepDiff has no compiled
    dependency for caching. A lock keeps the compound get/move and
    set/evict operations safe when a cache is shared across threads,
    including on free-threaded Python builds.
    """

    __slots__ = ('cache', 'capacity', 'lock')

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError('Capacity of DistanceCache needs to be positive.')  # pragma: no cover.
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            cache = self.cache
            try:
                value = cache[key]
            except KeyError:
                return not_found
            cache.move_to_end(key)
            return value

    def set(self, key, report_type=None, value=None):
        with self.lock:
            cache = self.cache
            if report_type:
                content = cache.get(key)
                if content is None:
                    content = defaultdict(SetOrdered)
                content[report_type].add(value)
                value = content
            cache[key] = value
            cache.move_to_end(key)
            if len(cache) > self.capacity:
                cache.popitem(last=False)

    def __contains__(self, key):
        return key in self.cache


LFUCache = DistanceCache


class DummyLFU:

    def __init__(self, *args, **kwargs):
        pass

    set = __init__

    def get(self, *args, **kwargs):
        return not_found

    def __contains__(self, key):
        return False
