-- unitracc@groupboard: update-0001.sql -*- coding: utf-8 -*- äöü
BEGIN TRANSACTION;

CREATE INDEX groupboard_messages__message_date__index
          ON groupboard_messages (message_date);
CREATE INDEX groupboard_messages__thread_id__index
          ON groupboard_messages (thread_id);
END;
