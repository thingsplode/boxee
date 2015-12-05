import logging
import boxee.persistence
import sys, os

__author__ = 'tamas'
logger = logging.getLogger(__name__)


def main(argv):
    dao = None
    try:
        FORMAT = '%(levelname)s - %(module)s.%(funcName)s: %(message)s'
        logging.basicConfig(format=FORMAT)
        current_folder = os.path.dirname(os.path.realpath(sys.argv[0]))
        dao = boxee.persistence.BoxDao(range(17, 19), current_folder)
    except BaseException as e:
        print('Base exception received: %s' % str(e))
    finally:
        if dao is not None:
            dao.destroy()


if __name__ == '__main__':
    main(sys.argv[1:])  # chop off the sys.argv[0] which is the name of the script
