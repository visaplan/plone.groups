# -*- coding: utf-8 -*-

# Unitracc-Tools:
from visaplan.tools.minifuncs import translate_dummy as _

# Andere Browser und Adapter:
from visaplan.plone.breadcrumbs.base import (BaseCrumb,
        DesktopBrowserCrumb,
        register, registered,
        )
from visaplan.plone.breadcrumbs.utils import crumbdict

from visaplan.plone.groups.groupdesktop.crumbs import OK  # ... und anschließend:
desktop_crumbs = registered('group-desktop')


# ---------------------------------------------- [ Crumb-Klassen ... [
class PluralSwitchingDesktopCrumb(DesktopBrowserCrumb):
    """
    Generischer Krümel für Unterseiten des Schreibtischs, die in Abhängigkeit
    davon, ob eine Gruppe aktiv ist, eine Singular- oder Pluralform ausgeben;
    außerdem kann ein Browser angegeben werden.

    Das Label ist entweder eine Singular- oder eine Pluralform; beide werden
    bei Instantiierung angegeben.  Die Singualarform wird verwendet, wenn keine
    Gruppen-ID angegeben ist (dann also "Meine" statt "Unsere").
    """
    def __init__(self, id, label_sing, label_plu, browser=None, parents=[]):
        """
        eingeschobene Argumente:
        - die Beschriftung für Singular (wenn Gruppe *angegeben*)
        - die Beschriftung für Plural (wenn Gruppe *nicht* angegeben)
        - der Browser (optional)
        """
        self.label_sing = label_sing
        self.label_plu = label_plu
        DesktopBrowserCrumb.__init__(self, id,
                                     None,  # kein label: hier eigene Logik
                                     browser, parents)

    def tweak(self, crumbs, hub, info):
        crumbs.append(crumbdict(
            hub['translate'](self.label_plu if info['gid'] is None
                             else self.label_sing),
            self._desktop_subpage_url(info, self._virtual_id)))


class DetectGroupFromThread(BaseCrumb):
    """
    Erzeuge keinen eigenen Krümel, sondern ermittle die Gruppen-ID
    aus der Thread-ID *vor* dem Aufruf der Parents!

    Es wird allerdings der Gruppenschreibtischkrümel sichergestellt
    und der Gruppenforum-Krümel hinter diesen sortiert.
    """
    def __call__(self, crumbs, hub, info):
        # set_trace()
        if info['gid'] is None:
            tid = info['request_var'].get('tid')
            if tid is not None:
                info['gid'] = hub['groupboard'].get_group_id(tid)
        BaseCrumb.__call__(self, crumbs, hub, info)

    def tweak(self, crumbs, hub, info):
        tip = crumbs.pop()  # 'Gruppen-Forum' hier entfernen ...
        desktop_crumbs(crumbs, hub, info, override=True)
        crumbs.append(tip)  # und nach dem Gruppenschreibtisch wieder anfügen
# ---------------------------------------------- ] ... Crumb-Klassen ]


def register_crumbs():
    for tid, label_withgroup, label_nogroup, browser in [
            ('viewBoard',
             _('Groupboard'),
             _('Groupboards'),
             'groupboard',
             ),
            ]:
        register(PluralSwitchingDesktopCrumb(tid,
                                     label_withgroup,
                                     label_nogroup,
                                     browser,
                                     [desktop_crumbs]))
    for tid in ('my-calendar', 'our-calendar'):
        for label_withgroup, label_nogroup, browser in [
                (_('Group calendar'),
                 _('My calendar'),
                 None,
                 ),
                ]:
            register(PluralSwitchingDesktopCrumb(tid,
                                         label_withgroup,
                                         label_nogroup,
                                         browser,
                                         [desktop_crumbs]))

    groupboard_crumb = registered('viewBoard')

    detect_gid_from_tid = DetectGroupFromThread(None, [groupboard_crumb])

    for tid, label in [
            ('newThread',
             _('neues Thema'),
             ),
            ]:
        register(DesktopBrowserCrumb(tid, label,
                                     'groupboard',
                                     [groupboard_crumb]))

    for tid, label in [
            ('replyThread',
             _('Thema ansehen'),
             ),
            ]:
        register(DesktopBrowserCrumb(tid, label,
                                     'groupboard',
                                     [detect_gid_from_tid]))

# -------------------------------------------- [ Initialisierung ... [
register_crumbs()
# -------------------------------------------- ] ... Initialisierung ]

OK = True
