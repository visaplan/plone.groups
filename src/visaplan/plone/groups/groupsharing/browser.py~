# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
"""
Browser groupsharing

Refactoring der SQL-Tabelle unitracc_groupmemberships:
    - Spalte courseuid umbenannt nach group_id_
    - Spalte groupuid umbenannt nach member_id_
"""
# Zope/Plone:
from AccessControl import Unauthorized
from visaplan.plone.base import BrowserView, implements, Interface
from Products.PluggableAuthService.interfaces.plugins import IGroupEnumerationPlugin
from Globals import DevelopmentMode
from Products.CMFCore.utils import getToolByName
from zope.site.hooks import getSite
import transaction

# Standardmodule:
from datetime import datetime, date, timedelta
from time import localtime, time
from collections import defaultdict

# Unitracc:
from visaplan.plone.base.permissions import (ManageGroups, ViewGroups,
        ManageUsers, ManageCourses,
        )

# installierte Module:
from psycopg2._psycopg import IntegrityError, InterfaceError, InternalError

# Unitracc-Tools:
from visaplan.tools.minifuncs import makeBool
from visaplan.tools.coding import safe_decode
from visaplan.tools.lands0 import list_of_strings
from visaplan.plone.tools.forms import (tryagain_url, detect_duplicates,
        back_to_referer,
        )
from visaplan.plone.tools.context import message
from visaplan.plone.tools.context import getbrain
from visaplan.tools.classes import Proxy
from visaplan.tools.profile import StopWatch
from visaplan.tools.dates import make_date_formatter

# Andere Browser:
from visaplan.plone.groups.unitraccgroups.utils import (split_group_id,
        ALL_GROUP_SUFFIXES, LEARNER_SUFFIX, pretty_group_title,
        ALUMNI_SUFFIX,
        )

# Dieser Browser:
from .utils import (makedate, datefromform,
        make_keyfunction, gettitle, getgrouptitle, getcoursetitle,
        build_groups_set, recursive_members, journal_text,
        make_break_at_row,
        default_dates_dict,
        )

# Logging und Debugging:
from visaplan.plone.tools.log import getLogSupport
logger, debug_active, DEBUG = getLogSupport(defaultFromDevMode=False)
from visaplan.tools.debug import log_or_trace, pp
from pprint import pformat
sw_kwargs = {'enable': bool(debug_active),
             }

if debug_active:
    def DBG_P(txt, *args):  # DEBUG
        from time import strftime
        if args:
            print '*** @@groupsharing', strftime('%H:%M:%S'), txt % args
        else:
            print '*** @@groupsharing', strftime('%H:%M:%S'), txt
else:
    def DBG_P(txt, *args):
        pass


# Allerweltsgruppe, der jeder nicht-anonyme User angehoert,
# daher uninteressant:
BORING_GROUPS = set(['AuthenticatedUsers'])
try:
    from Products.zkb.config import MORE_BORING_GROUPS
    BORING_GROUPS.update(MORE_BORING_GROUPS)
except:
    pass
# siehe auch @@groupdesktop.STATIC_GROUPS_BLACKLIST, ...ANONYMOUS_GROUPS

ANCIENT_PAST = makedate('31.12.1999')
USE_ZOPE_METHODS = 0
SECS_PER_DAY = 24 * 3600
ALUMNI_CUT = - (len(ALUMNI_SUFFIX) + 1)  # zum Abschneiden


class IGroupSharing(Interface):

    def canManage(self):
        """
        Darf der angemeldete Benutzer diese Gruppe bzw., wenn keine angegeben:
        alle Gruppen bearbeiten?
        """

    def authManage(self):
        """
        Wirft ggf. Unauthorized
        """

    def get_group_info_by_id(self, group_id, pretty=0, getObject=0):
        """
        Gib ein Dict. zurück;
        - immer vorhandene Schlüssel: id, group_title, group_description
        - nur bei automatisch erzeugten Gruppen: role, role_translation, brain
        """

    def get_groups_by_user_id(self, user_id, explicit=True, askdb=None):
        """
        Gib eine sortierte Liste von Gruppen-Info-Dictionarys zurück.
        """

    def get_user_and_all_groups(self, uogid):
        """
        Ermittle die IDs aller Gruppen, denen der übergebene User (oder die
        Gruppe -- uogid) angehört - abzgl. der üblichen Ausnahme
        'AuthenticatedUsers'.
        Gib ein 2-Tupel zurück:

        (user_id, set(group_ids))

        Wenn die übergebene ID <uogid> zu einem User gehört, wird sie aus dem
        Set der Gruppen-IDs entfernt und im ersten Teil des Tupels
        zurückgegeben; ansonsten ist dieser erste Teil None.
        """

    def delete_group_membership_by_group_id(self):
        """
        Aufgerufen aus manage_group_view;
        die Gruppenzuordnungen sollen hier *tatsächlich*
        spurlos beseitigt werden! (Aufräumfunktion)

        Formularfelder:
        ids -- eine Liste von Member-IDs
        group_id -- die aufzuräumende Gruppe
        """

    def add_group_membership(self):
        """
        Füge *einen* Benutzer (oder eine Gruppe)
        einer oder mehreren Gruppen hinzu

        Startdatum ist heute;
        ein Endedatum wird nicht gesetzt.

        Siehe auch --> add_to_group (mehrere Benutzer, eine Gruppe,
        variable Datumswerte)
        """

    def end_group_memberships(self):
        """
        *Beende* Gruppenmitgliedschaften (ohne sie spurlos zu entfernen)
        """

    def delete_group_memberships(self):
        """
        Zum Aufruf aus Formularen: *Entferne* Gruppenmitgliedschaften
        (und lösche sie aus der relationalen Datenbank)
        """

    def search_groups(self, string_='', sort_=True):
        """ """

    def get_explicit_group_memberships(self, group_id):
        """
        gib die Benutzer und Gruppen zurück, die direkte Mitglieder
        der übergebenen Gruppe sind
        """

    def search_groups_and_users(self, string_=''):
        """ """

    def add_to_group(self):
        """
        Füge Benutzer und/oder Gruppen einer Gruppe hinzu.
        Formulardaten:

        Formular   | Feldname   | Erklärung
        -----------+------------+----------------------------------------
        group_id   | group_id_  | ursprünglich ging es nur um Kursgruppen
        ids:list   | member_id_ | ursprünglich "(Schul-) Klassen", jetzt
                   |            | allgemein Benutzer- oder Gruppen-IDs
        start_<id> | start      | Startdatum, d.m.yyyy, default: heute
        end_<id>   | ends       | Ablaufdatum, d.m.yyyy, default: leer
        """

    def delete_groups(self):
        """ """

    def update_group(self):
        """ """

    def can_view_unitracc_groups(self):
        """
        für Schema: regelt den Zugriff auf das Gruppenfreigabe-Widget
        """

    def get_permission_authors(self):
        """ """

    def get_custom_search_authors(self):
        """ """

    def get_group_memberships(self, group_id, explicit=True):
        """
        Gib alle Gruppen zurück, deren direktes Mitglied die
        übergebene Gruppe ist
        (ACHTUNG, Argument 'explicit' wird bisher nicht berücksichtigt!)
        """

    def connect_groups(self):
        """ Verbindet manuell erstellte Gruppen mit automatisch erstellten Kursgruppen. """

    def disconnect_groups(self):
        """
        Trennt manuell erstellte Gruppen von automatisch erstellten Kursgruppen.
        """

    def scheduled_group_memberships(self):
        """
        Arbeite die Gruppenzuordnungen ab gemäß der Tabelle
        unitracc_groupmemberships (neuer cron-Job).
        """

    def update_view_duration(self):
        """ Aktualisiert die eingetragenen Daten für die Gruppenzugehörigkeitsdauer """

    def replay_groups(self):
        """
        Gruppenzuordnungen "nachholen".  Da die Formulardaten Datumswerte
        enthalten können, darf das nur von einem Admin gemacht werden.
        """

    def get_course_info_for_group_ids(self, group_ids):
        """ """

    def get_group_manager_for_group_id(self, group_id):
        """ """

    def is_member_of_any(self, group_ids, user_id=None, default=False):
        """
        Ist der übergebene Benutzer Mitglied einer der übergebenen Gruppen?

        - wenn user_id nicht übergeben wird, wird der angemeldete Benutzer
          verwendet
        - wenn die Liste der Gruppen-IDs leer ist, wird der Vorgabewert
          verwendet (default)
        """

PRETTY_MASK = {}
for role in ALL_GROUP_SUFFIXES:
    PRETTY_MASK[role] = u'%s group "{group}"' % role
if 0 and 'nur fuer den Parser':
    _('Author group "{group}"')
    _('Reader group "{group}"')
    _('learner group "{group}"')
    _('alumni group "{group}"')


