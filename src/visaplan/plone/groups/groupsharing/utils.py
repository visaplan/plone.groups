# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et tw=79
"""
utils.Modul für Browser groupsharing

Autor: Tobias Herp
"""

# Standardmodule
from datetime import date
from time import strftime
from collections import defaultdict

# Unitracc-Tools:
from visaplan.tools.coding import safe_decode


def makedate(s, default=None):
    """
    Konvertiere ein Datum aus einem Datepicker-Datumsfeld

    >>> import datetime
    >>> makedate('1.4.2014')
    datetime.date(2014, 4, 1)

    Siehe auch unitracc.tools.forms.make_date_parser
    (ohne default-Wert, mit strptime)
    """
    if not s:
        return default
    if isinstance(s, basestring):
        liz = map(int, s.split('.'))
    else:
        liz = map(int, s)
    assert len(liz) == 3, '"d.m.yyyy" date value expected (%r)' % s
    liz.reverse()
    return date(*tuple(liz))


def datefromform(prefix, name, form, default=None, logger=None):
    """
    Lies einen Datumswert aus den Formulardaten, unter Tolerierung
    fehlerhafter Formulardaten (wenn reparierbar)

    >>> form={'start_heinz': '2016-05-02',
    ...       'end_heinz': ('', ''),
    ...       'end_nemo': ('', '2016-06-17')}
    >>> datefromform('start_', 'heinz', form)
    datetime.date(2016, 5, 2)
    >>> datefromform('end_', 'heinz', form)
    >>> datefromform('end_', 'nemo', form)
    Traceback (most recent call last):
      ...
    ValueError: Single value expected; 2-tuple of identical values tolerated

    """
    key = prefix + name
    val = form.get(key, default)
    if val is None:
        return val
    result = None
    try:
        result = makedate(val, default)
    except ValueError as e:
        if logger is not None:
            logger.error('Value for %(key)r: invalid date (%(val)r)', locals())
        if isinstance(val, (list, tuple)):
            if len(val) == 2 and val[0] == val[1]:
                result = makedate(val[0], default)
            else:
                logger.error("Can't recover from error!")
                logger.exception(e)
                raise
        else:
            raise
    finally:
        return result


def default_dates_dict():
    """
    zur Verwendung mit defaultdict
    """
    return {'start_date': None,
            'end_date': None,
            }


def _traverse_dict(dic, groups):
    """
    Hilfsfunktion für build_groups_set:
    realisiert die Rekursion.
    Es wird abgebrochen, wenn es keine Änderungen mehr gab.

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        }

    <groups> enthält zunächst die <uid> (oder gid) selbst:
    >>> groups = set(['user_a'])

    Der Rückgabewert wird üblicherweise nicht verwendet;
    er gibt die Anzahl der Iterationen an:
    >>> _traverse_dict(dic, groups)
    2
    >>> sorted(groups)
    ['group_a', 'group_b', 'user_a']
    """
    iterations = 1
    while True:
        finished = True
        for gid, members in dic.iteritems():
            if gid in groups:
                continue
            if groups.intersection(members):
                groups.add(gid)
                finished = False
        if finished:
            break
        iterations += 1
    return iterations


def build_groups_set(dic, userid):
    """
    Hilfsfunktion für is_member_of_factory

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        }
    >>> groups = build_groups_set(dic, 'user_a')
    >>> sorted(groups)
    ['group_a', 'group_b', 'user_a']
    """
    groups = set([userid])
    _traverse_dict(dic, groups)
    return groups


def build_groups_depthdict(dic, userid):
    """
    Erzeugt ein dict, das die Gruppen-IDs und die Rekursionstiefen enthält.

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        }
    >>> groups = build_groups_depthdict(dic, 'user_a')
    >>> groups['user_a']
    0
    >>> groups['group_b']
    1
    >>> groups['group_a']
    2
    >>> sorted(groups.items())
    [('group_a', 2), ('group_b', 1), ('user_a', 0)]
    """
    groups_dict = {userid: 0}  # Identität
    groups = set([userid])
    # -------------------------- [ nach _traverse_dict ... [
    iterations = 1
    newly_found = set()
    while True:
        for gid, members in dic.iteritems():
            if gid in groups:
                continue
            if groups.intersection(members):
                newly_found.add(gid)
        if newly_found:
            groups.update(newly_found)
            while newly_found:
                gid = newly_found.pop()
                groups_dict[gid] = iterations
            iterations += 1
        else:
            break
    # -------------------------- ] ... nach _traverse_dict ]
    return groups_dict


