BEGIN TRANSACTION;  -- -*- coding: utf-8 -*- äöü
-- Korrekturbefehl zu --> update-0001.sql

UPDATE unitracc_groupmemberships
   SET done = false
   WHERE done AND active
         AND ends IS NOT NULL AND ends < NOW();
SELECT * FROM groupmemberships_done_but_active_view;
END;
