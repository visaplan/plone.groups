# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
# UNFERTIG!
"""\
Cache für Gruppenmitgliedschaften

Dieser Cache verfolgt das Ziel, schnellstmöglich eine brauchbare Auskunft zu
liefern.  Es wird daher, sofern möglich, sofort eine Antwort zurückgegeben;
wenn dabei festgestellt wird, daß die Cache-Lebensdauer überschritten wurde,
wird anschließend die Aktualisierung angestoßen, sodaß beim nächsten Request
der aktualisierte Wert zur Verfügung steht.

Achtung:
- Prinzipiell ist es möglich, in einer Zope-Instanz mehrere Plone-Portale zu
  betreiben.  Vorerst ist das bei uns nicht der Fall; insofern können wir etwas
  Performanz herausholen ...
- Insbesondere für den Fall der Umstellung auf ZEO ist zu überlegen, ob der
  Cache zwischen einzelnen Prozessen geteilt werden kann;
  das wäre insbesondere dann wichtig, wenn bei Bearbeitung der
  Gruppenzuordnungen auch die zwischengespeicherten Objekte entsprechend
  manipuliert würden.
"""

# Standardmodule:
from time import time, sleep
from thread import start_new_thread

# -------------------------------------------- [ Daten ... [
CACHE_TIMEOUT = 600  # 600 Sekunden --> 10 Minuten
REVERSE_DICT = None  # <-- .utils.build_groups_reversedict
MEMBERSHIP_DICT = {}
WORKING_THREAD = None
REFRESH_TIMEOUT = 10
# -------------------------------------------- ] ... Daten ]

def get_portal(*args, **kwargs):
    """
    Vorerst unterstützen wir nur *ein* Portal ...
    """
    return 'default'

def refresh_map(sequential=False, **kwargs):
    """
    Aktualisiere die Mitgliedschaftstabelle
    """
    global REVERSE_DICT

# UNFERTIG!
