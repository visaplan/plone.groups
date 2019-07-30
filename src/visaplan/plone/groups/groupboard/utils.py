# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
utils-Modul für unitracc@@groupboard
"""

# Unitracc-Tools:
from visaplan.plone.tools.log import getLogSupport

# Logging und Debugging:
logger, debug_active, DEBUG = getLogSupport(fn=__file__)

def getsavedkey(dic):
    return dic.get('saved', '')

def make_getUserName(context=None, getBrowser=None):
    if getBrowser is None:
        getBrowser = context.getBrowser
    author = getBrowser('author')

    def getUserName(user_id):
        user_o = author.get(user_id)
        if user_o is None:
            logger.error('Could not find profile of user %(user_id)r', locals())
            return user_id
        liz = []
        val = user_o.getFirstname()
        if val:
            liz.append(val[:1])
        val = user_o.getLastname()
        if val:
            liz.append(val)
        return '. '.join(liz) or user_id

    return getUserName