class Browser(BrowserView):

    implements(IGroupSharing)

    config_storage_key = 'groupsharing'

    def canManage(self):
        return self._canManage()

    def _canManage(self, groupinfo=None):
        """
        Darf der aktuell angemeldete Benutzer die Gruppe bearbeiten?
        """
        context = self.context
        checkperm = getToolByName(context, 'portal_membership').checkPermission

        for perm in ('Manage portal',
                     ManageGroups,
                     ):
            if checkperm(perm, context):
                return True

        if groupinfo is None:
            form = context.REQUEST.form
            gid = None
            for varname in ('group_id',
                            'gid',
                            ):
                gid = form.get(varname) or None
                if gid is not None:
                    break
            if gid is None:
                return False

            ggibi = groupinfo_factory(context)
            groupinfo = ggibi(gid)

        member = getToolByName(context, 'portal_membership').getAuthenticatedMember()
        member_id = member.getId()
        try:
            return groupinfo['group_manager'] == member_id
        except KeyError:
            return False

    def authManage(self):
        return self._authManage()

    def _authManage(self, groupinfo=None):
        if not self._canManage(groupinfo):
            raise Unauthorized

    # @trace_this
    def get_group_info_by_id(self, group_id, pretty=0, getObject=0):
        """
        Gib ein Dict. zurück;
        - immer vorhandene Schlüssel: id, group_title, group_description
        - nur bei automatisch erzeugten Gruppen: role, role_translation, brain

        Argumente:
        group_id -- ein String, normalerweise mit 'group_' beginnend
        pretty -- wenn True, wird ein Schlüssel 'pretty_title' erzeugt, der
                  den Gruppentitel ohne das Rollensuffix enthält.
        getObject -- wenn True, wird das Gruppenobjekt als 'group_object'
                     mitgeliefert (bisher in keiner groupinfo_factory-Variante
                     enthalten).

        Insbesondere, wenn für viele Gruppen Informationen benötigt werden
        (z.B. für Auswahllisten), empfiehlt sich alternativ die Verwendung der
        Factory-Funktion groupinfo_factory:

          getinfo = groupinfo_factory(self.context)
          for group_id in ...:
              dict_ = getinfo(group_id)
              ...
        """

        context = self.context
        pg = getToolByName(context, 'portal_groups')
        getAdapter = context.getAdapter
        group = pg.getGroupById(group_id)
        acl = getToolByName(context, 'acl_users')

        dict_ = {'id': group_id}
        try:
            thegroup = acl.source_groups._groups[group_id]
            dict_['group_title'] = thegroup['title']
        except KeyError:
            return {}
        if getObject:
            dict_['group_object'] = thegroup
        dict_['group_description'] = thegroup['description']
        dict_['group_manager'] = thegroup.get('group_manager')
        dict_['group_desktop'] = thegroup.get('group_desktop')

        # Hier die Berechtigung prüfen:
        ### XXX Wozu?! Reine Ausgabemethode!
        ###     (und macht Probleme mit @@tan._redeem2)
        # self._authManage(dict_)

        dic = split_group_id(group_id)
        if dic['role'] is not None:
            dict_.update(dic)
        else:
            if pretty:
                translate = getAdapter('translate')
                dict_['pretty_title'] = translate(dict_['group_title'])
            return dict_

        translate = getAdapter('translate')

        if dic['role'] is None:
            dict_['role_translation'] = None
        else:
            dict_['role_translation'] = translate(dic['role'])
        dict_['brain'] = getbrain(context, dic['uid'])
        if pretty:
            liz = dict_['group_title'].split()
            if liz and liz[-1] == dict_['role']:
                stem = ' '.join(liz[:-1])
                dict_['pretty_title'] = translate(PRETTY_MASK[dict_['role']]).format(group=stem)
            else:
                dict_['pretty_title'] = translate(dict_['group_title'])

        return dict_

    #@print_call_and_result_length
    #@print_call_and_result
    def get_groups_by_user_id(self, user_id, explicit=True, askdb=None,
                              pretty=None):
        """
        Gib eine sortierte Liste von Gruppen-Info-Dictionarys zurück.

        user_id -- Nutzer-ID
        explicit -- wenn True (default), nur die direkten
                    Gruppenmitgliedschaften zurückgeben
        askdb -- auch inaktive Gruppenmitgliedschaften ermitteln
                 (aus der SQL-Datenbank);
                 zusätzliche Schlüssel: active, start_date, end_date

        Schlüssel der Dictionarys:
        id, group_title, group_description (immer vorhanden;
                                           das letztere oft leer);
        brain, uid: ggf. das Referenzobjekt (Strukturelement oder Kurs);
        role: (Pseudo-) Rolle gemäß Gruppen-ID
        role_translation: übersetzte Version
        """

        context = self.context

        #Remove dummy group
        group_ids = self._get_filtered_groups(user_id)
        list_ = []
        ggibi = groupinfo_factory(self.context, pretty=pretty)
        if explicit:
            is_direct_member_of = is_direct_member__factory(context, user_id)
            for group_id in group_ids:
                if is_direct_member_of(group_id):
                    list_.append(ggibi(group_id))
            if askdb:
                # Gruppen-IDs lt. Zope sind definitiv:
                zope_gids = set([dic['id']
                                 for dic in list_])
                fields = ['group_id_',
                          'start', 'ends',
                          'active', 'done',
                          ]
                for dic in list_:
                    dic['active'] = True
                # today = date.today()
                with context.getAdapter('sqlwrapper') as sql:
                    query_data = {'member_id_': user_id,
                                  # 'active': False,
                                  }
                    # Informationen aus Datenbank auslesen:
                    result = sql.select('unitracc_groupmemberships',
                                        fields,
                                        query_data=query_data)
                    active_in_db = set([dic['group_id_']
                                        for dic in result
                                        if dic['active']
                                        ])
                    db_gids = set([dic['group_id_']
                                   for dic in result])
                    # speichern in Struktur, für von Zope gefundene
                    # Mitgliedschaften:
                    db_membership_info = defaultdict(default_dates_dict)
                    format_date = make_date_formatter()
                    for dic in result:
                        member_id = dic['group_id_']
                        db_membership_info[member_id] = {
                                'start_date': format_date(dic['start']),
                                'end_date': format_date(dic['ends']),
                                }

                    # Fehlende Gruppenzuordnungen in DB schreiben:
                    missing_in_db = zope_gids.difference(db_gids)
                    for gid in missing_in_db:
                        tmp = \
                        sql.insert('unitracc_groupmemberships',
                                   {'member_id_': user_id,
                                    'group_id_': gid,
                                    'active': True,
                                    # 'start': ANCIENT_PAST,
                                    },
                                   returning=fields)
                        ## Zope ist definitiv; also Datenbank-Zustand fixen!
                        # Aktiv in Zope, inaktiv in Datenbank:
                    inactive_in_db = db_gids.difference(active_in_db)
                    activate_in_db = inactive_in_db.intersection(zope_gids)
                    if activate_in_db:
                        query_data['group_id_'] = sorted(activate_in_db)
                        sql.update('unitracc_groupmemberships',
                                   {'active': True,
                                    },
                                   query_data=query_data)

                    missing_in_zope = active_in_db.difference(zope_gids)
                    if missing_in_zope:
                        query_data['group_id_'] = sorted(missing_in_zope)
                        sql.update('unitracc_groupmemberships',
                                   {'active': False,
                                    },
                                   query_data=query_data)
                    # Inaktive Zuordnungen dem Ergebnis zufügen:
                    for group_id in db_gids.difference(zope_gids):
                        dic = ggibi(group_id) \
                                or {'id': group_id,
                                    'group_title': '%s (unknown or deleted)'
                                                   % group_id,
                                    }
                        dic['active'] = False
                        list_.append(dic)
                    # Datumsinformationen ergänzen:
                    for dic in list_:
                        group_id = dic['id']
                        dic.update(db_membership_info[group_id])
        else:
            for group_id in group_ids:
                list_.append(ggibi(group_id))
        list_.sort(key=getgrouptitle)
        return list_

    def get_group_memberships(self, group_id, explicit=True):
        """
        Gib alle Gruppen zurück, deren direktes Mitglied die
        übergebene Gruppe ist
        (ACHTUNG, Argument 'explicit' wird bisher nicht berücksichtigt!)
        """

        context = self.context
        ## evtl. wieder aktivieren für Gruppen-ID aus *Request*;
        ## @@tan.selectable_groups braucht eine Auskunft für *Nicht*-Manager:
        # context.getBrowser('authorized').managePortal()
        is_direct_member_of = is_direct_member__factory(context, group_id)

        list_ = []
        for id in self._get_all_group_ids():
            if is_direct_member_of(id):
                list_.append(self.get_group_info_by_id(id))

        list_.sort(key=getgrouptitle)

        return list_

    def _gen_inherited_group_memberships(self, DONE, member_id, limit=10):
        # noch unfertig ...
        if member_id in DONE:
            return

    def _get_all_group_ids(self):
        """
        Gib die IDs *aller* vorhandenen Gruppen zurück
        """
        context = self.context
        acl = getToolByName(context, 'acl_users')

        group_ids = list(acl.source_groups._groups)
        if 'AuthenticatedUsers' in group_ids:
            group_ids.remove('AuthenticatedUsers')
        return group_ids

    def get_all_group_ids(self):
        """
        Gib die IDs *aller* vorhandenen Gruppen zurück,
        bis auf die langweiligen.

        Gibt ein Set zurück; daher wurde die vorhandene Methode
        _get_all_group_ids nicht einfach ersetzt.
        """
        context = self.context
        acl = getToolByName(context, 'acl_users')

        group_ids = set(acl.source_groups._groups)
        group_ids.difference_update(BORING_GROUPS)
        return group_ids

    def get_all_groups(self, pretty=False):
        """
        Gib Gruppeninformationen von allen Gruppen zurück,
        bis auf die langweiligen.
        """
        ggibi = groupinfo_factory(self.context, pretty)
        return sorted([ggibi(gid)
                       for gid in self.get_all_group_ids()
                       ],
                      key=getgrouptitle)

    def _get_filtered_groups(self, id):
        """
        Gib die IDs aller Gruppen zurueck, denen der User mit der uebergebenen ID
        angehoert, abzgl. der Gruppe 'AuthenticatedUsers'.

        Wenn kein entsprechender User gefunden wird, wird eine Gruppe
        gesucht.
        """
        context = self.context
        acl = getToolByName(context, 'acl_users')
        user = acl.getUser(id)
        group_ids = set()
        if user:
            group_ids = set(user.getGroups())
        else:
            pg = getToolByName(context, 'portal_groups')
            group = pg.getGroupById(id)
            if group:
                group_ids = set(group.getGroups())

        rslt = sorted(group_ids.difference(BORING_GROUPS))
        DBG_P('_get_filtered_groups(%r) --> %s', id, rslt)    # DEBUG
        return rslt

    def get_user_and_all_groups(self, uogid):
        """
        Ermittle die IDs aller Gruppen, denen der übergebene User (oder die
        Gruppe -- uogid) angehört - abzgl. der üblichen Ausnahme
        'AuthenticatedUsers'.
        Gib ein 2-Tupel zurück:

        (user_id, set(group_ids))

        Wenn die übergebene ID <uogid> zu einem User gehört, wird sie aus dem
        Set der Gruppen-IDs entfernt und im ersten Teil des Tupels
        zurückgegeben; ansonsten ist dieser erste Teil None.
        """
        global USE_ZOPE_METHODS
        with StopWatch('@@gs.guaag(%r): USE_ZOPE_METHODS=%r'
                       % (uogid, USE_ZOPE_METHODS),
                       **sw_kwargs) as stopwatch:
            context = self.context
            acl = getToolByName(context, 'acl_users')
            if USE_ZOPE_METHODS:
                uogo = acl.getUser(uogid)  # "user or group object"
                if uogo is None:
                    uogo = acl.getGroup(uogid)
                group_ids = acl.source_groups.getGroupsForPrincipal(uogo)
                is_user = uogid not in acl.source_groups._group_principal_map
                gcount = len(group_ids)
                if is_user:
                    return (uogid, group_ids)
                else:
                    return (None, group_ids)
            else:
                gpm = acl.source_groups._group_principal_map
                group_ids = build_groups_set(gpm, uogid)
                group_ids.difference_update(BORING_GROUPS)
                gcount = len(group_ids)
                if uogid not in gpm:
                    group_ids.discard(uogid)
                    return (uogid, group_ids)
                else:
                    return (None, group_ids)

    def get_all_groups_including_user(self, uogid):
        """
        Ermittle die IDs aller Gruppen, denen der übergebene User (oder die
        Gruppe -- uogid) angehört - abzgl. der üblichen Ausnahme
        'AuthenticatedUsers'.

        Unterschied zu get_user_and_all_groups:
        Wenn die übergebene <uogid> einen User bezeichnet, wird sie völlig
        schmerzbefreit zwischen den etwaigen Gruppen-IDs zurückgegeben.
        """
        context = self.context
        acl = getToolByName(context, 'acl_users')
        gpm = acl.source_groups._group_principal_map
        group_ids = build_groups_set(gpm, uogid)
        group_ids.difference_update(BORING_GROUPS)
        return group_ids

    def _is_explicit_member(self, string_, group_id):
        """
        Für mehrfache Anwendung:
        stattdessen Factory-Funktion is_direct_member__factory verwenden!
        (siehe unten)
        """
        context = self.context
        acl = getToolByName(context, 'acl_users')
        #string_ can be user_id or group_id
        return string_ in acl.source_groups._group_principal_map[group_id]

    # @print_call_and_result
    # @trace_this
    def get_explicit_group_memberships(self, group_id):
        """
        gib die Benutzer und Gruppen zurück, die direkte Mitglieder
        der übergebenen Gruppe sind

        Die Elemente der Sequenz sind dict-Objekte mit folgenden
        Schlüsseln:
        - id
        - type
        - title
        - role_translation
        - start
        - ends
        - active
        - ismember_zope
        """
        with StopWatch('@@gs.gegm(%r)',
                       mapping=(group_id,),
                       **sw_kwargs) as stopwatch:
            context = self.context
            getBrowser = context.getBrowser
            getAdapter = context.getAdapter

            getBrowser('authorized').raiseAnon()

            acl = getToolByName(context, 'acl_users')
            author = getBrowser('author')
            ggibi = groupinfo_factory(self.context)
            group = ggibi(group_id)
            pg = getToolByName(context, 'portal_groups')
            list_ = []
            # OOSet hat keine difference-Methode:
            try:
                members_zope = set(acl.source_groups._group_principal_map[group_id])
                DBG_P('members_zope = %s', members_zope)
            except KeyError:
                message(context,
                        'Group ${group_id} not found!',
                        'error',
                        mapping=locals())
                return []
            members = sorted(members_zope)
            logger.info('gegm: Mitglieder der Gruppe %s', group_id)
            logger.info('gegm: lt. Zope, vorher: %s', members)

            gmibi = memberinfo_factory(context, pretty=0, bloated=2)
            try:
                with getAdapter('sqlwrapper') as sql:
                    table = "unitracc_groupmemberships"
                    fields = ['member_id_',
                              'start', 'ends', 'active',
                              ]
                    # where = "WHERE group_id_=%(group_id_)s"
                    stopwatch.lap('Vorbereitungen')
                    rows = sql.select(table,
                                      # where=where,
                                      fields=fields,
                                      query_data={'group_id_': group_id})
                    stopwatch.lap('SQL-Abfrage')
                    members_sql = set([dic['member_id_']
                                       for dic in rows
                                       ])
                    logger.info('gegm: lt. SQL, vorher:  %s',
                                sorted(members_sql))

                    if debug_active:
                        pp([('members_sql:', sorted(members_sql)),
                            ('Enrico enthalten:', 'Enrico' in members_sql),
                            ('members_zope:', sorted(members_zope)),
                            ('Enrico enthalten:', 'Enrico' in members_zope),
                            ])
                    missing_in_db = members_zope.difference(members_sql)
                    if debug_active:
                        pp(missing_in_db=sorted(missing_in_db))
                    logger.info('gegm, "missing_in_db": %s',
                                sorted(missing_in_db))
                    active_in_db = set([dic['member_id_']
                                        for dic in rows
                                        if dic['active']
                                        ])
                    # füge der SQL-Tabelle alle fehlenden Einträge hinzu:
                    stopwatch.lap('Vor den SQL-Inserts')
                    temp_ = []
                    for member_id in missing_in_db:
                        data = {'member_id_': member_id,
                                'group_id_': group_id,
                                'active': True,
                                }
                        logger.info('gegm, sql: inserting %(member_id_)s'
                                     ' into %(group_id_)s',
                                     data)
                        temp_.extend(sql.insert(table,
                                                data,
                                                returning=fields))
                    stopwatch.lap('Nach den SQL-Inserts (%d)' % len(missing_in_db))
                    temp_.extend(rows)
                    acl_gu = acl.getUser
                    gbbuid = author.getBrainByUserId
                    if 0:
                        pp((('members_zope:', members_zope),
                            ('members_sql:', members_sql),
                            ('missing_in_db:', missing_in_db),
                            ))
                    # über alle (alten und neuen) Datensätze iterieren:
                    # (Schlüssel: member_id_, start, ends, active)
                    zombie_ids = []
                    for dict_ in temp_:
                        id = dict_['member_id_']
                        try:
                            info = gmibi(id)
                        except KeyError:
                            print '*' * 79
                            print '(Gruppen- oder Benutzer-) Id:', id
                            print '*' * 79
                            raise
                        else:
                            if (info is None
                                or info['type'] is None  # bloated >= 2
                                ):
                                zombie_ids.append(id)
                                logger.warn('User or group %(id)r not found',
                                            locals())
                                continue
                            info.update(dict_)
                            info['ismember_zope'] = id in members_zope
                            info['brain'] = gbbuid(id)
                            for a in ('start', 'ends'):
                                d = info[a]
                                if d is not None:
                                    info[a] = d.strftime('%d.%m.%Y')
                            list_.append(info)

            except InternalError as e:
                logger.error("Can't update the SQL data")
                logger.exception(e)
                # info['ismember_zope'] = True ist hier zuverlässig -
                # schließlich ist Zope die einzige verwendete Quelle
                list_[:] = [gmibi(id)
                            for id in members
                            ]

            list_.sort(key=gettitle)
            DBG_P('get_explicit_group_memberships(%(group_id)r) -> %(list_)s'
                  % locals())

            return list_

    def get_inherited_group_memberships_by_group_id(self, group_id):

        context = self.context
        ### Managerrechte-Erfordernis absichtlich entfernt!
        ### Wenn wider Erwarten doch notwendig, muß insbesondere der
        ### Gruppenschreibtisch für Nicht-Manager sorgfältig getestet werden!
        ## context.getBrowser('authorized').managePortal()

        list_ = []
        for group_id in self._get_filtered_groups(group_id):
            list_.append(self.get_group_info_by_id(group_id))

        list_.sort(key=getgrouptitle)

        return list_

    def get_courses_and_desktop_groups(self, user_id, gid=None):
        """
        Gib zwei Listen zurück (courses, desktops1):
        - die Kurse mit den schreibtischrelevanten Gruppen
        - die Gruppen, für die Schreibtische existieren
        """  # ----------------------------------------- [ gcadg ... [
        context = self.context
        getAdapter = context.getAdapter
        with StopWatch('@@gs.gcadg', **sw_kwargs) as stopwatch:
            is_direct_member_of = is_direct_member__factory(context, user_id)
            # Verwendung der Gruppeninfo sowohl für Kurse als auch für
            # Schreibtische; teure Berechnung puffern:
            group_info = Proxy(groupinfo_factory(context,
                                                 pretty=1,
                                                 forlist=0))

            courses = []
            alumni_gids = []  # Alumni-Gruppen
            desktops1 = []
            acl = getToolByName(context, 'acl_users')
            user = acl.getUser(user_id)
            if not user:
                return courses, desktops1

            desktops2 = []
            all_groups_of_user = set(user.getGroups())
            get_mapping_group = get_group_mapping_course__factory(
                    context,
                    group_ids=all_groups_of_user,
                    group_info=group_info)
            stopwatch.lap('Vorbereitungen')
            # ------------------- [ gcadg: Kursgruppen ... [
            if gid is None:
                # persönlicher Schreibtisch - Kursgruppen ungefiltert
                for group_id in all_groups_of_user:
                    if group_id in BORING_GROUPS:
                        continue
                    # dic wird auch für ungefilterte Kurse verwendet:
                    dic = group_info[group_id]
                    if is_direct_member_of(group_id):
                        if dic['group_desktop']:
                            desktops1.append(dic)
                        elif dic['group_manager'] == user_id:
                            desktops2.append(dic)
                        elif id == gid:
                            desktops2.append(dic)
                    role = dic.get('role')
                    if role == LEARNER_SUFFIX:
                        courses.append(get_mapping_group(group_id))
                    elif role == ALUMNI_SUFFIX:
                        alumni_gids.append(group_id)
                stopwatch.lap('Alle Kurse des Users')
            else:
                # Gruppenschreibtisch - nur Kurse über die aktuelle Gruppe
                for group_id in all_groups_of_user:
                    if group_id in BORING_GROUPS:
                        continue
                    if is_direct_member_of(group_id):
                        dic = group_info[group_id]
                        if dic['group_desktop']:
                            desktops1.append(dic)
                        elif dic['group_manager'] == user_id:
                            desktops2.append(dic)
                        elif id == gid:
                            desktops2.append(dic)

                pg = getToolByName(context, 'portal_groups')
                group = pg.getGroupById(gid)
                if group:
                    all_groups_of_group = set(group.getGroups())
                else:
                    all_groups_of_group = set()

                for group_id in all_groups_of_group:
                    if group_id in BORING_GROUPS:
                        continue
                    dic = group_info[group_id]
                    role = dic.get('role')
                    if role == LEARNER_SUFFIX:
                        courses.append(get_mapping_group(group_id))
                    elif role == ALUMNI_SUFFIX:
                        alumni_gids.append(group_id)
                stopwatch.lap('Nur Kurse der Gruppe')

            alumni_uids = set([get_mapping_group(gid)['course_uid']
                               for gid in alumni_gids
                               ])
            # ------------------- ] ... gcadg: Kursgruppen ]

            if debug_active:
                pp(courses=courses, alumni_gids=alumni_gids,
                   alumni_uids=sorted(alumni_uids))
            course_uids = set()
            if courses:
                # wenn Kurse gefunden, Statistiken ermitteln
                for dic in courses:
                    uid = dic.get('course_uid')
                    if uid is not None:
                        course_uids.add(uid)
                # Statistiken sind mit Autoren-UID verknüpft:
                author = context.getBrowser('author').get()
                if author:
                    author_uid = author.UID()
                    query_data = {'user_uid': author_uid,
                                  'course_uid': sorted(course_uids),
                                  }
                    stat_dict = {}
                    with getAdapter('sqlwrapper') as sql:
                        rows = sql.select('course_statistics_overview',
                                          query_data=query_data)
                        for row in rows:
                            course_uid = row['course_uid']
                            stat_dict[course_uid] = row
                    for dic in courses:
                        course_uid = dic['course_uid']
                        dic['stats'] = stat_dict.get(course_uid)
                        dic['coursedocs_link'] = course_uid in alumni_uids
                        dic['currently_booked'] = True
                stopwatch.lap('Kursstatistiken')

            alumni_uids.difference_update(course_uids)
            if alumni_uids:
                # abgelaufene Kursgruppen: separat auflisten
                alumnig = []
                for uid in alumni_uids:
                    dic = get_mapping_group(''.join(('group_', uid, '_', ALUMNI_SUFFIX)))
                    dic['coursedocs_link'] = True
                    dic['currently_booked'] = False
                    alumnig.append(dic)
                if alumnig[1:]:
                    alumnig.sort(key=getcoursetitle)
                courses.extend(alumnig)

            desktops1.sort(key=getgrouptitle)  # Gruppen mit Schreibtisch
            desktops2.sort(key=getgrouptitle)  # von mir administrierte Gruppen
            # bestimmte Gruppen ohne Schreibtisch
            # trotzdem anhängen - aber als letztes:
            desktops1.extend(desktops2)
            return courses, desktops1  # --------------- ] ... gcadg ]

    def get_groups_with_desktops(self, user_id, gid=None):
        """
        Gib die Gruppen zurück, ...
        - für die ein Schreibtisch ausgewählt werden kann
          (Schreibtisch-Flag aktiv; zuerst ausgegeben)
        - die der angegebene Benutzer administriert, oder
        - die aktuell ausgewählt ist (nach den echten Schreibtischgruppen)

        """
        context = self.context
        # context.getBrowser('authorized').managePortal()
        is_direct_member_of = is_direct_member__factory(context, user_id)
        ggibi = groupinfo_factory(context, 1, 0)

        list1 = []
        list2 = []
        for id in self._get_all_group_ids():
            if is_direct_member_of(id):
                dic = ggibi(id)
                if 0 and not list1:
                    pp(dic=dic)
                if dic['group_desktop']:
                    list1.append(dic)
                elif dic['group_manager'] == user_id:
                    list2.append(dic)
                elif id == gid:
                    list2.append(dic)
        list1.sort(key=getgrouptitle)
        list2.sort(key=getgrouptitle)
        # bestimmte Gruppen ohne Schreibtisch
        # trotzdem anhängen - aber als letztes:
        list1.extend(list2)
        return list1

    def get_inherited_group_memberships_by_user_id(self, user_id):
        """
        FUNKTIONIERT NUR FEHLERHAFT
        """
        # @@TODO: BUGFIX IT (TH: Was genau stimmt denn nicht?!)
        # TH 25.1.2016: Manage users/Groups statt Manage portal
        context = self.context

        authorized = context.getBrowser('authorized')
        authorized.raiseAnon()
        DBG_P('get_inherited_group_memberships_by_user_id(user_id=%r)', user_id)

        member = getToolByName(context, 'portal_membership').getAuthenticatedMember()
        my_id = member.getId()
        DBG_P('... my_id = %r', my_id)
        if my_id != user_id:
            checkperm = getToolByName(context, 'portal_membership').checkPermission
            if not (checkperm(ManageUsers, context)
                    or checkperm(ManageGroups, context)
                    ):
                raise Unauthorized

        acl = getToolByName(context, 'acl_users')
        groups = self._get_filtered_groups(user_id)

        list_ = []
        for group_id in list(groups):
            if user_id not in acl.source_groups._group_principal_map[group_id]:
                groups.remove(group_id)
                list_.append(self.get_group_info_by_id(group_id))

        list_.sort(key=getgrouptitle)

        return list_

    def delete_group_membership_by_group_id(self):
        """
        Aufgerufen aus manage_group_view;
        die Gruppenzuordnungen sollen hier *tatsächlich*
        spurlos beseitigt werden! (Aufräumfunktion)

        Formularfelder:
        ids -- eine Liste von Member-IDs
        group_id -- die aufzuräumende Gruppe
        """
        # siehe auch --> end_group_memberships, _end_group_memberships
        context = self.context

        getAdapter = context.getAdapter
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        if not checkperm(ManageGroups, context):
            raise Unauthorized

        groups = context.getBrowser('groups')
        request = context.REQUEST
        form = request.form

        ids = form.get('ids')
        group_id = form.get('group_id')

        group = groups.getById(group_id)
        course = self.get_group_info_by_id(group_id)

        if ids:
            with getAdapter('sqlwrapper') as sql:
                for id in ids:
                    group.removeMember(id)
                    sql.delete("unitracc_groupmemberships",
                               query_data={'member_id_': id,
                                           'group_id_': group_id,
                                           })
            message(context,
                    'Changes saved.')
        else:
            message(context,
                    'Please select an user or a group to remove.')
        return request.RESPONSE.redirect(request['HTTP_REFERER'])

    def add_group_membership(self):
        """
        Füge *einen* Benutzer (oder eine Gruppe)
        einer oder mehreren Gruppen hinzu

        Startdatum ist heute;
        ein Endedatum wird nicht gesetzt.

        Siehe auch --> add_to_group (mehrere Benutzer, eine Gruppe,
        variable Datumswerte)
        """
        context = self.context

        getAdapter = context.getAdapter
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        if not (checkperm(ManageUsers, context) or
                checkperm(ManageGroups, context)
                ):
            raise Unauthorized

        form = context.REQUEST.form

        member_id = form.get('user_id')
        group_ids = form.get('group_ids')

        if member_id and group_ids:
            TODAY = date.today()
            start = TODAY
            ends = None
            with getAdapter("sqlwrapper") as sql:
                for group_id in group_ids:
                    if group_id == member_id:
                        message(context,
                                "Won't add group ${group_id} to itself!",
                                'error',
                                mapping=locals())
                        continue
                    start = datefromform('start_', group_id, form,
                                         default=TODAY, logger=logger)
                    ends = datefromform('end_', group_id, form,
                                        default=None, logger=logger)
                    self._update_view_duration(group_id, member_id, sql,
                                               start, ends,
                                               TODAY)
            message(context,
                    'Changes saved.')
        else:
            message(context,
                    'Nothing to do!', 'error')
        return context.REQUEST.RESPONSE.redirect(context.REQUEST['HTTP_REFERER'])

    # ------------------------------- [ Mitgliedschaften beenden ... [
    def end_group_memberships(self):
        """
        Zum Aufruf aus Formularen: *Beende* Gruppenmitgliedschaften
        (ohne sie spurlos zu entfernen)
        """
        context = self.context
        request = context.REQUEST
        form = request.form
        member_var = form['member_var']
        group_var = form['group_var']
        path = form.get('path') or None
        varnames = form.get('varnames') or None
        return self._end_group_memberships(member_var, group_var,
                                           path=path, varnames=varnames)

    # verwendet von @@groupdesktop.set_end_of_group_membership_to_today:
    def _end_group_memberships(self, member_var, group_var,
                              path=None, varnames=None,
                              **kwargs):
        """
        Beende Gruppenmitgliedschaften

        member_var - Name der Request-Variablen, die einen (Wert: ein String)
                     bzw. mehrere (eine Sequenz) Benutzer- oder Gruppen-IDs angibt
        group_var - dto., für die Gruppe(n), aus denen die vorgenannten
                    Mitglieder entfernt werden sollen
        path - für tryagain_url
        varnames - für tryagain_url

        Üblicherweise gibt nur eine der beiden Variablen eine Sequenz an;
        dies ist aber nicht zwingend.
        """
        # siehe auch --> delete_group_membership_by_group_id
        if 'context' in kwargs:
            context = kwargs.pop('context')
        else:
            context = self.context

        getAdapter = context.getAdapter
        _ = getAdapter('translate')
        request = context.REQUEST
        form = request.form

        member_ids = form.get(member_var, [])

        sing_msg = None
        # zunächst analysieren und group_, member_ids vorbereiten:
        single_member, single_group = (None, None)
        if isinstance(member_ids, basestring) and member_ids:
            single_member = True
            member_ids = [member_ids]
        group_ids = form.get(group_var, [])
        if isinstance(group_ids, basestring) and group_ids:
            single_group = True
            group_ids = [group_ids]

        # ... dann prüfen, ...
        errors = 0
        if not member_ids:
            message(context,
                    'No member ids given', 'error')
            errors += 1
        if not group_ids:
            message(context,
                    'No group ids given', 'error')
            errors += 1
        if errors:
            return back_to_referer(context)

        # dann Meldung erstellen:
        mapping = {}
        if single_member:
            mapping['group_id'] = group_ids[0]
            if single_group:
                sing_msg = ('Membership of ${member_id}'
                            ' in group ${group_id} ended.')
            else:
                sing_msg = ('Membership'
                            ' in group ${group_id} ended.')
        if single_group:
            mapping['member_id'] = member_ids[0]
            if sing_msg is None:
                sing_msg = 'Membership of ${member_id} ended.'

        if varnames is None:
            varnames = (member_var, group_var)
        url = tryagain_url(request, varnames, path)

        with getAdapter("sqlwrapper") as sql:
            counter = 0
            groupdesktop = context.getBrowser('groupdesktop')
            can_admin = groupdesktop._make_group_administration_checker(context)
            ends = TODAY = date.today()
            for group_id in sorted(set(group_ids)):
                if not can_admin(group_id):
                    errors += 1
                    message(context,
                            'You are not allowed to administrate group '
                            '${group_id}',
                            'error',
                            mapping=locals())
                    continue
                for member_id in sorted(set(member_ids)):
                    self._update_view_duration(group_id, member_id,
                                               sql,
                                               0, ends, TODAY)
                    counter += 1
            if counter == 1 and sing_msg:
                message(context,
                        sing_msg, mapping=mapping)
            elif counter:
                message(context,
                        'Ended ${counter} memberships.',
                        mapping=locals())
            elif not errors:
                message(context,
                        'Nothing to do!',
                        'warning')
        return request.RESPONSE.redirect(url)
    # ------------------------------- ] ... Mitgliedschaften beenden ]

    # ----------------------------- [ Mitgliedschaften entfernen ... [
    def delete_group_memberships(self):
        """
        Zum Aufruf aus Formularen: *Entferne* Gruppenmitgliedschaften
        (und lösche sie aus der relationalen Datenbank)
        """
        context = self.context
        request = context.REQUEST
        form = request.form
        member_var = form['member_var']
        group_var = form['group_var']
        path = form.get('path') or None
        varnames = form.get('varnames') or None
        return self._delete_group_memberships(member_var, group_var,
                                           path=path, varnames=varnames)

    def _delete_group_memberships(self, member_var, group_var,
                              path=None, varnames=None,
                              **kwargs):
        """
        Entferne Gruppenmitgliedschaften

        member_var - Name der Request-Variablen, die einen (Wert: ein String)
                     bzw. mehrere (eine Sequenz) Benutzer- oder Gruppen-IDs angibt
        group_var - dto., für die Gruppe(n), aus denen die vorgenannten
                    Mitglieder entfernt werden sollen
        path - für tryagain_url
        varnames - für tryagain_url

        Üblicherweise gibt nur eine der beiden Variablen eine Sequenz an;
        dies ist aber nicht zwingend.
        """
        # siehe auch --> delete_group_membership_by_group_id
        if 'context' in kwargs:
            context = kwargs.pop('context')
        else:
            context = self.context

        getAdapter = context.getAdapter
        _ = getAdapter('translate')
        request = context.REQUEST
        form = request.form

        member_ids = form.get(member_var, [])

        sing_msg = None
        # zunächst analysieren und group_, member_ids vorbereiten:
        single_member, single_group = (None, None)
        if isinstance(member_ids, basestring) and member_ids:
            single_member = True
            member_ids = [member_ids]
        group_ids = form.get(group_var, [])
        if isinstance(group_ids, basestring) and group_ids:
            single_group = True
            group_ids = [group_ids]

        # ... dann prüfen, ...
        errors = 0
        if not member_ids:
            message(context,
                    'No member ids given', 'error')
            errors += 1
        if not group_ids:
            message(context,
                    'No group ids given', 'error')
            errors += 1
        if errors:
            return back_to_referer(context)

        # dann Meldung erstellen:
        mapping = {}
        if single_member:
            mapping['group_id'] = group_ids[0]
            if single_group:
                sing_msg = ('Membership of ${member_id}'
                            ' in group ${group_id} deleted.')
            else:
                sing_msg = ('Membership'
                            ' in group ${group_id} deleted.')
        if single_group:
            mapping['member_id'] = member_ids[0]
            if sing_msg is None:
                sing_msg = 'Membership of ${member_id} deleted.'

        if varnames is None:
            varnames = (member_var, group_var)
        url = tryagain_url(request, varnames, path)

        with getAdapter("sqlwrapper") as sql:
            counter = 0
            groupdesktop = context.getBrowser('groupdesktop')
            can_admin = groupdesktop._make_group_administration_checker(context)
            ends = TODAY = date.today()
            for group_id in sorted(set(group_ids)):
                if not can_admin(group_id):
                    errors += 1
                    message(context,
                            'You are not allowed to administrate group '
                            '${group_id}',
                            'error',
                            mapping=locals())
                    continue
                for member_id in sorted(set(member_ids)):
                    self._delete_group_membership_by_user_id(group_id, member_id,
                                               sql)
                    counter += 1
            if counter == 1 and sing_msg:
                message(context,
                        sing_msg, mapping=mapping)
            elif counter:
                message(context,
                        'Deleted ${counter} memberships.',
                        mapping=locals())
            elif not errors:
                message(context,
                        'Nothing to do!',
                        'warning')
        return request.RESPONSE.redirect(url)

    def _delete_group_membership_by_user_id(self, group_id, user_id, sql):
        """
        Aus edit_group_membership, "Aus ausgewählten Gruppen entfernen":
        löscht die Zuordnungen derzeit spurlos.
        """
        context = self.context
        groups = context.getBrowser('groups')

        group = groups.getById(group_id)
        group.removeMember(user_id)
        where = "WHERE member_id_=%(user_id)s AND group_id_=%(group_id)s"
        sql.delete("unitracc_groupmemberships",
                   where,
                   query_data={'user_id': user_id,
                               'group_id': group_id,
                               })
    # ----------------------------- ] ... Mitgliedschaften entfernen ]

    def search_groups(self, string_='', sort_=True):

        context = self.context
        getBrowser = context.getBrowser

        # hier wollen wir die Gruppen nur sehen,
        # also sollte ViewGroups reichen :
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        if not (checkperm(ManageGroups, context) or
                # TODO: detaillierterer Check für Kursmanager?
                checkperm(ManageCourses, context) or
                checkperm(ViewGroups, context)
            ):
            raise Unauthorized

        acl = getToolByName(context, 'acl_users')
        lightsearch = getBrowser('lightsearch')
        filt = lightsearch.filter
        make_searchstring = groupinfo_factory(context, searchtext=True)
        # list_ = make
        if string_:
            string_ = safe_decode(string_)  # .encode('utf-8')
            try:
                list_ = [group_info
                         for group_info in acl.source_groups._groups.values()
                         if filt(string_, make_searchstring(group_info))
                         ]
            except UnicodeDecodeError as e:
                # print dir(e)
                logger.exception(e)
                for a in ['args', 'encoding', 'end', 'message', 'object',
                    'reason', 'start']:
                    logger.error('I e.%-10s %r', a+':', getattr(e, a, None))
                raise
        else:
            list_ = list(acl.source_groups._groups.values())

        if sort_ and list_[1:]:
            # CHECKME: ist für sortindex wirklich der Kontext nötig?
            # sortindex = getAdapter('sortindex')
            list_.sort(key=getgrouptitle)
            # getkey = make_keyfunction('title', sortindex)
            # list_.sort(key=getkey)
        return list_

    def search_learner_groups(self, string_='', sort_=True):
        """
        Suche learner-Gruppen
        """
        ggibi = groupinfo_factory(self.context)
        list_ = [group for group in
                 [ggibi(group_info['id'])
                  for group_info in self.search_groups(string_, sort_)]
                 if group.get('role') == LEARNER_SUFFIX]

        return list_

    def search_groups_and_users(self, string_=''):
        """
        Gib Benutzer und Gruppen zurück, die dem Suchausdruck entsprechen

        Benutzer: mit @@usermanagement.search;
        Gruppen: mit .search_groups.

        Es findet keinerlei spezielle Behandlung für leere Suchausdrücke statt.

        gf: ../usermanagement/browser.py
        """

        context = self.context
        getBrowser = context.getBrowser
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        if not (checkperm(ManageGroups, context) or
                # TODO: detaillierterer Check für Kursmanager?
                checkperm(ManageCourses, context) or
                checkperm(ViewGroups, context)
            ):
            raise Unauthorized

        form = context.REQUEST.form
        sortindex = context.getAdapter('sortindex')
        acl = getToolByName(context, 'acl_users')
        lightsearch = getBrowser('lightsearch')
        author = getBrowser('author')

        list_ = []
        for dict_ in self.search_groups(string_, False):
            dict_ = dict(dict_)
            dict_['type'] = 'group'
            list_.append(dict_)

        form.update({'SearchableText': string_})
        for brain in getBrowser('usermanagement').search():
            dict_ = {}

            dict_['brain'] = brain
            dict_['title'] = author.get_formatted_name(brain)
            dict_['id'] = brain.getUserId
            dict_['type'] = 'user'
            list_.append(dict_)

        getkey = make_keyfunction('title', sortindex)
        list_.sort(key=getkey)

        return list_

    def add_to_group(self):
        """
        Füge Benutzer und/oder Gruppen einer Gruppe hinzu.
        Formulardaten:

        Formular   | Feldname   | Erklärung
        -----------+------------+----------------------------------------
        group_id   | group_id_  | ursprünglich ging es nur um Kursgruppen
        ids:list   | member_id_ | ursprünglich "(Schul-) Klassen", jetzt
                   |            | allgemein Benutzer- oder Gruppen-IDs
        start_<id> | start      | Startdatum, d.m.yyyy, default: heute
        end_<id>   | ends       | Ablaufdatum, d.m.yyyy, default: leer
        """
        context = self.context
        getAdapter = context.getAdapter

        checkperm = getToolByName(self.context, 'portal_membership').checkPermission
        if checkperm(ManageGroups, context):
            cg_only = False
        elif checkperm(ManageCourses, context):
            # hat noch keine Wirkung:
            cg_only = True  # "course groups only"
        else:
            raise Unauthorized

        request = context.REQUEST
        form = request.form

        group_id = form.get('group_id')
        ids = form.get('ids')   # Nutzer- oder Gruppen-IDs
        logger.info('unitracc@@groupsharing.add_to_group: form=\n%s',
                    pformat(form))

        if group_id and ids:
            if cg_only and 0:
                # nur learner-Gruppen? Das ist möglicherweise zu
                # ungenau!
                dic = split_group_id(group_id)
                if dic['role'] != 'learner':
                    raise Unauthorized
            dupes = list(detect_duplicates(ids))
            if dupes:
                logger.warning('%d Duplikate in Liste von %d IDs:\n%s', len(dupes),
                        len(ids), dupes)
            TODAY = date.today()
            with getAdapter("sqlwrapper") as sql:
                for member_id in ids:
                    if group_id == member_id:
                        message(context,
                                "Won't add group ${group_id} to itself!",
                                'error',
                                mapping=locals())
                        continue
                    start = datefromform('start_', member_id, form,
                                         default=TODAY, logger=logger)
                    ends = datefromform('end_', member_id, form,
                                        default=None, logger=logger)
                    self._update_view_duration(group_id, member_id, sql,
                                               start, ends,
                                               TODAY)
            message(context,
                    'Changes saved.')
        else:
            message(context,
                    'Nothing to do!', 'error')

        return request.RESPONSE.redirect(request['HTTP_REFERER'])

    def delete_groups(self):
        """ """
        # TODO: Vorab prüfen, ob die Gruppe(n) Mitglieder hat/haben;
        #       Information über Anzahl direkter und indirekter Mitglieder,
        #       und Löschen nur unter best. Bedingungen?
        context = self.context

        getAdapter = context.getAdapter
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        if not checkperm(ManageGroups, context):
            raise Unauthorized

        request = context.REQUEST
        form = request.form
        logger.debug('delete_groups: form=\n%s', pformat(form))

        group_ids = form.get('group_ids', [])
        if group_ids:
            acl = getToolByName(context, 'acl_users')

            for group_id in group_ids:
                acl.source_groups.removeGroup(group_id)
                logger.info('group %(group_id)r deleted', locals())

            message(context,
                    'Changes saved.')
        else:
            message(context,
                    'Nothing to do!', 'error')

        return request.RESPONSE.redirect(request['HTTP_REFERER'])

    def update_group(self):
        """ """
        context = self.context

        getAdapter = context.getAdapter
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        if not checkperm(ManageGroups, context):
            raise Unauthorized

        acl = getToolByName(context, 'acl_users')
        form = context.REQUEST.form
        acl.source_groups.updateGroup(group_id=form.get('group_id'),
                                      title=form.get('title', ''),
                                      description=form.get('description', ''),
                                      group_desktop=form.get('group_desktop', ''),
                                      )
        message(context,
                'Changes saved.')

        return context.REQUEST.RESPONSE.redirect(context.REQUEST['HTTP_REFERER'])

    def voc_get_explicit_group_memberships_for_auth(self):
        """
        auswaehlbare Gruppen fuer Freigabe
        """

        context = self.context
        member = getToolByName(context, 'portal_membership').getAuthenticatedMember()
        gd = context.getBrowser('groupdesktop')
        excluded = gd.getGroupsBlacklist()
        return [(dict_['id'], dict_['group_title'])
                for dict_ in self.get_groups_by_user_id(member.getId())
                if dict_['id'] not in excluded
                ]

    def can_view_unitracc_groups(self):
        """
        für Schema: regelt den Zugriff auf das Gruppenfreigabe-Widget
        """

        context = self.context
        checkperm = getToolByName(context, 'portal_membership').checkPermission

        for perm in ('Manage portal',
                     # ViewGroups,
                     ManageGroups,
                     ):
            if checkperm(perm, context):
                return True

        member = getToolByName(context, 'portal_membership').getAuthenticatedMember()
        if context.Creator() == member.getId():
            if context.getReviewState() != 'published':
                return True

        return False  # pep 20.2

    def get_permission_authors(self):
        # TODO: direkte Einbindung in unitracc.content.base.getCustomSearch?
        # TODO: Set verwenden;
        # XXX: Doppelverwendung der Variablen <id>!

        context = self.context
        pg = getToolByName(context, 'portal_groups')
        acl = getToolByName(context, 'acl_users')

        dict_ = {}

        for id in context.users_with_local_role('Owner'):
            dict_[id] = 1

        for id in context.users_with_local_role('Author'):
            user = acl.getUser(id)
            if user:
                dict_[id] = 1

            for id in pg.getGroupMembers(id):
                dict_[id] = 1

        return dict_.keys()

    def get_custom_search_authors(self):

        return ['author=' + id
                for id in self.get_permission_authors()]

    def connect_groups(self):
        """ Verbindet manuell erstellte Gruppen mit automatisch erstellten Kursgruppen. """
        self._connect_groups()

    def _connect_groups(self, today=None, journal=None,  # ----- [ _c._g. ... [
                        ggibi=None):
        context = self.context
        portal = getToolByName(context, 'portal_url').getPortalObject()
        getAdapter = context.getAdapter
        grouplog = getAdapter('grouplog')
        if journal is None:
            journal = []
        if ggibi is None:
            ggibi = groupinfo_factory(context, forlist=True)
        ok = True
        sm = portal.getAdapter('securitymanager')
        sm(userId='system')
        sm.setNew()
        try:
            # ------------------------------------------ ... _connect_groups ...
            with getAdapter('sqlwrapper') as sql:
                groupbrowser = context.getBrowser("groups")
                if today is None:
                    table = 'groupmemberships_for_creation__view'
                    query_data = None
                    where = None
                else:
                    table = 'groupmemberships_pending__baseview'
                    query_data = {'start': today}
                    where = ('WHERE "start" <= %(start)s'
                             ' AND (ends IS NULL'
                                  ' OR ends > %(start)s)'
                             )
                logger.info('_connect_groups: verwende Sicht %(table)s',
                            locals())
                if where is not None:
                    logger.info('_connect_groups: where=\n'
                                '\t%(where)s\n'
                                'query_data=\n'
                                '\t%(query_data)s',
                                locals())
                fields = ['group_id_', 'member_id_',
                          'start', 'ends',
                          'active', 'done',
                          'id',
                          ]
                # auf "active" nicht prüfen - maßgeblich ist Zope!
                result = sql.select(table=table,  # Name der Sicht
                                    fields=fields,
                                    where=where,
                                    query_data=query_data)
                # Schreiboperationen müssen auf die Tabelle gehen:
                table = "unitracc_groupmemberships"
                logger.info('_connect_groups: %d Zeilen gefunden', len(result))
                done_ids = []     # erledigte Einträge
                changed_ids = []  # Das Ende-Datum steht noch aus!
                gone_ids = []     # Verflossene Gruppen
                by = '- Scheduler -'
                try:
                    # ---------------------------------- ... _connect_groups ...
                    for row in result:
                        group_id = row['group_id_']
                        course = groupbrowser.getById(group_id)
                        if course is None:
                            msgtext = (
                                'Could not connect member %(member_id_)s '
                                'to group %(group_id_)s: group not found'
                                % row)
                            journal.append((False, msgtext))
                            logger.error(msgtext)
                            ok = False
                            gone_ids.append(row['id'])
                            grouplog.missing(by=by, **row)
                            continue
                        group_title = ggibi(group_id)['group_title']
                        course.addMember(row['member_id_'])
                        journal.append((True, 'Added member %(member_id_)s '
                            'to group %(group_id_)s'
                            % row))
                        logger.info('_connect_groups, group %(group_id_)s:'
                                    ' adding member %(member_id_)s',
                                    row)
                        ends = row['ends']
                        grouplog.added(by=by, group_title=group_title, **row)
                        if ends is None or ends < today:
                            done_ids.append(row['id'])
                        else:
                            changed_ids.append(row['id'])
                finally:
                    logger.info('_connect_groups: %d Zeilen zu aendern', len(changed_ids))
                    # ---------------------------------- ... _connect_groups ...
                    if changed_ids:
                        rows = list(sql.update(table,
                                          {'active': True,
                                           },
                                          query_data={'id': changed_ids},
                                          returning=['id']))
                        journal.append((True, 'Updated %d rows (%d IDs, sets:'
                            '%d in, %d out'
                            % (len(rows), len(changed_ids),
                               len(set(changed_ids)),
                               len(set([row['id'] for row in rows])),
                               )))
                        logger.info('_connect_groups: %d rows updated'
                                    ' (still active)',
                                    len(rows))
                    if done_ids:
                        rows = list(sql.update(table,
                                          {'active': True,
                                           'done': True,
                                           },
                                          query_data={'id': done_ids},
                                          returning=['id']))
                        journal.append((True, 'Updated %d rows (%d IDs, sets:'
                            '%d in, %d out'
                            % (len(rows), len(done_ids),
                               len(set(done_ids)),
                               len(set([row['id'] for row in rows])),
                               )))
                        logger.info('_connect_groups: %d rows updated'
                                    ' (completed)',
                                    len(rows))
                    # ---------------------------------- ... _connect_groups ...
                    if gone_ids:
                        logger.warning('_connect_groups: %d obsolete Zeilen', len(gone_ids))
                        rows = list(sql.update(table,
                                          {'active': False,
                                           'done': True,
                                           },
                                          query_data={'id': gone_ids},
                                          returning=['id']))
                        journal.append((True, 'Updated %d rows (%d IDs, sets:'
                            '%d in, %d out'
                            % (len(rows), len(gone_ids),
                               len(set(gone_ids)),
                               len(set([row['id'] for row in rows])),
                               )))
                        logger.info('_connect_groups: %d obsolete rows settled', len(rows))
        except Exception as e:
            logger.exception(e)
            journal.append((False, e.__class__.__name__))
            ok = False
        finally:
            sm.setOld()
        return ok  # ----------------------------------- ] ... _connect_groups ]

    def disconnect_groups(self):
        """
        Trennt manuell erstellte Gruppen von automatisch erstellten Kursgruppen.
        """
        context = self.context
        request = context.REQUEST
        form = request.form
        verbose = makeBool(form.get('verbose', ''))
        if verbose:
            journal = []
        else:
            journal = None
        ok = self._disconnect_groups(journal=journal)
        if verbose:
            txt = (journal and journal_text(journal)
                   or 'Disconnect members: No changes')
            print txt
            if verbose >= 2:
                return txt
        return ok

    def _disconnect_groups(self, today=None, journal=None,  # -- [ _dc._g. ... [
                           ggibi=None):
        """
        Lies die Tabelle unitracc_groupmemberships aus
        und beende entsprechend die heute ablaufenden Gruppenmitgliedschaften
        """
        context = self.context
        getAdapter = context.getAdapter
        portal = getToolByName(context, 'portal_url').getPortalObject()
        grouplog = getAdapter('grouplog')
        if journal is None:
            journal = []
        ok = True
        sm = portal.getAdapter('securitymanager')
        sm(userId='system')
        sm.setNew()
        try:
            if ggibi is None:
                ggibi = groupinfo_factory(context, forlist=True)
            with getAdapter('sqlwrapper') as sql:
                by = '- Scheduler -'
                groupbrowser = context.getBrowser("groups")
                if today is None:
                    table = 'groupmemberships_for_deletion__view'
                    query_data = None
                    where = None
                else:
                    table = 'groupmemberships_pending__baseview'
                    query_data={'ends': today}
                    where = ('WHERE ends IS NOT NULL'
                              ' AND ends <= %(ends)s'
                              )
                logger.info('_disconnect_groups: verwende Sicht %(table)s',
                            locals())
                if where is not None:
                    logger.info('_disconnect_groups: where=\n'
                                '\t%(where)s\n'
                                'query_data=\n'
                                '\t%(query_data)s',
                                locals())
                fields = ['group_id_', 'member_id_',
                          'start', 'ends',
                          'id',
                          ]
                result = sql.select(table=table,  # Name der Sicht
                                    fields=fields,
                                    where=where,
                                    query_data=query_data)
                # ----------------------------------- ... _disconnect_groups ...
                # Schreiboperationen müssen auf die Tabelle gehen:
                table = "unitracc_groupmemberships"
                logger.info('_disconnect_groups: %d Zeilen zu aendern',
                            len(result))
                portal_groups = getToolByName(getSite(), 'portal_groups')
                done_ids = []     # erledigte Einträge
                gone_ids = []     # Verflossene Gruppen
                # wenn in dieser Methode eine Zeile verarbeitet wird, ist sie
                # *immer* erledigt, weil das ends-Datum abgelaufen ist!
                # `---> done=True
                NEW_DATA = {'active': False,
                            'done': True,
                            }
                for row in result:
                    member_id = row['member_id_']
                    group_id = row['group_id_']
                    try:
                        if portal_groups.removePrincipalFromGroup(
                                member_id, group_id):
                            journal.append((True, 'Removed member %(member_id_)s '
                                'from group %(group_id_)s'
                                % row))
                        else:
                            journal.append((True, '%(member_id_)s '
                                'was no member of group %(group_id_)s'
                                % row))
                        done_ids.append(row['id'])
                    except KeyError:
                        grouplog.missing(by=by, **row)
                        journal.append((False,
                            'Could not remove member %(member_id_)s '
                            'from group %(group_id_)s: group not found'
                            % row))
                    except NameError as e:
                        ename = e.__class__.__name__
                        logger.error('%(ename)s: '
                            'Could not remove member %(member_id)s '
                            'from group %(group_id)s',
                            locals())
                        logger.error('row: %(row)s', locals())
                        logger.exception(e)
                        journal.append((False,
                            '%(ename)s: '
                            'Could not remove member %(member_id)s '
                            'from group %(group_id)s'
                            % locals()))
                    else:
                        row.update(NEW_DATA)
                        group_title = ggibi(group_id)['group_title']
                        grouplog.removed(by=by,
                                         group_title=group_title,
                                         **row)
                    finally:
                        logger.info('_disconnect_groups, group %(group_id_)s:'
                                    ' removing member %(member_id_)s',
                                    row)
                # ----------------------------------- ... _disconnect_groups ...
                if done_ids:
                    rows = list(sql.update(table,
                                      NEW_DATA,
                                      query_data={'id': done_ids},
                                      returning=['id']))
                    journal.append((True, 'Updated %d rows (%d IDs, sets:'
                        '%d in, %d out'
                        % (len(rows), len(done_ids),
                           len(set(done_ids)),
                           len(set([row['id'] for row in rows])),
                           )))
                    logger.info('_disconnect_groups: %d rows updated'
                                ' (completed)',
                                len(rows))
                if gone_ids:
                    rows = list(sql.update(table,
                                      NEW_DATA,
                                      query_data={'id': gone_ids},
                                      returning=['id']))
                    journal.append((True, 'Updated %d rows (%d IDs, sets:'
                        '%d in, %d out'
                        % (len(rows), len(gone_ids),
                           len(set(gone_ids)),
                           len(set([row['id'] for row in rows])),
                           )))
                    logger.info('_disconnect_groups: %d obsolete rows settled', len(rows))
                transaction.commit()
        except Exception as e:
            journal.append((False, e.__class__.__name__))
            ok = False
        finally:
            sm.setOld()
            return ok  # ---------------------------- ] ... _disconnect_groups ]

    @log_or_trace(0, logger=logger, trace=1)
    def scheduled_group_memberships(self):
        """
        Arbeite die Gruppenzuordnungen ab gemäß der Tabelle
        unitracc_groupmemberships (neuer cron-Job).

        Keine Prüfung auf Berechtigungen, da ohnehin keine Angaben möglich
        sind (über den Inhalt der rel. Datenbank hinaus)!
        Es werden lediglich ggf. die ausführlichen Ausgaben abgeschaltet
        (was kein Problem ist, wg. Loggings).

        Siehe <http://dev-wiki.unitracc.de/wiki/Zeitgesteuerte_Gruppenzuweisung>
        """
        context = self.context
        request = context.REQUEST
        # print dir(request.RESPONSE)
        form = request.form
        verbose = makeBool(form.get('verbose', ''))
        if verbose:
            checkperm = getToolByName(context, 'portal_membership').checkPermission
            if not checkperm(ManageGroups, context):
                verbose = False
        journal = []
        # jedenfalls beide ausführen:
        ok = self._connect_groups(journal=journal)
        if not self._disconnect_groups(journal=journal):
            ok = False
        if not ok:
            request.RESPONSE.setStatus(500)
        if verbose:
            lines = []
            if not journal:
                lines.append('scheduled_group_memberships: '
                             'nothing to do')
            for boo, txt in journal:
                if not boo or verbose > 1:
                    lines.append(' '.join((boo and 'i' or 'E',
                                           txt)))
            lines.append('')
            return '\n'.join(lines)
        elif True:  # sonst nicht wegzukriegende Ausgabe ...
            if journal:
                logger.info('scheduled_group_memberships() beendet;'
                            ' Journal: %s',
                            journal_text(journal))
            else:
                logger.info('scheduled_group_memberships() beendet;'
                            ' Journal ist leer')
            return ''
        elif ok:
            return ''
        else:
            return '%d error(s)' % len([tup
                                        for tup in journal
                                        if not tup[0]
                                        ])

    def replay_groups(self):
        """
        Gruppenzuordnungen "nachholen".  Da die Formulardaten Datumswerte
        enthalten können, darf das nur von einem Admin gemacht werden.

        Argumente (aus Query-String):

          start -- erforderlich
          end -- optional

          (beides Strings im Format d.m.jjjj)

        TODO: Testen mit neuen Versionen von _[dis]connect_groups
        """
        context = self.context
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        if not checkperm(ManageGroups, context):
            raise Unauthorized
        res = ['<html>']

        def tell(s, elem='p'):
            if elem:
                res.append('<%(elem)s>%(s)s</%(elem)s>'
                           % locals())
            print s
        request = context.REQUEST
        form = request.form
        start = form.get('start')
        start = makedate(start)
        end = form.get('end')
        if end:
            end = makedate(end)
        else:
            end = date.today()
        tell('Gruppenzuordnungen nachholen', 'h1')
        tell('start: %s' % start)
        tell('end: %s' % end)
        assert start <= end
        limit = 500
        counter = 0
        day = start
        ONEDAY = timedelta(1)
        while day <= end:
            tell('%s:' % day, 'h2')
            changes_here = 0
            changes = self._connect_groups(day)
            if changes:
                changes_here += changes
                tell('%d connections' % (changes,))
            changes = self._disconnect_groups(day)
            if changes:
                changes_here += changes
                tell('%d disconnections' % (changes,))
            if not changes_here:
                tell('no changes')
            day += ONEDAY
            counter += 1
            if counter >= limit:
                tell('Abbruch', 'h2')
                tell('limit erreicht (%d)' % limit)
                break
        res.append('</html>')
        return '\n'.join(res)

    def update_view_duration(self):
        """
        1. Ermittle, ob der heutige Tag im Zeitraum der Zugehörigkeit liegt
        2. Trage neue Werte für Start und Ende für Benutzer und Gruppe in die
        Datenbank ein bzw. aktualisiere einen etwa schon vorhandenen Datensatz
        3. Setze oder entferne entsprechend die Zope-Gruppenzugehörigkeit;
        4. gib einen entsprechenden logischen Wert zurück.

        (bis auf die Ermittlung der Eingabewerte alles durch
        _update_view_duration erledigt)
        """
        context = self.context
        form = context.REQUEST.form

        # 1. Zeitraum der Zugehörigkeit
        start = makedate(form.get('start'))
        ends = makedate(form.get('end'))

        group_key = form.get('group_key', 'course')
        member_key = form.get('member_key', 'group')
        group_id = form.get(group_key)
        member_id = form.get(member_key)
        with context.getAdapter('sqlwrapper') as sql:
            # 2. Eintragung in Datenbank   und
            # 3. Zope-Gruppenzugehörigkeit:
            return self._update_view_duration(group_id, member_id, sql,
                                              start, ends)

    @log_or_trace(debug_active, logger=logger)
    def _update_view_duration(self,  # -------------- [ _u.v.d() ... [
                              group_id, member_id,
                              sql,
                              start, ends, TODAY=None):
        """
        1. Ermittle, ob der heutige Tag im Zeitraum der Zugehörigkeit liegt
        2. Trage neue Werte für Start und Ende für Benutzer und Gruppe in die
        Datenbank ein bzw. aktualisiere einen etwa schon vorhandenen Datensatz
        3. Setze oder entferne entsprechend die Zope-Gruppenzugehörigkeit
        4. Gib einen logischen Wert zurück, der informiert, ob die
        Gruppenmitgliedschaft nach Ausführung besteht (True) oder nicht (False).

        Wenn start == 0, wird *kein* Wert für start geschrieben
        """
        # 1. Zeitraum der Zugehörigkeit
        # (Tests auf None müssen explizit erfolgen!)
        if TODAY is None:
            TODAY = date.today()
        nostart = start == 0
        if nostart:
            start = None
        if start is None:
            if ends is None:
                now_active = True
            else:
                now_active = TODAY < ends
        elif ends is None:
            now_active = start <= TODAY
        else:
            now_active = start <= TODAY < ends
        # ------------------------------ ... _update_view_duration ...

        # 2. Eintragung in Datenbank
        NEWDATA = {'start':  start,
                   'ends':   ends,
                   'active': now_active,
                   }
        if nostart:
            # XXX bei Änderung eines vorhandenen Datensatzes
            #     wird das Startdatum nicht entfernt!
            del NEWDATA['start']
            NEWDATA['done'] = not now_active
        elif start is None:  # "can't compare datetime.date to NoneType"! :-(
            NEWDATA['done'] = not now_active
        elif start <= TODAY:
            # Startdatum [vor] heute; Enddatum auch schon vorbei?
            NEWDATA['done'] = not now_active
        # ... das Startdatum liegt in der Zukunft:
        elif ends is None:
            # vorgezogen, da kleiner als Startdatum:
            NEWDATA['done'] = False
        elif start >= ends:
            # Ende- kleiner als Startdatum?!
            # Fehlerhafter Eintrag, der sich sofort selbst erledigt:
            NEWDATA['done'] = True
        else:
            NEWDATA['done'] = False
        query_data = {'group_id_':  group_id,
                      'member_id_': member_id,
                      }
        table = "unitracc_groupmemberships"
        where = "WHERE group_id_=%(group_id_)s and member_id_=%(member_id_)s"

        # ------------------------------ ... _update_view_duration ...
        rows = sql.select(table, where=where,
                          query_data=query_data)
        if rows:
            if debug_active:
                pp('Daten gefunden!',
                   query_data=query_data,
                   rows=rows,
                   NEWDATA=NEWDATA)
            sql.update(table, NEWDATA, where, query_data=query_data)
        else:
            if debug_active:
                pp('Keine Daten gefunden!',
                   query_data=query_data,
                   NEWDATA=NEWDATA)
            NEWDATA.update(query_data)
            sql.insert(table, NEWDATA)

        # 3. Zope-Gruppenzugehörigkeit
        context = self.context
        acl = getToolByName(context, 'acl_users')
        groups = context.getBrowser('groups')
        group_o = groups.getById(group_id)
        members = acl.source_groups._group_principal_map[group_id]
        if now_active:
            if member_id not in members:
                group_o.addMember(member_id)
            else:
                NEWDATA['active_before'] = True
        else:
            if member_id in members:
                group_o.removeMember(member_id)
            else:
                NEWDATA['active_before'] = False
        ggibi = groupinfo_factory(context, forlist=1)
        group_title = ggibi(group_id)['group_title']
        context.getAdapter('grouplog').row_updated(group_id=group_id,
                                                   group_title=group_title,
                                                   member_id=member_id,
                                                   **NEWDATA)
        return now_active  # --------- ] ... _update_view_duration() ]

    def get_group_manager_for_group_id(self, group_id):

        context = self.context
        groupbrowser = context.getBrowser('groups')
        group = groupbrowser.getById(group_id)
        return group.getProperty('group_manager')

    def get_course_info_for_group_ids(self, group_ids):

        context = self.context

        list_ = []
        for group_id in group_ids:
            for dict_ in self.get_inherited_group_memberships_by_group_id(group_id):
                try:
                    brain = dict_['brain']
                    if brain and brain.portal_type == 'UnitraccCourse':
                        list_.append(dict_)
                except (KeyError, AttributeError) as e:
                    pass

        return list_

    def get_manageable_groups(self, group_id=None, pretty=True, forlist=None):
        """
        Gib die Gruppen zurück, die der aktuell angemeldete Benutzer
        administrieren darf.

        group_id -- wenn übergeben, wird nur genau diese eine verwendet
        pretty -- siehe groupinfo_factory
        forlist -- wenn von Manager aufgerufen,
                   kann die "kleine Info" besorgt werden (siehe den Code)
        """
        context = self.context
        getAdapter = context.getAdapter
        checkperm = getToolByName(context, 'portal_membership').checkPermission
        is_group_manager = checkperm(ManageGroups, context)
        if is_group_manager:
            if forlist is None:
                forlist = True
        else:
            forlist = False  # group_manager-Information wird benötigt
            user = getToolByName(context, 'portal_membership').getAuthenticatedMember()
            user_id = str(user)
        ggibi = groupinfo_factory(self.context, pretty, forlist)
        if group_id:
            group_ids = [group_id]
        elif is_group_manager:
            # alle interessanten:
            group_ids = self.get_all_group_ids()
        else:
            group_ids = set(user.getGroups()).difference(BORING_GROUPS)
        if is_group_manager:
            res = map(ggibi, list(group_ids))
        else:
            res = []
            for group_id in group_ids:
                dic = ggibi(group_id)
                if dic['group_manager'] == user_id:
                    res.append(dic)
        res.sort(key=getgrouptitle)
        return res

    def get_all_members(self, group_ids, **kwargs):
        """
        Liefere alle Mitglieder der übergebenen Gruppe(n).

        Schlüsselwortargumente für .utils.recursive_members und
        groupinfo_factory dürfen angegeben werden;
        letztere werden aber ignoriert, wenn die vorgabegemäße Filterung
        groups_only=True übersteuert wird. In diesem Fall (potentiell sowohl
        Benutzer als auch Gruppen, oder nur Benutzer) werden nur IDs
        zurückgegeben.

        Rückgabe:
        - Sequenz von Gruppeninformationen, mit groups_only=True (Vorgabe);
        - ansonsten nur eine Sequenz der IDs (je nach Aufrufargumenten nur
          Benutzer-IDs, oder gemischt)
        """
        context = self.context
        acl = getToolByName(context, 'acl_users')
        gpm = acl.source_groups._group_principal_map
        filter_args = {}
        for key in ('groups_only', 'users_only',
                    'containers',
                    'default_to_all'):
            try:
                filter_args[key] = kwargs.pop(key)
            except KeyError:
                pass
        members = recursive_members(list_of_strings(group_ids),
                                    gpm, **filter_args)
        groups_only = filter_args.get('groups_only', False)
        if groups_only:
            format_args = {'pretty': False,
                           'forlist': True,
                           }
            format_args.update(kwargs)
            ggibi = groupinfo_factory(context, **format_args)
            res = []
            for gid in members:
                res.append(ggibi(gid))
            return res
        elif kwargs and debug_active:
            pp('ignoriere:', kwargs)

        return members

    def is_member_of_any(self, group_ids, user_id=None, default=False):
        """
        Ist der übergebene Benutzer Mitglied einer der übergebenen Gruppen?

        - wenn user_id nicht übergeben wird, wird der angemeldete Benutzer
          verwendet
        - wenn die Liste der Gruppen-IDs leer ist, wird der Vorgabewert
          verwendet (default)
        """
        context = self.context
        getBrowser = context.getBrowser
        getBrowser('authorized').raiseAnon()
        if user_id is not None:
            # wer darf sowas fragen? Manager, Gruppenmanager, ...?
            # TODO: Hier entsprechende Überprüfung!
            pass

        if not group_ids:
            return default
        if user_id is None:
            member = getToolByName(context, 'portal_membership').getAuthenticatedMember()
            user_id = member.getId()

        return user_id in self.get_all_members(group_ids)


