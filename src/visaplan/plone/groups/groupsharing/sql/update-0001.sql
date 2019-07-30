BEGIN TRANSACTION;  -- -*- coding: utf-8 -*- äöü
-- SQL-Sichten zur Suche nach fehlerhaft behandelten Scheduler-Einträgen
-- (vorgeplanten Gruppenzuweisungen mit Ende);
-- siehe (gf) ../browser.py, Rev. 16437;
-- Korrekturbefehl in --> update-0002.sql

-- die drei hier erzeugten Sichten:
DROP VIEW IF EXISTS groups_with_memberships_done_but_active_view;
DROP VIEW IF EXISTS members_with_memberships_done_but_active_view;
DROP VIEW IF EXISTS groupmemberships_done_but_active_view;

CREATE VIEW groupmemberships_done_but_active_view AS
  SELECT id,
         group_id_ group_id,
         member_id_ member_id,
         done,
         start,
         ends,
         active
    FROM unitracc_groupmemberships gm
   WHERE done AND active
         AND ends IS NOT NULL AND ends < NOW();

CREATE VIEW groups_with_memberships_done_but_active_view AS
  SELECT group_id,
         count(group_id) cnt
    FROM groupmemberships_done_but_active_view
   GROUP BY group_id
   ORDER BY cnt DESC;

CREATE VIEW members_with_memberships_done_but_active_view AS
  SELECT member_id,
         count(member_id) cnt
    FROM groupmemberships_done_but_active_view
   GROUP BY member_id
   ORDER BY cnt DESC;

END;
