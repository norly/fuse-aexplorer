from stat import S_IFDIR


class FuseCache():
    def __init__(self):
        # Initialize virtual root
        self.cache = {}

    # Cache tuple:
    # (dict of attrs, dict of children in folder)


    def getattr(self, path):
        paths = [p for p in path.split('/') if len(p) > 0]
        #print(paths)

        # Virtual root
        st = dict(st_mode=(S_IFDIR | 0o755), st_nlink=2)

        c = self.cache
        for p in paths:
            if c == None:
                return None

            if p not in c:
                return None

            (st, c) = c[p]

        return st


    def getkids(self, path):
        paths = [p for p in path.split('/') if len(p) > 0]

        c = self.cache
        for p in paths:
            if c == None:
                return None

            if p not in c:
                return None

            (_, c) = c[p]

        return c


    # Set a cache node's children and their attributes.
    # This implicitly purges any prvious children from the cache.
    # Thus, those directories will be re-scanned next time.
    def setkids(self, path, children):
        paths = [p for p in path.split('/') if len(p) > 0]

        c = self.cache
        for p in paths:
            # We expect to be able to walk the path, because we can't get
            # there without Linux' VFS stat'ing all directories leading up.
            parent = c
            (_, c) = c[p]

        if (c == self.cache):
            self.cache = children
        else:
            (st, _) = parent[p]
            parent[p] = (st, children)