# ----------------------------------------- [ Factory-Funktionen ... [
def is_direct_member__factory(context, userid):
    """
    Erzeuge eine Funktion, die prüft, ob der *beim Erzeugen angegebene* Nutzer
    in der bei jedem Aufruf anzugebenden Gruppe direkt enthalten ist.
    """
    acl = getToolByName(context, 'acl_users')
    gpm = acl.source_groups._group_principal_map
    # <BTrees.OOBTree.OOBTree object at ...>
    # print 'gpm: %(gpm)r' % locals()

    def is_direct_member_of(group_id):
        return userid in gpm[group_id]

    return is_direct_member_of


def is_member_of__factory(context, userid):
    """
    Erzeuge eine Funktion, die die *direkte oder indirekte* Mitgliedschaft
    des übergebenen Users in der jeweils zu übergebenden Gruppe überprüft.
    """
    acl = getToolByName(context, 'acl_users')
    gpm = acl.source_groups._group_principal_map
    # <BTrees.OOBTree.OOBTree object at ...>
    # print 'gpm: %(gpm)r' % locals()

    groups = build_groups_set(gpm, userid)

    def is_member_of(groupid):
        return groupid in groups

    return is_member_of


def get_group_mapping_course__factory(context, group_ids, group_info):
    """
    "get (the) group mapping (the) course"

    Erzeuge eine Funktion, die die Gruppe zurückgibt, die
    - die übergebene Kursgruppe vermittelt, und
    - einen Schreibtisch erzeugt

    Argumente:
    group_ids - vorab ermittelte Menge aller interessierenden Gruppen
                (in denen der Benutzer direkt oder indirekt Mitglied ist)
    group_info - ein dict-Objekt zur Pufferung aller angeforderten
                 Gruppen-Infos (siehe visaplan.tools.classes.Proxy)
    """
    getAdapter = context.getAdapter
    acl = getToolByName(context, 'acl_users')
    gpm = acl.source_groups._group_principal_map

    def get_group_mapping_course(coursegroup_id):
        """
        Gib die erste Gruppe zurück, die die übergebene Kursgruppe vermittelt

        coursegroup_id - die ID einer primären Kursgruppe, die evtl. einen
                         Schreibtisch erzeugt, wahrscheinlich aber nicht

        Das Ergebnis enthält:
        - garantiert den Schlüssel 'coursegroup_id'
        - einen Schlüssel 'stats' für die (hier nicht gefüllte!) Statistik
        - UID, Title und Brain des Kurses
        - im Erfolgsfall die Gruppeninfo der nächsten vermittelnden Gruppe
          (bei user_id -> group_a -> group_b -> group_abc123_learner wäre das
          die der Gruppe group_a)
        """
        course_uid, pseudorole = coursegroup_id.split('_')[1:]
        course_brain = getbrain(context, course_uid)
        dic2 = {'coursegroup_id': coursegroup_id,
                'course_uid': course_uid,
                'course_brain': course_brain,
                'course_title': course_brain and course_brain.Title,
                'stats': None,
                }
        done = set()

        def inner(group_id):
            if group_id in done:
                return
            done.add(group_id)
            if group_id not in group_ids:
                return
            # zuerst die Rekursion:
            for child_id in gpm[group_id]:
                res = inner(child_id)
                if res is not None:
                    return res
            try:
                dic = group_info[group_id]
                if dic['group_desktop']:
                    return dic
            except KeyError:
                pass

        dic = inner(coursegroup_id)
        if dic is not None:
            dic2.update(dic)
        return dic2

    return get_group_mapping_course


