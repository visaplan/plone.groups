# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""
utils-Modul für Browser groupdesktop

Autor: Tobias Herp
"""


# ----------- Hilfsfunktionen für getLoopDicts:
def basicfilter(pt):
    """
    >>> basicfilter('UnitraccBinary')
    ['portal_type=UnitraccBinary']
    """
    return ['portal_type=%s' % (pt, )]


def make_authorfilter(userid):
    """
    >>> ff = make_authorfilter('Zampano')
    >>> ff('UnitraccBinary')
    ['portal_type=UnitraccBinary', 'author=Zampano']
    """
    AUTHOR = 'author=%s' % userid

    def inner(pt):
        return basicfilter(pt) + [AUTHOR]
    return inner


def make_groupfilter(gid):
    """
    >>> ff = make_groupfilter('Authors')
    >>> ff('UnitraccBinary')
    ['portal_type=UnitraccBinary', 'group=Authors']
    """
    GROUP = 'groups=%s' % gid

    def inner(pt):
        return basicfilter(pt) + [GROUP]
    return inner


if __name__ == "__main__":
    import doctest
    doctest.testmod()
