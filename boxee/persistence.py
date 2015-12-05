import sqlite3
import logging
import traceback

__author__ = 'tamas'

logger = logging.getLogger(__name__)


# http://zetcode.com/db/sqlitepythontutorial/
# http://www.scadacore.com/field-applications/programming-calculators/online-hex-converter
# http://www.binaryhexconverter.com/hex-to-decimal-converter

class PersistenceException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class BoxDao:
    """
    The data access object for the box locker
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

    def fetch_empty_slots(self):
        """
        Returns all the slot ids which are currently empty;\n
        Runs the query: select slot_id from locker where used=F;\n
        :return: the rows found (can be iterated) and referred to by row[0] or row['slot_id']. If nothing found None is returned;
        """
        try:
            self.cursor.execute('SELECT slot_id FROM locker WHERE used=?', 'F')
            self.connection.commit()
            rows = self.cursor.fetchall()
            if len(rows) == 0:
                return None
            else:
                return rows
        except BaseException as e:
            raise PersistenceException(e)

    def fetch_slot_by_barcode(self, barcode):
        """
        Returns the slot_id which contains a parcel identified by barcode
        :param barcode: the barcode which identifies the parcel
        :return: the slot_id which can be than opened
        """
        try:
            self.cursor.execute('SELECT * FROM locker WHERE barcode = ?', barcode)
            self.connection.commit()
            row = self.cursor.fetchone()
            if len(row) > 0:
                logger.debug('fetching by barcode %s with row-size [%s] and slot id [%s]', barcode, len(row),
                             row['slot_id'])
                return row['slot_id']
            else:
                logger.debug('fetching by barcode %s with row-size [%s]. Slot ID: -1 is returned.', barcode, len(row))
                return -1
        except BaseException as e:
            logger.error('could not fetch row by barcode due to: %s', str(e))
            raise PersistenceException(e)

    def update_box(self, slot_id, used=False, barcode=''):
        """
        Updates the slot information (used or not, and if used what is the parcel identifier barcode)
        :param slot_id: the slot in which the parcel will be stored
        :param used: false or true
        :param barcode: the parcel identifier
        :return:
        """
        try:
            logger.debug('updating box with slot id [%s] used [%s] and barcode [%s]', slot_id, used, barcode)
            self.cursor.execute(
                "update slot set used='{0}' where slot_id={1} and barcode='{2}';".format(used, slot_id, barcode))
            self.connection.commit()
        except BaseException as e:
            self.connection.rollback()
            raise PersistenceException(e)

    def destroy(self):
        """
        Closes the connection
        :return:
        """
        logger.info('destroying %s', __name__)
        self.connection.close()

# insert into slot(slot_id, used, barcode) values (18,'T','abrakadabra');
