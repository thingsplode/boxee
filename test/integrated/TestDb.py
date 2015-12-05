import logging
import boxee.persistence
import sys, os, traceback


__author__ = 'tamas'
logger = logging.getLogger(__name__)


def main(argv):
    dao = None
    try:
        FORMAT = '%(levelname)s - %(module)s.%(funcName)s: %(message)s'
        logging.basicConfig(format=FORMAT)
        current_folder = os.path.dirname(os.path.realpath(sys.argv[0]))
        print ('current folder %s' % current_folder)
        dao = boxee.persistence.BoxDao(range(17, 19), current_folder)
        dao.update_box(17, True, 'one')
        dao.update_box(18, True, 'two')
        slot1 = dao.fetch_slot_by_barcode('one')
        print slot1
        slot2 = dao.fetch_slot_by_barcode('two')
        print slot2
        slot3 = dao.fetch_slot_by_barcode('three')
        print slot3
        dao.update_box(17, False, '')
        dao.update_box(18, False, '')
    except BaseException as e:
        print('Base exception received: %s' % str(e))
        traceback.print_exc()
    finally:
        if dao is not None:
            dao.destroy()


if __name__ == '__main__':
    main(sys.argv[1:])  # chop off the sys.argv[0] which is the name of the script
