# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName

from visaplan.plone.base import BrowserView, implements, Interface
from .utils import (STRUCTURE_GROUP_SUFFIXES,
        generic_group_id, split_group_id,
        )

class IUnitraccGroups(Interface):

    def getStructureGroupPrefixes():
        """
        Gib die "Praefixe" (eigentlich natuerlich Suffixe) zurueck,
        die fuer die assoziierten Gruppen der Strukturelemente
        verwendet werden
        """

    def buildStructureGroupName(uid, prefix):
        """
        Gib die generische Gruppen-ID für die übergebene UID und das übergeben Suffix zurück;
        siehe auch .utils.learner_group_id().
        """

    def generateAssociatedGroups(uid):
        """
        erzeuge alle assoziierten Gruppennamen fuer
        die uebergebene UID
        """


class Browser(BrowserView):

    implements(IUnitraccGroups)

    @staticmethod
    def getStructureGroupPrefixes():
        # zum Finden: _Reader, _Author
        # auch hartcodiert in @@mycontent.isReaderGroupID:
        return STRUCTURE_GROUP_SUFFIXES

    @staticmethod
    def buildStructureGroupName(uid, prefix):
        """
        Gib die generische Gruppen-ID für die übergebene UID und das übergeben Suffix zurück;
        siehe auch .utils.learner_group_id().
        """
        return generic_group_id(uid, prefix)

    @staticmethod
    def generateAssociatedGroups(uid):
        """
        erzeuge alle assoziierten Gruppennamen fuer
        die uebergebene UID
        """
        for suff in STRUCTURE_GROUP_SUFFIXES:
            yield generic_group_id(uid, suff)

    @staticmethod
    def splitGroupID(gid):
        """
        Splitte die übergebene Gruppen-ID auf und gib ein Dictionary zurück.

        Die Schlüssel 'uid' und 'role' haben String-Werte,
        sofern der Mittelteil wie eine korrekte UID aussieht und das Suffix
        eine der hierfür bekannten Rollen ist;
        ansonsten sind sie None.
        """
        return split_group_id(gid)

    def groupInfo(self, gid):
        """
        Ergänze die Gruppeninformationen aus splitGroupID durch den
        Gruppentitel; gib ein Dictionary mit den Schlüsseln
        'uid', 'role', 'group_id' und 'title' zurück.

        Siehe auch @@groupsharing.get_group_info_by_id
        """
        dic = split_group_id(gid)
        dic['group_id'] = gid
        context = self.context
        acl = getToolByName(context, 'acl_users')
        dic['title'] = acl.source_groups._groups[gid]['title']
        return dic


# vim: ts=8 sts=4 sw=4 si et
