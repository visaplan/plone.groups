# -*- coding: utf-8 -*- Umlaute: ÄÖÜäöüß

# Zope/Plone:
from visaplan.plone.base import BrowserView, implements, Interface
from Globals import DevelopmentMode

# Unitracc:
from visaplan.plone.base.permissions import ManageGroups, ManageCourses

# Unitracc-Tools:
from visaplan.plone.base.typestr import pluralize
from visaplan.tools.profile import StopWatch
from visaplan.plone.tools.log import getLogSupport
from visaplan.tools.minifuncs import makeBool
from visaplan.tools.minifuncs import gimme_True
from visaplan.plone.infohubs import make_hubs

# Andere Browser und Adapter:
from visaplan.plone.groups.unitraccgroups.utils import LEARNER_SUFFIX, split_group_id

# Dieser Browser:
from .utils import make_authorfilter, make_groupfilter
from .crumbs import OK

# Logging und Debugging:
logger, debug_active, DEBUG = getLogSupport('groupdesktop')
from visaplan.tools.debug import pp
sw_kwargs = {'enable': bool(debug_active),
             }


# ------------------------------------------------------ [ Daten ... [
# TODO: die folgenden beiden Listen sollten inzwischen obsolet sein;
#       prüfen und möglichst entfernen!
STATIC_GROUPS_BLACKLIST = ['group_Author',
                           # nicht zur Bearbeitung, also kein Schreibtisch:
                           'group_academic_accounts',
                           # ... Vortraege Reader:
                           'group_1255c69f5497ffb66ab21dfb9108ec4e_Reader',
                           # HTML-Autoren:
                           'group_1cc0c081bceacc480da7af79f1fb70d4',
                           ]
ANONYMOUS_GROUPS = [
                    # Evaluation Reinigung I Reader (UNITRACC-421):
                    'group_04c187b106643685b2f51201e12d534a',
                    ]
# siehe auch @@groupsharing.BORING_GROUPS
# ------------------------------------------------------ ] ... Daten ]


class IGroupDesktop(Interface):

    def getInfo(self,
                topic=None,
                tid=None,
                portal_type=None,
                get_members=0):
        """
        Gib ein Python-Dictionary zurueck, das interessante
        Informationen fuer den Gruppenschreibtisch enthaelt
        """

    def getLoopDicts(self, gid=None, topic=None, exclude=None):
        """
        Gib Dictionarys fuer group-desktop zurueck
        """

    def getGroupsBlacklist(self):
        """
        Gib die Gruppen zurueck, die *keine* Gruppenschreibtische erzeugen
        """

    def groupProvidesMembers(self, gid):
        """
        Stellt die uebergebene Gruppe ueber ihren Gruppenschreibtisch
        die Visitenkarten ihrer Mitglieder zur Verfuegung?
        """

    def can_view_group_administration(self, group_id, user_id=None):
        """
        Kann Benutzer Gruppenschreibtisch administrieren? ja/nein
        """

    def auth_view_group_administration(self, group_id, user_id=None):
        """
        Kann Benutzer Gruppenschreibtisch administrieren? ja/nein;
        wenn nein -> Unauthorized-Exception
        """

    def set_end_of_group_membership_to_today(self):
        """
        Mitgliedschaft durch Gruppenadministrator beeenden.
        """


