import sqlite3
import time
import datetime
from hashlib import md5
import pickle
import os.path as ospath
from os import system

SCHEMA_VERSION = 2
SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id VARCHAR(32) PRIMARY KEY NOT NULL,
  description VARCHAR(50),
  initial_date DATETIME NOT NULL,
  final_date DATETIME,
  initial_hour DATETIME NOT NULL,
  final_hour DATETIME,
  recurrence INTEGER,
  alert INTEGER,
  cycles INTEGER
);

CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scheduled DATETIME,
  event VARCHAR(32),
  sent BOOLEAN,
  FOREIGN KEY (event) REFERENCES events(id)
);

CREATE TABLE IF NOT EXISTS migrations(
  version INTEGER
);

INSERT into migrations(version) VALUES ('2');
"""


class Database:
    def __init__(self, path=None):
        if path is None:
            path = ospath.join(ospath.abspath(ospath.dirname(__file__)), "planner.sqlite")
        if not ospath.exists(path):
            system("touch {}".format(path))
            tmp = sqlite3.connect(path)
            tmp.executescript(SCHEMA)
            tmp.commit()
            tmp.close()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT version from migrations;")
            assert cursor.fetchone()[0] == SCHEMA_VERSION
        except Exception as e:
            cursor.execute("select 'drop table ' || name || ';' from sqlite_master where type = 'table';")
            self.connection.commit()
            self.connection.executescript(SCHEMA)
            self.connection.commit()

    def new_event(self, event):
        try:
            event['initial_date'] = '-'.join(event['initial_date'].split("/")[::-1])
            event['final_date'] = '-'.join(event['final_date'].split("/")[::-1])
            eid = md5(pickle.dumps(event)).hexdigest()
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO events(id, description, initial_date, final_date, initial_hour, final_hour, "
                           "recurrence, alert, cycles) VALUES (?,?,?,?,?,?,?,?,?);", (eid, event['description'], event['initial_date'],
                                                                          event['final_date'], event['initial_hour'],
                                                                          event['final_hour'], event['recurrence'],
                                                                          event['alert'], event['cycles']))
            if event['alert'] != "0":
                sd = event['initial_date'].split('-')
                sh = event['initial_hour'].split(':')
                d = int(sd[2])
                m = int(sd[1])
                y = int(sd[0])
                H = int(sh[0])
                M = int(sh[1])
                sched = datetime.datetime(y, m, d, H, M) - datetime.timedelta(minutes=abs(int(event['alert'])))
                cursor.execute("INSERT INTO alerts(scheduled, event, sent) VALUES (?,?,?);", (sched, eid, False))
                # if event['recurrence'] ==
            cursor.close()
            self.connection.commit()
            return True
        except Exception as e:
            print(e)
            return False

    def get_events(self):
        pass

    def get_alarms(self):
        pass

    def __del__(self):
        self.connection.close()


if __name__ == '__main__':
    Database()
