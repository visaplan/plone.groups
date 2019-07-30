# -*- coding: utf-8 -*-

# Unitracc-Tools:
from visaplan.tools.coding import safe_decode

# ------------------------------------------------------ [ Daten ... [
STRUCTURE_GROUP_SUFFIXES = ['Reader', 'Author']
# -------------------------------- [ Gruppen für Kurse ... [
# Achtung, Kleinschreibung:
LEARNER_SUFFIX = intern('learner')
ALUMNI_SUFFIX = intern('alumni')
COURSE_GROUP_SUFFIXES = [LEARNER_SUFFIX, ALUMNI_SUFFIX]
# -------------------------------- ] ... Gruppen für Kurse ]
ALL_GROUP_SUFFIXES = STRUCTURE_GROUP_SUFFIXES + COURSE_GROUP_SUFFIXES
UID_CHARS = frozenset('0123456789abcdef')
SIMPLE_GROUP_INFO = {'uid': None,
                     'role': None,
                     }
PRETTY_MASK = {}
for role in ALL_GROUP_SUFFIXES:
    PRETTY_MASK[role] = u'%s group "{group}"' % role
if 0 and 'nur fuer den Parser':
    _('Author group "{group}"')
    _('Reader group "{group}"')
    _('learner group "{group}"')
    _('alumni group "{group}"')
# ------------------------------------------------------ ] ... Daten ]


def split_group_id(gid):
    """
    Splitte die übergebene Gruppen-ID auf und gib ein Dictionary zurück,
    das über eine etwaige "Rollenkomponente" informiert und dann auch
    die uid des zugehörigen Objekts enthält.

    Die Schlüssel 'uid' und 'role' haben String-Werte,
    sofern der Mittelteil wie eine korrekte UID aussieht und das Suffix
    eine der hierfür bekannten Rollen ist;
    ansonsten sind sie None.

    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_Author')
    {'role': 'Author', 'uid': 'f6350ab731c3601e925eac482206bda5'}

    Bei "normalen" Gruppen hat die scheinbare UID keine spezielle
    Bedeutung und wird daher nicht als solche zurückgegeben:

    >>> split_group_id('group_0123456789abcdef0123456789abcdef')
    {'role': None, 'uid': None}

    Das Suffix 'learner' repräsentiert keine echte Rolle (es wird stattdessen
    'Reader' vermittelt); es ist aber ein bekanntes Suffix und wird als solches
    zurückgegeben:

    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_learner')
    {'role': 'learner', 'uid': 'f6350ab731c3601e925eac482206bda5'}

    Wenn Unicode übergeben wird, kommt Unicode zurück:

    >>> split_group_id(u'group_f6350ab731c3601e925eac482206bda5_Author')
    {'role': u'Author', 'uid': u'f6350ab731c3601e925eac482206bda5'}

    Es wird genau auf Plausibilität geprüft und ggf. ein Dict. mit
    None-Werten zurückgegeben.

    Falsche Zeichen in der UID:
    >>> split_group_id('group_FOOBARBAZ1c3601e925eac482206bda5_Author')
    {'role': None, 'uid': None}

    Unbekanntes oder leeres Suffix:
    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_')
    {'role': None, 'uid': None}
    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_Foo')
    {'role': None, 'uid': None}

    Falsche Länge der UID:
    >>> split_group_id('group_f6350ab731c3601c482206bda5_Author')
    {'role': None, 'uid': None}

    Falsches Präfix:
    >>> split_group_id('gröup_f6350ab731c3601e925eac482206bda5_learner')
    {'role': None, 'uid': None}
    >>> split_group_id(u'gröup_f6350ab731c3601e925eac482206bda5_learner')
    {'role': None, 'uid': None}
    """
    liz = gid.split('_', 2)
    res = dict(SIMPLE_GROUP_INFO)

    if not liz[2:]:
        return res
    elif liz[0] != 'group':
        return res
    elif liz[2] not in ALL_GROUP_SUFFIXES:
        return res
    uid = liz[1]
    if not uid:
        return res
    elif set(uid).difference(UID_CHARS):
        return res
    elif len(uid) != 32:
        return res
    res['uid'] = uid
    res['role'] = liz[2]
    return res

def learner_group_id(uid):
    """
    Gib die ID der Lerngruppe für den Kurs mit der übergebenen UID zurück.

    >>> learner_group_id('f6350ab731c3601e925eac482206bda5')
    'group_f6350ab731c3601e925eac482206bda5_learner'
    """
    return '_'.join(('group', uid, LEARNER_SUFFIX))

def alumni_group_id(uid):
    """
    Gib die ID der Lerngruppe für den Kurs mit der übergebenen UID zurück.

    >>> alumni_group_id('f6350ab731c3601e925eac482206bda5')
    'group_f6350ab731c3601e925eac482206bda5_alumni'
    """
    return '_'.join(('group', uid, ALUMNI_SUFFIX))

def generic_group_id(uid, role):
    """
    Gib die ID der assoziierten Gruppe zurück, die die Rolle <role> im Kontext
    des Objekts mit der angegebenen <uid> vermitteln soll.

    >>> generic_group_id('f6350ab731c3601e925eac482206bda5', 'Author')
    'group_f6350ab731c3601e925eac482206bda5_Author'
    """
    return '_'.join(('group', uid, role))


def pretty_group_title(id, title, translate=None):
    """
    >>> pretty_group_title('group_f6350ab731c3601e925eac482206bda5_Author',
    ...                    'SuP-Fachbuch Author')
    u'Author group "SuP-Fachbuch"'
    """
    dic = split_group_id(id)
    if dic['role'] is None:
        return None
    liz = safe_decode(title).split()
    role = liz.pop()
    if role != safe_decode(dic['role']):
        return None
    stem = u' '.join(liz)
    if translate is None:
        return PRETTY_MASK[role].format(group=stem)
    return translate(PRETTY_MASK[role]).format(group=stem)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

# vim: ts=8 sts=4 sw=4 si et
