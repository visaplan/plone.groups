" vim-Skript:
" Übersetzungs-Strings für neuen Datentyp erzeugen
" Anwendung:
" - browser.py mit vim öffnen
" - neuen Typ am Ende in Singularform anfügen ("nur fuer den Parser"),
"   z. B. "    binary"
" - mit dem Schreibcursor in dieser Zeile ":source new-type.vim" aufrufen

s,^\( *\)\(\w\+\)$,\1# \2:\r\1_('Our \2')\r\1_('Own \2')\r\1_('a \2')\r\1_('Add new \2')\r\1_('Unitracc\u\2')\r\1_('Unitracc\u\2_plural')
" generische Pluralformen (wird mind. eine Variante nicht finden):
%s,^\( *\)\(_('\(Our\|Own\) \w\+[^ys]\)\(')\),\1\2s\4,
%s,^\( *\)\(_('\(Our\|Own\) \w\+\)y\(')\),\1\2ies\4,
