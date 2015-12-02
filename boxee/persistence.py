import sqlite3
import logging
import traceback

__author__ = 'tamas'

logger = logging.getLogger(__name__)


class BoxDao:
    """
    """

    def __init__(self, box_range, current_folder):
        self.connection = None
        try:
            logger.info("Creating Box DB at: " + current_folder + "/boxee.db")
            self.connection = sqlite3.connect(current_folder + "/boxee.db")
            self.cursor = self.connection.cursor()
            self.cursor.executescript("""
              create table if not exists locker(id integer primary key autoincrement, slot_id int not null, used char(1) not null, barcode text not null);
              create unique index if not exists unique_slot on locker (slot_id);
              """)
            init_string = ''.join(
                ["insert into locker(slot_id, used, barcode) values (%s,'F','');" % box for box in box_range])
            self.cursor.executescript(init_string)
            self.connection.commit()
        except BaseException as e:
            traceback.print_exc()
            logger.error('Error while initializing database: %s', str(e))
        finally:
            if self.connection:
                self.connection.rollback()
                self.connection.close()

    def update_box(self, slot_id, used=False, barcode=''):
        try:
            logger.debug('updating box with slot id [%s] used [%s] and barcode [%s]', slot_id, used, barcode)
            self.cursor.execute(
                "update slot set used='{0}' where slot_id={1} and barcode='{2}';".format(used, slot_id, barcode))
        except BaseException as e:
            raise e
        finally:
            self.connection.rollback()

    def destroy(self):
        logger.info('destroying %s', __name__)
        self.connection.close()

# insert into slot(slot_id, used, barcode) values (18,'T','abrakadabra');
