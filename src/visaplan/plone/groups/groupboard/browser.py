# -*- coding: utf-8 -*- Umlaute: ÄÖÜäöüß
"""
Browser unitracc@@groupboard: Gruppennachrichten
"""
__author__ = "enrico"
__date__ = "$29.04.2013 15:48:48$"
# Standardmodule:
from datetime import datetime
from urllib import quote_plus

# Zope/Plone:
from visaplan.plone.base import BrowserView, implements, Interface

# Unitracc-Tools:
from visaplan.tools.coding import safe_decode
from visaplan.plone.tools.context import message

# Dieser Browser:
from .utils import getsavedkey, make_getUserName
from .crumbs import OK

# Logging und Debugging:
import logging
logger = logging.getLogger('unitracc@@groupboard')


class IGroupBoard(Interface):
    """

    """

    def viewBoard(self):
        """
        generelle Ansicht des Forums
        """

    def newThread(self):
        """
        neues Thema eröffnen
        """

    def replyThread(self, tid=None):
        """
        Antwort auf ein Thema schreiben
        """

    def save(self):
        """
        Neues Thema speichern
        """

    def save_reply(self):
        """
        Speichern einer Antwort
        """

    def get_messages(self, group_id=None, subject_id=None, all=None):
        """
        Hole alle Nachrichten aus der Datenbank.
        Falls Gruppe angegeben nur für Gruppe.
        Falls subject_id angegeben hole Thema für
        antwort ausgabe.
        """

    def get_group_id(self, subject_id):
        """
        Ermittle die Gruppen-ID für den angegebenen Thread
        """

    def editThread(self):
        """
        Einen Thread inklusive Titel bearbeiten
        """

    def delete_thread(self):
        """
        Einen Thread löschen.
        """

    def delete_post(self, mid=None, tid=None, withoutreturn=None):
        """
        Delete a single message
        """