def build_groups_reversedict(dic):
    """
    Erzeuge ein dict-Objekt, das die Zuordnungen umkehrt:

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        }
    >>> membership = build_groups_reversedict(dic)
    >>> membership['user_a']
    set(['group_b'])
    >>> sorted(membership.items())
    [('group_b', set(['group_a'])), ('group_c', set(['group_a'])), ('user_a', set(['group_b'])), ('user_b', set(['group_b'])), ('user_c', set(['group_c']))]

    Das Ergebnis-dict enthält nur die direkten Zuordnungen;
    die rekursive Auflösung ist ein weiterer Schritt.
    """
    revdic = defaultdict(set)
    for gid, members in dic.items():
        for uog in members:
            revdic[uog].add(gid)
    return dict(revdic)


def recursive_memberships(uogid, revdic, exclude_member=False):
    """
    Ermittle die rekursiv aufgelösten Gruppenmitgliedschaften des übergebenen
    Users bzw. der Gruppe (uogid, "user or group id") anhand des revertierten
    dicts (erzeugt von --> build_groups_reversedict)

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        }
    >>> membership = build_groups_reversedict(dic)
    >>> gm = recursive_memberships('user_a', membership)
    >>> sorted(gm)
    ['group_a', 'group_b', 'user_a']

    Das "anfragende Mitglied" ist im Ergebnis enthalten;
    für User-IDs macht es Sinn, exclude_member=True zu übergeben:
    >>> sorted(recursive_memberships('user_a', membership, True))
    ['group_a', 'group_b']

    Zirkelschlüsse sind unkritisch; sie führen lediglich dazu, daß die
    angefragte Gruppe in der zurückgegebenen Menge enthalten ist:
    >>> dic.update({'group_d': ['group_e'],
    ...             'group_e': ['group_f'],
    ...             'group_f': ['group_d'],
    ...             'group_A': ['group_B'],
    ...             'group_B': ['group_A'],
    ...             })
    >>> membership = build_groups_reversedict(dic)
    >>> sorted(recursive_memberships('group_d', membership))
    ['group_d', 'group_e', 'group_f']
    >>> sorted(recursive_memberships('group_A', membership))
    ['group_A', 'group_B']

    User, die in keiner Gruppe sind:
    >>> recursive_memberships('user_x', membership, True)
    set([])
    """
    res = set([uogid])
    try:
        newly_found = set(revdic[uogid])
    except KeyError:  # User ohne Gruppe
        pass
    else:
        while newly_found:
            res.update(newly_found)
            this_iteration = set()
            for gid in newly_found:
                try:
                    found_here = revdic[gid].difference(res)
                    if found_here:
                        this_iteration.update(found_here)
                except KeyError:
                    pass
            res.update(this_iteration)
            newly_found = this_iteration
    finally:
        if exclude_member:
            res.discard(uogid)
        return res


def recursive_members(gids, dic,
                      containers=None,
                      groups_only=False,
                      users_only=False,
                      default_to_all=False):
    """
    Ermittle die rekursiv aufgelösten Mitglieder der übergebenen
    Gruppen.

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        'group_d': ['group_a'],
    ...        }
    >>> am = recursive_members(['group_a'], dic, groups_only=True)
    >>> sorted(am)
    ['group_b', 'group_c']
    >>> sorted(recursive_members(['group_a'], dic))
    ['group_b', 'group_c', 'user_a', 'user_b', 'user_c']
    >>> sorted(recursive_members(['group_d'], dic, users_only=True))
    ['user_a', 'user_b', 'user_c']
    >>> sorted(recursive_members(['group_d'], dic, groups_only=True))
    ['group_a', 'group_b', 'group_c']

    containers-Argument:
    - True: die Container werden hinzugefügt
      (mit groups_only: ... sofern es wirklich Gruppen sind)
    - False: die Container werden ausgefiltert
    - None (Vorgabe): weder aktiv hinzufügen noch ausfiltern

    >>> kwargs = {'groups_only': True,
    ...           'containers': True}
    >>> sorted(recursive_members(['group_d'], dic, **kwargs))
    ['group_a', 'group_b', 'group_c', 'group_d']
    >>> kwargs = {'groups_only': True,
    ...           'containers': False}
    >>> sorted(recursive_members(['group_c', 'group_d'], dic, **kwargs))
    ['group_a', 'group_b']
    >>> kwargs = {'users_only': True,
    ...           'containers': True}
    >>> sorted(recursive_members(['group_d'], dic, **kwargs))
    ['user_a', 'user_b', 'user_c']
    >>> kwargs = {'containers': False}

    Das spezielle Argument default_to_all erfordert groups_only=True
    und gibt alle Gruppen zurück, sofern keine Gruppen-IDs übergeben wurden:

    >>> sorted(recursive_members([], dic, groups_only=True,
    ...                          default_to_all=True))
    ['group_a', 'group_b', 'group_c', 'group_d']
    """
    if users_only and groups_only:
        raise ValueError('recursive_members(%(gids)r): '
                         '*either* groups_only '
                         '*or* users_only!'
                         % locals())
    if not gids:
        if default_to_all:
            assert groups_only, 'default_to_all erfordert groups_only!'
            return set(dic.keys())
        else:
            # ohne default_to_all: keine Gruppen, keine Mitglieder
            return set()
    filtered = users_only or groups_only
    res = set()
    exclude = set()
    if containers is None:
        pass
    elif not containers:
        exclude.update(gids)
    for gid in gids:
        try:
            newly_found = set(dic[gid]).difference(res)
            if containers and not users_only:
                res.add(gid)
        except KeyError:  # keine Gruppe, oder?!
            if containers and not groups_only:
                res.add(gid)
        else:
            while newly_found:
                res.update(newly_found)
                this_iteration = set()
                for mid in newly_found:  # member id
                    try:
                        found_here = set(dic[mid]).difference(res)
                        if found_here:
                            this_iteration.update(found_here)
                        if users_only:   # Gruppen aus Ergebnis entfernen
                            exclude.add(mid)
                    except KeyError:
                        if groups_only:  # Benutzer aus Ergebnis entfernen
                            exclude.add(mid)
                res.update(this_iteration)
                newly_found = this_iteration
    res.difference_update(exclude)
    return res