# -------------------------------- [ groupinfo_factory ... [
def groupinfo_factory(context, pretty=0, forlist=0, searchtext=0):
    """
    Factory-Funktion; als Ersatz für get_group_info_by_id, insbesondere für
    wiederholte Aufrufe.  Indirektionen etc. werden einmalig beim Erstellen der
    Funktion aufgelöst und anschließend in einer Closure vorgehalten.

    pretty -- Gruppennamen auflösen, wenn Suffix an ID und Titel
    forlist -- Minimale Rückgabe (nur ID und Titel),
               aber mit pretty kombinierbar
    """
    getAdapter = context.getAdapter
    pg = getToolByName(context, 'portal_groups')
    get_group = pg.getGroupById
    acl = getToolByName(context, 'acl_users')
    translate = getAdapter('translate')
    GROUPS = acl.source_groups._groups

    def minimal_group_info(group_id):
        """
        Nur ID und Titel
        """
        group = get_group(group_id)

        dict_ = {'id': group_id}
        try:
            thegroup = GROUPS[group_id]
            dict_['group_title'] = safe_decode(thegroup['title'])
            return dict_
        except KeyError:
            return {}

    def basic_group_info(group_id):
        """
        Gib ein Dict. zurück;
        - immer vorhandene Schlüssel:
          id, group_title, group_description, group_manager, group_desktop
        - nur bei automatisch erzeugten Gruppen: role, role_translation, brain

        Argumente:
        group_id -- ein String, normalerweise mit 'group_' beginnend
        """

        group = get_group(group_id)

        dict_ = {'id': group_id}
        try:
            thegroup = GROUPS[group_id]
            dict_['group_title'] = safe_decode(thegroup['title'])
        except KeyError:
            return {}
        dict_['group_description'] = safe_decode(thegroup['description'])
        dict_['group_manager'] = thegroup.get('group_manager')
        dict_['group_desktop'] = thegroup.get('group_desktop')

        dic = split_group_id(group_id)
        if dic['role'] is not None:
            dict_.update(dic)

        dict_['role_translation'] = translate(dic['role'])
        dict_['brain'] = getbrain(context, dic['uid'])
        return dict_

    def pretty_group_info(group_id):
        """
        Ruft basic_group_info auf und fügt einen Schlüssel 'pretty_title'
        hinzu, der den Gruppentitel ohne das Rollensuffix enthält.
        """
        dic = basic_group_info(group_id)
        try:
            if 'role' not in dic:
                dic['pretty_title'] = translate(dic['group_title'])
                return dic
            liz = dic['group_title'].split()
            if liz and liz[-1] == dic['role']:
                stem = u' '.join(liz[:-1])
                mask = PRETTY_MASK[dic['role']]
                dic['pretty_title'] = translate(mask).format(group=stem)
            else:
                dic['pretty_title'] = translate(dic['group_title'])
        except KeyError as e:
            # evtl. keine Gruppe! (Aufruf durch get_mapping_group)
            print e
            pass
        return dic

    @log_or_trace(debug_active, logger=logger)
    def minimal2_group_info(group_id):
        """
        Ruft minimal_group_info auf und modifiziert ggf. den Schlüssel
        'group_title' (entsprechend dem von pretty_group_info zurückgegebenen
        Schlüssel 'pretty_title')
        """
        dic = minimal_group_info(group_id)
        if not dic:     # Gruppe nicht (mehr) gefunden;
            return dic  # {} zurückgeben
        dic2 = split_group_id(group_id)
        if dic2['role'] is not None:
            dic.update(dic2)
        if 'role' not in dic:
            dic['group_title'] = translate(dic['group_title'])
            return dic
        liz = dic['group_title'].split()
        if liz and liz[-1] == unicode(dic['role']):
            stem = u' '.join(liz[:-1])
            mask = PRETTY_MASK[dic['role']]
            dic['group_title'] = translate(mask).format(group=stem)
        else:
            dic['group_title'] = translate(dic['group_title'])
        return dic

    def make_searchstring(group_info):
        """
        Arbeite direkt auf einem group_info-Dict;
        Gib kein Dict zurück, sondern einen String für Suchzwecke
        """
        try:
            group_id = group_info['id']
        except KeyError:
            raise
        try:
            res = [safe_decode(group_info['title']),
                   safe_decode(group_id)]
        except KeyError:
            print group_info.items()
            raise
            return u''
        dic2 = split_group_id(group_id)
        prettify = True
        for val in dic2.values():
            if val is None:
                prettify = False
                break  # es sind immer alle None, oder alle nicht None
            else:
                res.append(safe_decode(val))
        if prettify:
            pretty = pretty_group_title(group_id, res[0], translate)
            if pretty is not None:
                res.append(safe_decode(pretty))
        descr = group_info['description']
        if descr:
            res.append(safe_decode(descr))
        # print res
        return u' '.join(res)  # .encode('utf-8')


    if searchtext:
        return make_searchstring
    if forlist:
        if pretty:
            return minimal2_group_info
        else:
            return minimal_group_info
    if pretty:
        return pretty_group_info
    else:
        return basic_group_info