class Browser(BrowserView):

    implements(IGroupDesktop)

    @staticmethod
    def isValid(gid):
        """
        Prüfe, ob die übergebene Gruppen-ID sinnvoll erscheint
        """
        if not gid:
            return False
        return gid != 'None'

    def getInfo(self,
                topic=None,
                tid=None,
                portal_type=None,
                get_members=0,
                get_breadcrumbs=0,
                **kwargs):
        """
        Gib ein Python-Dictionary zurueck, das interessante
        Informationen fuer den Gruppenschreibtisch enthaelt

        Argumente:
        topic -- wenn uebergeben, wird getLoopDicts aufgerufen

        tid -- die ID des aufrufenden Templates.

        portal_type -- fuer Breadcrumbs; nur verwendet, wenn tid
                       uebergeben

        get_members -- wenn True, werden die Gruppenmitglieder ermittelt

        get_breadcrumbs -- wenn True, werden die Brotkruemel erzeugt

        hub, info -- z. B. aus Browser-Aufruf hubandinfo.get
                     (derzeit nur als benannte Argumente;
                     beide oder keins von beiden übergeben!)

        Schluessel des Dictionarys:

        gid -- die Gruppen-ID, wenn im Request enthalten
               (ansonsten None)

        groups -- alle Gruppen des angemeldeten Benutzers, als Dictionarys
                  (wie von @@groupsharing.get_groups_by_user_id
                  zurueckgegeben)

        current -- der Kruemel fuer die ausgewaehlte Gruppe
                   (wenn gid nicht None)

        desktopurl -- die URL des Gruppenschreibtischs (ohne Argumente)

        baseurl -- die URL zum Anhaengen von Methodennamen

        members -- die Gruppenmitglieder als Sequenz von Dictionarys

        strings -- wenn topic uebergeben, das Ergebnis von
                   self.getLoopDicts(..., topic) (das in diesem Fall ein einzelnes
                   dict zurueckgibt, keine Sequenz)
        """
        with StopWatch('@@groupdesktop.getInfo',
                       **sw_kwargs) as stopwatch:
            context = self.context
            hub = kwargs.pop('hub', None)
            info = kwargs.pop('info', None)
            if hub is None:
                assert info is None
                hub, info = make_hubs(context)
            else:
                assert info is not None
            hub['authorized'].raiseAnon()

            rc = hub['rc']

            request = context.REQUEST
            form = request.form
            gid = info['gid']
            subpages = None
            user_id = info['user_id']

            if debug_active:
                DEBUG('getInfo(topic=%r, tid=%r, portal_type=%r, get_members=%r)',
                        topic, tid, portal_type, get_members)
            if tid is not None:
                assert tid, 'Template-ID muss None oder nicht-leer sein (%r)' % (tid,)
            stopwatch.lap('Vorbereitungen')

            # aus dem 'topic' laesst sich alles ableiten:
            if topic is not None:
                strings = self.getLoopDicts(gid, topic)
                if tid is None:
                    tid = strings['page']
                if portal_type is None:
                    portal_type = strings['portal_type']
            else:
                strings = None

            if 0 and 'devel':
                import pdb
                pdb.set_trace()
            _ = mogrify = hub['translate']

            baseurl = hub['unitraccfeature'].desktop_path()

            # wird von getGroups gefüllt:
            current = {}
            courses = []
            # groups: Gruppen für die Schreibtischauswahl
            #         Es dürfen nur Gruppen ausgegeben werden ...
            #         - deren Schreibtisch-Flag aktiv ist
            #         - zu denen eine *direkte* Mitgliedschaft besteht
            #         - (um die Auswahl des pers. Schreibtischs jedenfalls
            #           funktional zu machen:) Die aktuell gewählte Gruppe
            stopwatch.lap('Kurse und Gruppen besorgen ...')
            courses, dt_groups = \
                    hub['groupsharing'].get_courses_and_desktop_groups(
                            user_id, gid or None)
            stopwatch.lap('Kurse und Gruppen')
            if 0:
                pp((('courses:', courses),
                    ('dt_groups:', dt_groups),
                    ))
            for dic in dt_groups:
                if dic['id'] == gid:
                    # nicht einfach zuweisen, wg. pot. Änderung:
                    current.update(dic)
                if dic['group_manager'] == user_id:
                    dic['group_title'] = _('${group_title} (Group manager)',
                                           mapping=dic)
            stopwatch.lap('Gruppentitel')

            members = []  # ... der Gruppe <gid>
            # nur 'natuerliche Personen', also keine Gruppen:
            if (get_members
                and gid is not None
                # Desktop-Flag -> Mitglieder werden ausgegeben:
                and current.get('group_desktop')
                ):
                memberids = []
                gsle = hub['author'].getShortListEntry
                for brain in self.getGroupMembers(gid, user_id):
                    try:
                        member = gsle(brain)
                    except (KeyError, AttributeError, TypeError) as e:
                        logger.error('getInfo, brain=%(brain)r:' % locals())
                        logger.exception(e)
                        if brain is not None:
                            try:
                                dic = dict(brain)
                            except Exception:
                                logger.error('(leider keine dict-Darstellung verfuegbar)')
                            else:
                                logger.error('... dict(brain) = %(dic)s', locals())
                        continue
                    if not member['name']:
                        if member['id'].startswith('unitraccauthor.'):
                            logger.error('Karteileiche: User %(id)r', member)
                            continue
                        elif member['id']:
                            logger.error('Benutzer %(id)r hat keinen Namen', member)
                            member['name'] = member['id']
                    if member in members:
                        continue
                    elif member['id'] in memberids:
                        logger.error('Doppelter Benutzer "%(id)s"!', member)
                        continue
                    memberids.append(member['id'])
                    members.append(member)
                stopwatch.lap('Mitgliederliste')

            rslt = {'groups': dt_groups,
                    'members': members,
                    'current': current or None,
                    'gid': gid,
                    'calendar': gid
                    and {'url': '%(baseurl)s/our-calendar?gid=%(gid)s' % locals(),
                         'label': 'Group calendar',
                         }
                    or  {'url': '%(baseurl)s/my-calendar' % locals(),
                         'label': 'My calendar',
                         },
                    'userid': user_id,
                    'desktopurl': baseurl,
                    'baseurl': baseurl,
                    'devmode': DevelopmentMode,
                    'verbose': DevelopmentMode and makeBool(form.get('verbose', 'no')),
                    'strings': strings,
                    'courses': courses,
                    'info': info, # aus make_hubs-Aufruf
                    }
            return rslt

    def getGroupMembers(self, groupId, myId=None):
        """
        Gib alle Mitglieder der Gruppe mit der uebergebenen ID zurueck,
        die ihre Visitenkarte freigeschaltet haben
        (Katalogsuche; es kommen also Brains zurueck)

        groupId -- die ID der interessierenden Gruppe

        myId -- die ID des aktiven Users (optional)
        """
        context = self.context

        groups = context.getBrowser('groups')
        groupo = groups.getById(groupId)
        if not groupo:
            return []
        # erst die IDs der Gruppenmitglieder ...
        mids = groupo.getMemberIds()
        if not mids:
            return []
        if myId is None:
            myId = context.getBrowser('auth').getId()
        if myId in mids:
            pass
        else:
            checkperm = context.getAdapter('checkperm')
            if not checkperm(ManageGroups):
                logger.info('User %r nicht in Gruppe, keine Perm. "Manage Groups"'
                            % (myId,))
                return []
        query = {'getExcludeFromNav': False,
                 'portal_type': 'UnitraccAuthor',
                 'Creator': mids,
                 }
        pc = context.getAdapter('puc')()
        rslt = pc(query)
        return rslt

    def getLoopDicts(self, gid=None, topic=None, exclude=None):
        """
        Gib eine Sequenz von Dictionarys fuer group-desktop zurueck
        (oder ein einzelnes).

        Argumente:

            gid -- eine Gruppen-ID; wenn nicht angegeben, ist der private
                   Schreibtisch gemeint, und es wird ein Filter fuer den
                   aktuell angemeldeten Benutzer erzeugt

            topic -- z. B. 'event', korrespondierend mit 'UnitraccEvent'.
                     Wenn angegeben, wird ein einzelnes Dictionary
                     zurueckgegeben, ansonsten eine Sequenz aller auf dem
                     Schreibtisch aufzulistender Typen.

            exclude -- einzelne Topics, die aus der Sequenz herausgelassen werden
                       (weil sie z. B. nicht verlinkt, sondern explizit
                       eingebunden werden)

        Schluessel des/der Dictionarys (siehe Funktion mkdict):

            filter -- eine Liste von Kriterien fuer die Suche

            portal_type -- z. B. UnitraccImage

            text -- lokalisiert, z. B. "Unsere Bilder"

            page -- relative Seitenangabe

            thingies -- Pluralform fuer den portal_type, z. B. "Bilder"
        """
        context = self.context
        # "mogrify" wird vom Parser ignoriert:
        mogrify = self.context.getAdapter('translate')
        if gid and gid != 'None':  # self.isValid(gid):
            # Gruppe wird dann durch weiteres Argument gefiltert
            mkfilter = make_groupfilter(gid)
        else:
            # wenn nix Gruppe, dann *eigener* Schreibtisch
            userid = context.getAdapter('auth')().getId()
            mkfilter = make_authorfilter(userid)

        # CHECKME: kann hier das typestr-Modul zur Vereinfachung eingesetzt werden?
        def mkmytup(sing):
            """
            Tupel-Factory fuer 'Eigene Artikel'
            """
            plu = pluralize(sing)
            return ('Unitracc%s' % sing.capitalize(),  # --> pt (portal_type)
                    'my-%s' % plu,                     # --> page
                    mogrify('Own %s' % plu),           # --> text
                    sing,
                    plu,
                    )

        def mkourtup(sing):
            """
            Tupel-Factory fuer 'Unsere Artikel'
            """
            plu = pluralize(sing)
            return ('Unitracc%s' % sing.capitalize(),  # --> pt
                    'our-%s' % plu,                    # --> page
                    mogrify('Our %s' % plu),           # --> text
                    sing,
                    plu,
                    )

        def mkdict(pt, page, text, sing, plu):
            msgid = 'own_%(plu)s_desc'
            msgstr = mogrify(msgid)
            return {'portal_type': pt,
                    'thingy': mogrify(pt),
                    'thingies': mogrify('%s_plural' % pt),
                    'a_thingy': mogrify('a %s' % sing),
                    'filter': mkfilter(pt),  # ['portal_type=...']
                    'page': page,  # zb 'our-articles'
                    'text': text,  # zb 'Unsere Artikel'
                    'add_url': '/@@temp/add%s' % sing.capitalize(),
                    'add_text': mogrify('Add new %s' % sing),
                    'editorial_hint': (msgstr and msgstr != msgid)
                                      and msgstr  # spez. Text vorhanden
                                      or None,    # generische Version verw.
                    }
        if gid is None:
            mktup = mkmytup
        else:
            mktup = mkourtup
        if topic is not None:
            return mkdict(*mktup(topic))
        return [mkdict(*mktup(word))
                for word in (
                    'news',
                    'article',
                    'event',
                    'image',
                    'table',
                    'glossary',
                    'literature',
                    'formula',
                    'standard',
                    'animation',
                    'video',
                    'audio',
                    'course',
                    'binary',
                    )
                if not exclude
                   or word not in exclude
                ]

    # siehe STATIC_GROUPS_BLACKLIST, ANONYMOUS_GROUPS
    def getGroupsBlacklist(self):
        """
        Gib die Gruppen zurueck, die *keine* Gruppenschreibtische erzeugen
        """
        context = self.context
        unitraccgroups = context.getBrowser('unitraccgroups')
        mycontent = context.getBrowser('mycontent')
        gag = unitraccgroups.generateAssociatedGroups
        rslt = list(STATIC_GROUPS_BLACKLIST)
        for uid in mycontent.getBlacklist():
            rslt.extend(gag(uid))
        return rslt

    def groupProvidesMembers(self, gid):
        """
        Stellt die uebergebene Gruppe ueber ihren Gruppenschreibtisch
        die Visitenkarten ihrer Mitglieder zur Verfuegung?
        """
        if gid in ANONYMOUS_GROUPS:
            return False
        else:
            return gid not in self.getGroupsBlacklist()

    @staticmethod
    def makeTopic(portal_type):

        if portal_type.startswith('Unitracc'):
            return portal_type[8:].lower()
        return portal_type

    def can_view_group_administration(self, group_id, user_id=None):
        context = self.context

        checkperm = context.getAdapter('checkperm')
        if checkperm(ManageGroups):
            return True

        groupbrowser = context.getBrowser('groups')

        group = groupbrowser.getById(group_id)

        if not user_id:
            user_id = str(context.getAdapter('auth')())

        if group and group.getProperty('group_manager') == user_id:
            return True

    def _make_group_administration_checker(self, context=None, user_id=None):
        """
        Erzeuge eine Funktion, die überprüft, ob der angemeldete Benutzer die
        übergebene Gruppe administrieren darf.
        """
        if context is None:
            context = self.context

        getAdapter = context.getAdapter
        checkperm = getAdapter('checkperm')
        if checkperm(ManageGroups):
            return gimme_True

        cm = checkperm(ManageCourses)

        groupbrowser = context.getBrowser('groups')
        if not user_id:
            user_id = str(getAdapter('auth')())

        def can_administrate(group_id, user_id=user_id):
            if not user_id:
                user_id = str(getAdapter('auth')())

            if not user_id:
                return False

            group = groupbrowser.getById(group_id)
            if group and group.getProperty('group_manager') == user_id:
                return True
            if cm:
                dic = split_group_id(group_id)
                if dic['role'] == 'learner':
                    return True

            return False

        return can_administrate

    def auth_view_group_administration(self, group_id, user_id=None):

        if not self.can_view_group_administration(group_id=group_id, user_id=user_id):
            context = self.context
            context.getBrowser('tpcheck').unauthorized()

    def set_end_of_group_membership_to_today(self):
        """
        Mitgliedschaft durch Gruppenadministrator beeenden.
        """
        context = self.context
        gs = context.getBrowser('groupsharing')
        desktop_path = context.getBrowser('unitraccfeature').desktop_path()
        return gs._end_group_memberships('user_id', 'gid',
                                        path='/'.join((desktop_path,
                                                       'group_administration_user_view',
                                                       )),
                                        varnames=['gid',
                                                  ])