# ------------------------- [ Funktionen zum Sortieren ... [
def make_keyfunction(key, factory=None):
    """
    Factory-Funktion: gib eine Funktion zurück, die als Schlüsselfunktion
    verwendet werden kann (list.sort(key=make_keyfunction(...)).

    >>> dic={'id': 123, 'title': 'Alphanumeric'}
    >>> make_keyfunction('id')(dic)
    123
    >>> make_keyfunction('title')(dic)
    'Alphanumeric'

    Verwendung zum Sortieren:

    >>> dic2={'id': 456, 'title': 'Aaa'}
    >>> dic3={'id': 100, 'title': 'bbb'}
    >>> liz=[dic, dic2, dic3]
    >>> sorted(liz, key=make_keyfunction('id'))
    [{'id': 100, 'title': 'bbb'}, {'id': 123, 'title': 'Alphanumeric'}, {'id': 456, 'title': 'Aaa'}]
    >>> sorted(liz, key=make_keyfunction('title'))
    [{'id': 456, 'title': 'Aaa'}, {'id': 123, 'title': 'Alphanumeric'}, {'id': 100, 'title': 'bbb'}]

    Das optionale Argument <factory> ist eine Funktion, die den Wert für die
    Rückgabe transformiert (z. B. für Zahlen, die als Strings abgespeichert
    sind).
    """
    if factory is None:
        def keyfunc(dic):
            return dic[key]
    else:
        def keyfunc(dic):
            return factory(dic[key])
    return keyfunc


# schonmal vorgefertigt:
def getgrouptitle(dic):
    """
    Oft benötigte Schlüsselfunktion zum Sortieren von Listen von Dictionarys
    """
    return safe_decode(dic.get('group_title', ''))


def getcoursetitle(dic):
    """
    Schlüsselfunktion für Ergebnisse von
    .browser.get_group_mapping_course__factory()()
    """
    return safe_decode(dic.get('course_title', ''))


def gettitle(dic):
    """
    Dasselbe wie:
    gettitle = make_keyfunction('title', safe_decode)

    >>> dic={'id': 'abc123', 'title': 'Alphanumeric'}
    >>> gettitle(dic)
    u'Alphanumeric'
    >>> make_keyfunction('title')(dic)
    'Alphanumeric'
    """
    return safe_decode(dic.get('title', ''))
# ------------------------- ] ... Funktionen zum Sortieren ]


# ------------------------- [ Funktionen für Debugging ... [
def make_break_at_row(member_id):
    """
    Als Kriteriuzm für bedingten Breakpoint; Beispiel:

      break_at_row = make_break_at_row('Enrico')
      b 123, break_at_row(row)
    """
    from pprint import pprint
    break_all = None
    break_none = False
    if isinstance(member_id, basestring):
        member_ids = set([member_id])
    elif isinstance(member_id, (bool, int)):
        break_all = bool(member_id)
    elif member_id is None:
        break_none = True
    else:
        member_ids = set(member_id)

    def break_at_row(row):
        pprint(('row:', row))
        if break_all is not None:
            return break_all
        elif break_none:
            return False
        else:
            try:
                return row['member_id_'] in member_ids
            except KeyError as e:
                print e
                print 'Schluessel fehlt!'
                return True
    return break_at_row


def journal_text(lst):
    res = []
    for tup in lst:
        ok, txt = tup
        res.append('%s: %s' %
                   (ok and 'OK' or 'Fehler',
                    txt))
    # res.append('')
    return '\n'.join(res)
# ------------------------- ] ... Funktionen für Debugging ]


if __name__ == '__main__':
    import doctest
    doctest.testmod()