# -------------------------------- ] ... groupinfo_factory ]

# --------------------------------- [ userinfo_factory ... [
def userinfo_factory(context, pretty=0, forlist=0,
                     title_or_id=0):
    """
    Wie groupinfo_factory, aber für Benutzerobjekte.

    pretty -- für Benutzer: title als formatierter Name
              (author.get_formatted_name), wenn möglich
    forlist -- Minimale Rückgabe (nur ID und Titel),
               aber mit pretty kombinierbar
    title_or_id -- für Verwendung mit visaplan.tools.classes.Proxy:
               gib nur den Title oder ersatzweise die ID zurück
               (mit pretty kombinierbar)
    """
    getAdapter = context.getAdapter
    acl = getToolByName(context, 'acl_users')
    acl_gu = acl.getUser
    if pretty or not forlist:
        getBrowser = context.getBrowser
        author = getBrowser('author')
        gbbuid = author.getBrainByUserId
        gfn = author.get_formatted_name

    # ---------------------------- [ forlist ... [
    def basic_user_info(member_id):
        """
        Basisinformationen über einen Benutzer:
        id, title

        forlist, not: pretty
        """
        member = acl_gu(member_id)
        if member:
            return {'id': member_id,
                    'title': member.getProperty('fullname'),
                    }

    def pretty_user_info(member_id):
        """
        Basisinformationen über einen Benutzer:
        id, title

        forlist, pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            return {'id': member_id,
                    'title': (brain and gfn(brain))
                             or member.getProperty('fullname'),
                    }
    # ---------------------------- ] ... forlist ]

    # ------------------------ [ title_or_id ... [
    def pretty_title_or_id(member_id):
        try:
            return pretty_user_info(member_id)['title'] \
                   or member_id
        except:
            return None

    def basic_title_or_id(member_id):
        try:
            return basic_user_info(member_id)['title'] \
                   or member_id
        except:
            return None
    # ------------------------ ] ... title_or_id ]

    def full_user_info(member_id):
        """
        not: forlist, not: pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            return {'id': member_id,
                    'title': member.getProperty('fullname'),
                    'brain': brain,
                    'email': member.getProperty('email'),
                    }

    def full_pretty_user_info(member_id):
        """
        not: forlist, pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            return {'id': member_id,
                    'title': (brain and gfn(brain))
                             or member.getProperty('fullname'),
                    'brain': brain,
                    'email': member.getProperty('email'),
                    }

    if title_or_id:
        if pretty:
            return pretty_title_or_id
        else:
            return basic_title_or_id
    if forlist:
        if pretty:
            return pretty_user_info
        else:
            return basic_user_info
    if pretty:
        return full_pretty_user_info
    else:
        return full_user_info
# --------------------------------- ] ... userinfo_factory ]

# ------------------------------- [ memberinfo_factory ... [
def memberinfo_factory(context, pretty=0, forlist=0, bloated=0):
    """
    Wie groupinfo_factory, aber für Gruppen- und Benutzerobjekte.
    Es wird zusätzlich ein Feld 'type' gefüllt, das die Werte
    'user', 'group' oder (mit bloated >= 2) None annehmen kann.

    Die folgenden beiden werden einfach an groupinfo_factory bzw.
    userinfo_factory weitergereicht:

    pretty -- Gruppennamen auflösen, wenn Suffix an ID und Titel;
              für benutzer: title als formatierter Name (author
    forlist -- Minimale Rückgabe (nur ID und Titel),
               aber mit pretty kombinierbar

    Zusätzliches Argument:

    bloated -- Schlüssel hinzufügen für Mitgliederliste wie in Tabelle
               unitracc_groupmemberships.
               Wenn >= 2, werden auch für nicht gefundene Mitglieder Einträge
               zurückgegeben (noch nicht getestet)

               ACHTUNG: Der Schlüssel 'ismember_zope' wird immer mit True
                        gefüllt (auch für nicht existierende); das stimmt, wenn
               die IDs aus einer Zope-Mitgliederliste der interessierenden
               Gruppe stammen. Wenn die IDs auch aus einer anderen Quelle
               kommen (z. B. einer Datenbankabfrage), muß dieser Wert
               anschließend noch manuell korrigiert werden!
    """
    ggibi = groupinfo_factory(context, pretty, forlist)
    guibi = userinfo_factory(context, pretty, forlist)

    # ggibi gibt (für Gruppen) keinen title-Schlüssel zurück:
    g_title_key = (pretty and 'pretty_title'
                           or 'group_title')

    def basic_member_info(member_id):
        """
        Basisinformationen über ein "Member" (Benutzer oder Gruppe):
        id, title, type

        Suche zuerst einen Benutzer, dann als Rückfalloption eine Gruppe
        """
        member = guibi(member_id)
        if member is not None:
            member['type'] = 'user'
            return member
        member = ggibi(member_id)
        if member:
            member['type'] = 'group'
            member['title'] = member[g_title_key]
            return member
        else:
            return None  # PEP 20.2

    def bloated_member_info(member_id):
        """
        Gib dict-Objekt zurück wie nach dem Einfügen in
        die Tabelle unitracc_groupmemberships erzeugt
        """
        member = basic_member_info(member_id)
        if member is not None:
            member.update({'member_id_': member_id,
                           'start': None,
                           'ends': None,
                           'active': True,
                           'ismember_zope': True,
                           })
            return member
        elif bloated >= 2:
            return {'id': member_id,
                    'member_id_': member_id,
                    'title': 'not found: %(member_id)s'
                             % locals(),
                    g_title_key: None,
                    'type': None,
                    'ismember_zope': True,
                    'active': None,
                    'start': None,
                    'ends': None,
                    }

    if bloated:
        return bloated_member_info
    else:
        return basic_member_info
# ------------------------------- ] ... memberinfo_factory ]
# ----------------------------------------- ] ... Factory-Funktionen ]

if 0 and 'i18n honeypot':
    _('no group')   # -> voc_get_explicit_group_memberships_for_auth
