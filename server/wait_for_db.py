import sys
import MySQLdb
import time
import logging

RETRIES = int(sys.argv[5])
SLEEP_TIME = int(sys.argv[6])

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s [%(module)s] %(message)s')
logger = logging.getLogger("WaitForDB-check")


def main() -> int:
    result = 0
    attempts = 0

    logger.info("Checking if database is ready...")
    while attempts < RETRIES:
        try:
            db = MySQLdb.connect(host=sys.argv[1], user=sys.argv[2],
                                 passwd=sys.argv[3], db=sys.argv[4])
            cursor = db.cursor()
            cursor.execute(sys.argv[7])
            if not cursor.fetchone():
                logger.warning("Database seems to be running, but the query returned no result. Aborting...")
                result = 3
            cursor.close()
            break
        except MySQLdb.OperationalError as e:
            logger.info("Database if not ready yet. Waiting 10 seconds to re-check... ({})".format(attempts + 1))
        except Exception as e:
            logger.error("Unexpected error occurred. Please check the arguments informed. Exception: {}".format(e))
            result = 2
            break

        attempts += 1
        time.sleep(SLEEP_TIME)

    if result < 2:
        if attempts < RETRIES:
            logger.info("Database is ready.")
        else:
            logger.error("Database is not ready after wait for {} seconds.".format(RETRIES * SLEEP_TIME))
            result = 1

    return result


if __name__ == '__main__':
    sys.exit(main())
