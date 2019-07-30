# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et tw=79

# Unitracc-Tools:
from visaplan.tools.minifuncs import translate_dummy as _

# Andere Browser und Adapter:
from visaplan.plone.breadcrumbs.base import (RootedCrumb, BaseCrumb,
        DesktopBrowserCrumb, ViewCrumb,
        register,
        tellabout_call,
        )
from visaplan.plone.breadcrumbs.utils import (crumbdict,
        delete_last_nonfolderish_basecrumb,
        )
from visaplan.plone.base.typestr import (
        plu2tup, plu2import_label, view2plu,
        )

from visaplan.plone.tools.log import getLogSupport
logger, debug_active, DEBUG = getLogSupport(defaultFromDevMode=False)

# Debugging:
from visaplan.tools.debug import pp
from pdb import set_trace


# ---------------------------------------------- [ Crumb-Klassen ... [
class DesktopCrumbs(BaseCrumb):
    """
    Krümel für den persönlichen und ggf. den Gruppenschreibtisch.

    Die Schreibtische werden erzeugt:
    - unter dem Schreibtischordner (derzeit anhand seiner UID identifiziert)
    - für den 'temp'-Ordner (dto.), durch BaseParentsCrumbs
    - für die eigenen Inhalte
    """
    @tellabout_call #(2)
    def tweak(self, crumbs, hub, info, override):
        # override: Schreibtischerkennung übersteuern
        if crumbs[1:] and not override:
            # pp('%(self)r: skip?' % locals(), ('crumbs:', crumbs), ('override:', override))
            if info['skip_desktop_crumbs']:
                return
            info['skip_desktop_crumbs'] = True
            # return
        if not info['personal_desktop_done']:
            delete_last_nonfolderish_basecrumb(info, crumbs)
            # Schreibtisch nur einmal erzeugen:
            crumbs.append(
                    crumbdict(hub['translate']('myUNITRACC'),
                              info['desktop_url']))
            # die die Gruppenangabe auswerten und ggf. in die Sitzungsdaten
            # schreiben:
            info['personal_desktop_done'] = True
        if not info['group_desktop_done']:
            # Gruppenschreibtisch:
            if info['gid'] is not None:
                crumbs.append(
                    crumbdict(info['group_title'],
                              '%(desktop_url)s?gid=%(gid)s'
                              % info))
            info['group_desktop_done'] = True

    def __call__(self, crumbs, hub, info, override=None):
        for parent in self.parents:
            parent(crumbs, hub, info)
        self.tweak(crumbs, hub, info, override)


class DesktopSubCrumb(RootedCrumb):
    """
    Generischer Krümel für auf dem Schreibtisch angesiedelte virtuelle Seiten
    """
    @tellabout_call #(2)
    def tweak(self, crumbs, hub, info):
        crumbs.append(crumbdict(
            hub['translate'](self._raw_label),
            self._desktop_subpage_url(info, self.id)))


class GroupDesktopSubCrumb(DesktopSubCrumb):
    """
    Generischer Krümel für nur auf einem *Gruppen*schreibtisch angesiedelte
    virtuelle Seiten
    """
    @tellabout_call #(2)
    def tweak(self, crumbs, hub, info):
        if info['gid'] is not None:
            crumbs.append(crumbdict(
                hub['translate'](self._raw_label),
                self._desktop_subpage_url(info, self.id)))


class DesktopSubpageCrumb(BaseCrumb):
    """
    Generischer Krümel für echte Unterseiten (-objekte) des Schreibtischs.

    Das Label ist der Titel des Kontexts.
    """
    @tellabout_call #(2)
    def tweak(self, crumbs, hub, info):
        crumbs.append(crumbdict(
            info['context_title'],
            self._desktop_subpage_url(info, self.id)))


class ImportCrumb(BaseCrumb):
    """
    Brotkrümel für Importformulare;
    als Elternelement wird die passende PluralSwitchingThingiesCrumb-Funktion übergeben
    """
    def __init__(self, id, parents=[]):
        tmp = id.split('-', 1)
        if tmp[0] not in ('import',) or not tmp[1:]:
            raise ValueError('Invalid ID for ImportCrumb!'
                             ' (%(id)r)'
                             % locals())
        BaseCrumb.__init__(self, id, parents)
        return  # als Text einfach "Importieren"; das folgende daher
                # deaktiviert:
        plu = tmp[1]
        self._raw_label = plu2import_label[plu]

    @tellabout_call #(2)
    def tweak(self, crumbs, hub, info):
        crumbs.append(crumbdict(
            hub['translate']('Import'),
            self._desktop_subpage_url(info, self.id)))


class PluralSwitchingThingiesCrumb(BaseCrumb):
    """
    Brotkrümel, die je nachdem, ob eine Gruppen-ID aktiv ist,
    unterschiedliche Eltern generieren.

    Es ist unerheblich, ob eine Seite als (beispielsweise) "my-images" oder
    "our-images" aufgerufen wird; der generierte Krümel hängt davon ab, ob im
    Request eine Gruppe vorhanden ist.
    """

    def __init__(self, id, parents, tup):
        """
        Hier keine Parent-Angabe vorgesehen - das wäre der Gruppen- oder
        persönliche Schreibtisch, der von BaseParentsCrumbs erzeugt wird -,
        sondern stattdessen das (mine, our)(title, name)-Tupel
        """
        tmp = id.split('-', 1)
        if tmp[0] in ('my', 'our') or tmp[1:]:
            raise ValueError('Invalid ID for PluralSwitchingThingiesCrumb!'
                             ' (%(id)r)'
                             % locals())
        BaseCrumb.__init__(self, id, parents)
        self._tup = tup

    @tellabout_call
    def tweak(self, crumbs, hub, info):
        if not info['personal_desktop_done']:
            return
        try:
            has_group = info['gid'] is not None
            tup = self._tup[has_group]
            crumbs.append(crumbdict(
                hub['translate'](tup[0]),
                self._desktop_subpage_url(info, tup[1])))

        except KeyError as e:
            logger.error('Fehler in %s', self)
            logger.exception(e)
# ---------------------------------------------- ] ... Crumb-Klassen ]


# -------------------------------------------- [ Initialisierung ... [
def register_crumbs():
    desktop_crumbs = register(DesktopCrumbs('group-desktop'))

    psc = {}
    for plu, tup in plu2tup.items():
        func = PluralSwitchingThingiesCrumb(plu, [desktop_crumbs], tup)
        psc[plu] = func
        for whose in ('my', 'our'):
            key = '-'.join((whose, plu))
            register(func, key)
        register(ImportCrumb('-'.join(('import', plu)),
                             parents=[func]))
    # siehe auch generic_view_crumb:
    for view, plu in view2plu.items():
        register(ViewCrumb(view, parents=[psc[plu]]))

    register(DesktopSubpageCrumb('redeem_tan',
                                 [desktop_crumbs]))

    group_admin_crumb = GroupDesktopSubCrumb('group_administration_view',
                                             _('Group administration'))
    register(group_admin_crumb)
    for tid, label in [
            ('group_administration_learning_progress_view',
             _('Learning progress overview'),
             ),
            ('group_administration_user_view',
             # _('Members'),  ## (leider als 'Benutzer' übersetzt)
             _('Manage group memberships'),
             ),
            ]:
        register(GroupDesktopSubCrumb(tid, label,
                                      parents=[group_admin_crumb]))

register_crumbs()
# -------------------------------------------- ] ... Initialisierung ]

OK = True