if 0 and 'nur fuer den Parser':
    _('UnitraccArticle', 'Article')  # vim-Suche: thingy
    _('UnitraccAuthor', 'Author')    # nicht in typestr-Modul
    _('UnitraccContact', 'Contact')  # nicht in typestr-Modul
    _('UnitraccCourse', 'Course')
    _('UnitraccEvent', 'Event')
    _('UnitraccFile', 'File')  # nicht in typestr-Modul
    _('UnitraccFormula', 'Formula')
    _('UnitraccGlossary', 'Lexicon entry')
    _('UnitraccImage', 'Image')
    _('UnitraccLiterature', 'Literature reference')
    _('UnitraccNews', 'News')
    _('UnitraccStandard', 'Standard')
    _('UnitraccTable', 'Table')
    _('UnitraccAnimation', 'Animation')
    _('UnitraccAudio', 'Audio file')
    _('UnitraccVideo', 'Video')
    _('UnitraccArticle_plural', 'Articles')  # vim-Suche: s_plural
    _('UnitraccAuthor_plural', 'Authors')
    _('UnitraccContact_plural', 'Contacts')
    _('UnitraccCourse_plural', 'Courses')
    _('UnitraccEvent_plural', 'Events')
    _('UnitraccFile_plural', 'Files')
    _('UnitraccFormula_plural', 'Formulas')
    _('UnitraccGlossary_plural', 'Lexicon entries')
    _('UnitraccImage_plural', 'Images')
    _('UnitraccLiterature_plural', 'Literature references')
    _('UnitraccNews_plural', 'News')
    _('UnitraccStandard_plural', 'Standards')
    _('UnitraccTable_plural', 'Tables')
    _('UnitraccAnimation_plural', 'Animations')
    _('UnitraccAudio_plural', 'Audio files')
    _('UnitraccVideo_plural', 'Videos')
    # 'Our news' etc. muss jeweils komplett uebersetzt werden,
    # weil z. B. im Spanischen (wie in allen romanischen Sprachen)
    # das 'Our' je nach gramm. Geschlecht des Bestimmungsworts
    # unterschiedlich ausfaellt.
    # Suchen nach 'mogrify' (was der Parser ignoriert und das auch soll):
    _('Our news')
    _('Our articles')
    _('Our events')
    _('Our images')
    _('Our tables')
    _('Our glossaries', 'Our lexicon entries')
    _('Our formulas')
    _('Our standards')
    _('Our courses')
    _('Our files')
    _('Our animations')
    _('Our videos')
    _('Our audios', 'Our audio files')
    # auch die werden hier verwendet:
    _('Own news')
    _('Own articles')
    _('Own events')
    _('Own images')
    _('Own tables')
    _('Own glossaries', 'Own lexicon entries')
    _('Own formulas')
    _('Own standards')
    _('Own courses')
    _('Own files')
    _('Own animations')
    _('Own videos')
    _('Own audios', 'Own audio files')
    # generische (!) Strings:
    _('a news')
    _('a article', 'an article')
    _('a event', 'an event')
    _('a image', 'an image')
    _('a table')
    _('a glossary', 'a lexicon entry')
    _('a formula')
    _('a standard')
    _('a course')
    _('a file')
    _('a animation', 'an animation')
    _('a video')
    _('a audio', 'an audio file')
    _('Add new news')
    _('Add new article')
    _('Add new event')
    _('Add new image')
    _('Add new table')
    _('Add new glossary', 'Add new lexicon entry')
    _('Add new formula')
    _('Add new standard')
    _('Add new course')
    _('Add new file')
    _('Add new animation')
    _('Add new video')
    _('Add new audio', 'Add new audio file')
    # (noch?) nicht verwendet:
    x_('a author')
    x_('a contact')
    x_('a file')
    x_('Add new author')
    x_('Add new contact')
    x_('Add new file')
    # *** see -> source new-type.vim:
    # binary:
    _('Our binaries')
    _('Own binaries')
    _('a binary')
    _('Add new binary')
    _('UnitraccBinary', 'Binary')
    _('UnitraccBinary_plural', 'Binaries')

# vim: ts=8 sts=4 sw=4 si et hls