class Browser(BrowserView):
    """

    """
    implements(IGroupBoard)
    # ---------- Funktionen für die Views --------------

    def viewBoard(self):
        """
        Funktion zur Seite;
        gf: templates/board.pt
        """
        context = self.context
        form = context.restrictedTraverse('board')()
        return form

    def newThread(self):
        """
        neues Thema eröffnen
        """
        context = self.context
        gid = context.REQUEST.get('gid', None)
        form = context.restrictedTraverse('new-thread')(group=gid)
        return form

    def replyThread(self):
        """
        Antwort auf ein Thema schreiben
        """
        context = self.context
        tid = context.REQUEST.get('tid', None)
        form = context.restrictedTraverse('thread-reply')(tid=tid)
        return form

    def editThread(self):
        """
        Einen Thread inklusive Titel bearbeiten
        """
        context = self.context
        req = context.REQUEST
        form = req.form
        tid = form.get('tid')
        #Keine Thread id angegeben
        if not tid:
            return
        # Hole Daten
        messages = self.get_messages(subject_id=tid)
        first = messages['first']
        thread = messages['title']
        # Darf den Thread nicht editieren
        if not first['canEdit']:
            return
        form = context.restrictedTraverse('new-thread')(group=thread['group_uid'],
                                                        subject=thread['thread_subject'],
                                                        tid=thread['id'],
                                                        content=first['message'],
                                                        mid=first['id'])
        return form
    # ---- Funktionen für das Holen und aufbereiten der Daten -----

    def get_group_id(self, subject_id):
        """
        Ermittle die Gruppen-ID für den angegebenen Thread
        """
        context = self.context
        with context.getAdapter('sqlwrapper') as sql:
            rows = sql.select('groupboard_thread',
                              query_data={'id': subject_id},
                              maxrows=1)
            for row in rows:
                return row['group_uid']  # eine Id, *keine* UID

    def get_messages(self,  # ------------------- [ get_messages ... [
                     group_id=None, subject_id=None, all=None):
        """
        Hole alle Nachrichten aus der Datenbank.
        Falls Gruppe angegeben nur für Gruppe.
        Falls subject_id angegeben hole Thema für
        antwort ausgabe.
        """
        context = self.context
        getBrowser = context.getBrowser
        author = getBrowser('author')
        me = getBrowser('auth').getId()
        groupsharing = getBrowser('groupsharing')
        result = {}
        read = []
        new = []
        getAdapter = context.getAdapter
        getUserName = make_getUserName(getBrowser=getBrowser)
        with getAdapter('sqlwrapper') as sql:
            # ----------------------------------- ... get_messages ...
            if subject_id:
                where = "WHERE id=%(id)s"
                thread = sql.select(table="groupboard_thread",
                                    where=where,
                                    query_data={'id': subject_id},
                                    maxrows=1)

                # context.REQUEST.response.redirect funktionierte nicht.
                if not thread:
                    message_ = "Zugriffsversuch von %s auf nicht vorhandenes Thema." % me
                    logger.error(message_)
                    return "redirect"

                if not self.has_access(thread[0]['group_uid']):
                    message_ = "ACCESS DENIED \nZugriffsversuch von %s auf Thread  %s." % (me, thread[0])
                    logger.error(message_)
                    return "redirect"

                thread = thread[0]
                thread['group'] = safe_decode(
                        groupsharing.get_group_info_by_id(thread['group_uid'])['group_title'])
                # Hole alle Nachrichten.
                messages = sql.select(table="groupboard_messages",
                                      where="WHERE thread_id=%(thread_id)s order by message_date ASC",
                                      query_data={'thread_id': thread['id']})

                replys = []
                if not all:
                    messages = messages[:30]
                # für alle Nachrichten dasselbe: nur der Board-Manager darf löschen!
                CAN_DELETE = self.can_delete()
                MY_ID = getBrowser('auth').getId()
                for reply in messages:
                    user = getUserName(reply['user_id'])
                    retdate = reply['message_date']
                    canEdit = CAN_DELETE or reply['user_id'] == MY_ID
                    if not isinstance(retdate, datetime):
                        retdate = datetime(retdate._year,
                                           retdate._month,
                                           retdate._day,
                                           retdate._hour,
                                           retdate._minute)
                    saved = retdate.strftime("%d.%m.%Y %H:%M")
                    replys.append({'user': user,
                                   'saved': saved,
                                   'message': safe_decode(reply['message_text']),
                                   'id': reply['id'],
                                   'canEdit': canEdit,
                                   'canDelete': CAN_DELETE,
                                   })
                first_message = replys.pop(0)

                response = {'title': thread,
                            'first': first_message,
                            'replys': replys}
                return response

            # ----------------------------------- ... get_messages ...
            # Hole alle Threads für eine Gruppe
            if group_id:

                if not self.has_access(group_id):
                    message_ = "ACCESS DENIED \nZugriffsversuch von %s auf Gruppenforum  %s." % (me, group_id)
                    logger.error(message_)
                    desktop_path = getBrowser('unitraccfeature').desktop_path()
                    return context.REQUEST.RESPONSE.redirect(desktop_path + '/@@groupboard/viewBoard')

                where = "WHERE group_uid=%(group)s"
                threads = sql.select(table="groupboard_thread",
                                      where=where,
                                      query_data={'group': group_id})
            else:
                # Hole alle Threads in denen ich Gruppenmitglied bin.
                groups = getBrowser('groupdesktop').getInfo()['groups']
                threads = []
                for group in groups:
                    where = "WHERE group_uid=%(group)s"
                    thread = sql.select(table="groupboard_thread",
                                        where=where,
                                        query_data={'group': group['id']})
                    threads.extend(thread)
            delete_right = self.can_delete()

            # ----------------------------------- ... get_messages ...
            for thread in threads:

                # Hole Letzte Nachricht
                WHERE = "WHERE thread_id=%(thread_id)s ORDER by message_date DESC"
                last = sql.select(table="groupboard_messages",
                                  where=WHERE,
                                  query_data={'thread_id': thread['id']},
                                  maxrows=1)
                # Bastel den Nutzer zusammen.
                user = "Anonymous"
                saved = datetime.now().strftime("%d.%m.%Y %H:%M")
                unread = False
                if last:
                    last = last[0]
                    if not last['user_id']:
                        oops = 'No author found'
                        user = 'unknown author'
                        logger.error('groupboard message %s lacks user information', last)
                    else:
                        user = getUserName(last['user_id'])

                    retdate = last['message_date']
                    if not isinstance(retdate, datetime):
                        retdate = datetime(retdate._year,
                                           retdate._month,
                                           retdate._day,
                                           retdate._hour,
                                           retdate._minute)
                    saved = retdate.strftime("%d.%m.%Y %H:%M")
                    # Prüfe auf neue Nachricht
                    message_unread = sql.select(table="groupboard_message_tail",
                                      where="""WHERE message_id=%(message_id)s AND
                                      user_id=%(user_id)s""",
                                      query_data={'message_id': last['id'],
                                                  'user_id': me})

                    if not message_unread:
                        unread = True
                    thread['user'] = user
                    thread['saved'] = saved
                    thread['group'] = safe_decode(
                            groupsharing.get_group_info_by_id(thread['group_uid'])['group_title'])
                    thread['canDelete'] = delete_right
                    if not unread:
                        read.append(thread)
                    else:
                        new.append(thread)

            # XXX Schlüssel 'saved' (formatiertes Datum) ist ein String!
            result['read'] = sorted(read, key=getsavedkey, reverse=True)
            result['new'] = sorted(new, key=getsavedkey, reverse=True)

            return result  # -------------------- ] ... get_messages ]

    def get_message(self, tid, mid):
        if not mid or not tid:
            return
        with self.context.getAdapter('sqlwrapper') as sql:
            message = sql.select('groupboard_messages',
                                 ['user_id', 'message_text'],
                                 "WHERE id=%(mid)s and thread_id=%(tid)s",
                                 {'mid': mid, 'tid': tid},
                                 1)[0]
        if not self.can_edit(message):
            return
        return message['message_text']

    def save(self, subject=None):
        """
        Speichern eines neuen Themas
        """
        context = self.context
        form = context.REQUEST.form
        if form.get('tid'):
            return self.edit_thread()

        group = form.get('group')
        subject = form.get('subject')
        message = form.get('content', '  ')
        boardrules = form.get('boardrules')
        desktop_path = context.getBrowser('unitraccfeature').desktop_path()
        errors = []
        if not group:
            errors.append("1")
        if not subject:
            errors.append("2")
        if not message:
            errors.append("3")
        if not boardrules:
            errors.append("4")

        if errors:
            error = ",".join(errors)
            return context.REQUEST.RESPONSE.redirect(
            '%s/@@groupboard/newThread?error=%s&group=%s&subject=%s&content=%s'
                                                    % (desktop_path,
                                                       error,
                                                       group,
                                                       quote_plus(subject),
                                                       quote_plus(message)))
        with context.getAdapter('sqlwrapper') as sql:
            # Neues Thema Speichern
            values = {'group_uid': group,
                      'thread_subject': subject,
                      }
            # Update eine vorhandenen Themas
            try:
                sql.insert("groupboard_thread", values)
            except:
                print "Thema '%s' bereits vorhanden." % subject

            # Daten für Nachricht zusammenbauen
            now = datetime.now()
            # TH: Vergleich mit Textfeld (!) thread_subject?!
            where = "WHERE group_uid=%(group_uid)s AND thread_subject=%(thread_subject)s"
            tid = sql.select(table="groupboard_thread",
                             fields=['id'],
                             where=where,
                             query_data=values,
                             maxrows=1)[0]['id']
            user_id = context.getBrowser('auth').getId()
            values = {'thread_id': tid,
                      'message_text': message,
                      'message_date': now,
                      }
            values['user_id'] = user_id

            # Die Nachricht speichern
            table = "groupboard_messages"
            sql.insert(table, values)

        # Verweis auf das Gruppenforum für die Gruppe
        # in der das Thema geschrieben wurde
        return context.REQUEST.RESPONSE.redirect('%s/@@groupboard/replyThread?tid=%s'
                                                 % (desktop_path, tid))

    def save_reply(self):
        """
        Speichern einer Antwort
        """
        context = self.context
        desktop_path = context.getBrowser('unitraccfeature').desktop_path()
        subject = context.REQUEST.form['tid']
        message = context.REQUEST.form.get('reply')
        mid = context.REQUEST.form.get('mid')
        boardrules = context.REQUEST.form.get('boardrules', False)
        error = not boardrules
        redirect = context.REQUEST.RESPONSE.redirect
        if error:
            if mid:
                url = ('%s/@@groupboard/replyThread?tid=%s&mid=%s&error=%s'
                       ) % (desktop_path,
                            subject,
                            mid,
                            error)
            else:
                url = ('%s/@@groupboard/replyThread?tid=%s&reply=%s&error=%s'
                       ) % (desktop_path,
                            subject,
                            quote_plus(message),
                            error)
            return redirect(url)
        if not message:
            return redirect('%s/@@groupboard/replyThread?tid=%s&reply=%s'
                            % (desktop_path,
                               subject,
                               quote_plus(message)))
        user_id = context.getBrowser('auth').getId()
        now = datetime.now()
        values = {'thread_id': subject,
                  'message_text': message,
                  }

        # Die Nachricht speichern
        with context.getAdapter('sqlwrapper') as sql:
            table = "groupboard_messages"
            if mid:
                sql.update(table,
                           values,
                           "WHERE id=%(mid)s and thread_id=%(tid)s",
                           context.REQUEST.form)
            else:
                values['user_id'] = user_id
                # TODO: Datums-Standardwert mit SQL realisieren ...
                values['message_date'] = now
                sql.insert(table, values)
        # Redirect auf das Thema

        return redirect('%s/@@groupboard/replyThread?tid=%s'
                        % (desktop_path,
                           subject))

    def mark_as_read(self, message_id):
        """
        Markiert alle Nachrichten eines Threads als
        gelesen.
        """
        context = self.context
        with context.getAdapter('sqlwrapper') as sql:
            me = context.getBrowser('auth').getId()
            table = "groupboard_message_tail"
            where = "WHERE message_id=%(message_id)s and user_id=%(user_id)s"
            values = {'message_id': message_id,
                      'user_id': me,
                      }
            already_seen = sql.select(table, [], where, values)
            if already_seen:
                return

            sql.insert("groupboard_message_tail", values)
        return

    def delete_post(self):
        """
        Einzelnen Post löschen
        """
        context = self.context

        return

    def edit_post(self):
        """
        Einzelnen Post bearbeiten
        """
        context = self.context

        return

    def delete_thread(self):
        """
        Ganzen Thread löschen.
        """
        context = self.context
        thread = context.REQUEST.form.get('tid')

        if not self.can_delete():
            return
        #SQL Adapter
        with context.getAdapter('sqlwrapper') as sql:
            messages = self.get_messages(subject_id=thread, all=True)
            all_messages = []
            all_messages.extend(x for x in messages['replys'])
            all_messages.append(messages['first'])

            query = {'tid': thread}
            for message in all_messages:
                self.delete_post(mid=message['id'],
                                 tid=thread,
                                 withoutreturn=True)
            # delete Thread
            table = "groupboard_thread"
            where = "WHERE id=%(tid)s"
            sql.delete(table, where, query)
        desktop_path = context.getBrowser('unitraccfeature').desktop_path()
        url = "%s/@@groupboard/viewBoard" % desktop_path
        return context.REQUEST.RESPONSE.redirect(url)

    def edit_thread(self):
        """
        Ganzen Thread bearbeiten
        """
        context = self.context
        form = context.REQUEST.form
        group = form.get('group')
        subject = form.get('subject')
        message = form.get('content', '  ')
        _ = context.getAdapter('translate')
        tid = form.get('tid')
        mid = form.get('mid')
        boardrules = form.get('boardrules')
        desktop_path = context.getBrowser('unitraccfeature').desktop_path()
        error = boardrules is None
        url = ('%s/@@groupboard/editThread?tid=%s&mid=%s'
               '&group=%s&subject=%s&content=%s'
               ) % (desktop_path,
                   tid,
                   mid,
                   group,
                   quote_plus(subject),
                   quote_plus(message))
        if not group or not subject or not message or not boardrules:
            return context.REQUEST.RESPONSE.redirect(url + '&error=%s' % error)

        with context.getAdapter('sqlwrapper') as sql:
            group_uid = sql.select("groupboard_thread",
                                   ['group_uid'],
                                   "WHERE id=%(tid)s",
                                   form,
                                   1)[0]['group_uid']
            # Neues Thema Speichern
            values = {'thread_subject': subject,
                      }
            if group != group_uid:
                values['group_uid'] = group
            # Update eine vorhandenen Themas
            where = "WHERE id=%(tid)s"
            try:
                sql.update("groupboard_thread", values, where, form)
            except:
                print "Thema '%s' bereits vorhanden." % subject
                message(context,
                        _("Subject exists already in group."), 'error')
                return context.REQUEST.RESPONSE.redirect(url)

            # Daten für Nachricht zusammenbauen
            values = {'thread_id': tid, 'message_text': message}

            # Die Nachricht speichern
            table = "groupboard_messages"
            where = "WHERE id=%(mid)s and thread_id=%(tid)s"
            sql.update(table, values, where, form)
            # Verweis auf das Thread

        return context.REQUEST.RESPONSE.redirect('%s/@@groupboard/replyThread?tid=%s'
                                                 % (desktop_path, tid))

    def delete_post(self, mid=None, tid=None, withoutreturn=None):
        """
        Delete a single message
        """
        mid = self.context.REQUEST.form.get('id', mid)
        tid = self.context.REQUEST.form.get('tid', tid)
        if not tid or not mid or not self.can_delete():
            return
        with self.context.getAdapter('sqlwrapper') as sql:
            tail_table = "groupboard_message_tail"
            message_table = "groupboard_messages"
            #delete mark as Read
            tail_WHERE = "WHERE message_id=%(mid)s"
            query = {'mid': mid, 'tid': tid}
            sql.delete(tail_table, tail_WHERE, query)
            # Delete messages
            message_WHERE = "WHERE id=%(mid)s and thread_id=%(tid)s"
            sql.delete(message_table, message_WHERE, query)

        if not withoutreturn:
            return self.replyThread()

    def has_access(self, group_id):
        context = self.context
        groups = context.getBrowser('groupdesktop').getInfo()['groups']

        if group_id in [x['id'] for x in groups]:
            return True
        else:
            return False

    def isBoardManager(self, context=None, getAdapter=None):
        """
        Ist der aktive Benutzer ein Board-Manager?
        """
        if getAdapter is None:
            if context is None:
                context = self.context
            getAdapter = context.getAdapter
        return getAdapter('checkperm')('unitracc: Manage Board')

    def can_delete(self, context=None, getAdapter=None):
        """
        Board-Manager dürfen beliebige Forenbeiträge etc. löschen
        """
        return self.isBoardManager(context, getAdapter)

    def can_edit(self, m_object):
        #Prüfe auf Editierrecht
        context = self.context
        if self.isBoardManager(context):
            return True
        me = context.getBrowser('auth').getId()
        # offenbar wird als m_object mal etwas mit 'user_id',
        # mal etwas mit 'user' übergeben ...
        try:
            return me == m_object['user_id']
        except:
            return me == m_object['user']

    def get_guidelines(self):
        """
        Return Guidelines uid for Groupboard
        """
        context = self.context
        feature = context.getBrowser('unitraccfeature')
        return feature.board_guidelines()
