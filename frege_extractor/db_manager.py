import psycopg2
import psycopg2.extras
import logging
from config import DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD


def connect():
    engine = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE,
        user=DB_USERNAME,
        password=DB_PASSWORD
    )
    return engine


class DbManager:

    logger = None
    
    @staticmethod
    def init_logger():
        DbManager.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            fmt='%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S'))
        DbManager.logger.addHandler(handler)
        DbManager.logger.setLevel(logging.WARNING)
        DbManager.logger.propagate = False

    @staticmethod
    def _run_query(query, params):
        """Generic query execution method for all queries that do NOT
        return a result set (insert, update, delete)"""
        connection = connect()
        try:
            cursor = connection.cursor()
            DbManager.logger.info("Success calling database")
            cursor.execute(query, tuple(params))
        except (Exception, psycopg2.DatabaseError) as error:
            DbManager.logger.error("Error in transaction: {}".format(error))
            connection.rollback()
            raise Exception("DbManager Error:", error)
        else:
            connection.commit()
            DbManager.logger.info("Transaction completed successfully")
        finally:
            if connection is not None:
                DbManager.logger.info("Closing connection to database")
                connection.close()

    @staticmethod
    def _run_select_query(query, params):
        """Generic query execution method for all queries that
        return a result set (select)"""
        connection = connect()
        try:
            cursor = connection.cursor()
            DbManager.logger.info("Success calling database")
            cursor.execute(query, tuple(params))
            rs = cursor.fetchall()
        except (Exception, psycopg2.DatabaseError) as error:
            DbManager.logger.error("Error in transaction: {}".format(error))
            raise Exception("DbManager Error:", error)
        else:
            DbManager.logger.info("Transaction completed successfully")
            return rs
        finally:
            if connection is not None:
                DbManager.logger.info("Closing connection to database")
                connection.close()

    @staticmethod
    def select_languages():
        return DbManager._run_select_query("SELECT * FROM languages", [])

    @staticmethod
    def select_repository_languages(repo_id):
        return DbManager._run_select_query(
            "SELECT language_id, id FROM repository_language WHERE repository_id = %s ",
            [repo_id]
        )

    @staticmethod
    def select_repository_by_id(repo_id):
        return DbManager._run_select_query(
            "SELECT * FROM repositories WHERE repo_id = %s",
            [repo_id]
        )

    @staticmethod
    def update_present_repository_languages(repo_id, present_lang_ids):
        DbManager._run_query(
            "UPDATE repository_language SET present='True' "
            "WHERE repository_id = %s AND language_id IN %s",
            [repo_id, tuple(present_lang_ids)]
        )

    @staticmethod
    def insert_repository_languages(repo_id):
        """Inserts repository_language entries for given repo id and ALL languages.
        :return result set of entries: (id, language_id) - id of the inserted entry,
        and id of its language"""
        connection = connect()
        try:
            cursor = connection.cursor()
            DbManager.logger.info("Success calling database")
            query = "INSERT INTO repository_language (repository_id, language_id, present, analyzed)" \
                    "SELECT %s, languages.id, 'False', 'False' FROM languages RETURNING language_id, id"
            cursor.execute(query, (repo_id,))
            rs = cursor.fetchall()
        except (Exception, psycopg2.DatabaseError) as error:
            DbManager.logger.error("Error in transaction: {}".format(error))
            connection.rollback()
            raise
        else:
            connection.commit()
            DbManager.logger.info("Transaction completed successfully")
            return rs
        finally:
            if connection is not None:
                DbManager.logger.info("Closing connection to database")
                connection.close()

    @staticmethod
    def insert_repository_languages_set_present(repo_id, present_lang_ids):
        """Insert repository languages of given repo ID, sets 'present' column to True for
        given present language IDs.
        :returns result set containing IDs of inserted entries and their language IDs"""
        connection = connect()
        try:
            cursor = connection.cursor()
            DbManager.logger.info("Success calling database")
            insert_query = "INSERT INTO repository_language (repository_id, language_id, present, analyzed)" \
                           "SELECT %s, languages.id, 'False', 'False' FROM languages RETURNING language_id, id"
            cursor.execute(insert_query, (repo_id,))
            rs = cursor.fetchall()
            update_query = "UPDATE repository_language SET present='True' " \
                           "WHERE repository_id = %s AND language_id IN %s"
            cursor.execute(update_query, (repo_id, tuple(present_lang_ids)))
            # psycopg2.extras.execute_values(cursor,
            #     "UPDATE repository_language SET present='True' WHERE language")
        except (Exception, psycopg2.DatabaseError) as error:
            DbManager.logger.error("Error in transaction: {}".format(error))
            connection.rollback()
            raise
        else:
            connection.commit()
            DbManager.logger.info("Transaction completed successfully")
            return rs
        finally:
            if connection is not None:
                DbManager.logger.info("Closing connection to database")
                connection.close()

    @staticmethod
    def insert_repository_language_files(entries):
        """Inserts repository_language_file entries"""
        connection = connect()
        try:
            cursor = connection.cursor()
            DbManager.logger.info("Success calling database")
            query = "INSERT INTO repository_language_file (repository_language_id, file_path) VALUES %s"
            psycopg2.extras.execute_values(cursor, query, entries)
        except (Exception, psycopg2.DatabaseError) as error:
            DbManager.logger.error("Error in transaction: {}".format(error))
            connection.rollback()
            raise
        else:
            connection.commit()
            DbManager.logger.info("Transaction completed successfully")
        finally:
            if connection is not None:
                DbManager.logger.info("Closing connection to database")
                connection.close()

    @staticmethod
    def update_repository_language_present(repo_id, lang_id, present=True):
        """Sets 'present' property of a repository_language entry, default True"""
        DbManager._run_query(
            "UPDATE repository_language SET present = %s "
            "WHERE repository_id = %s AND language_id = %s",
            [present, repo_id, lang_id])

    @staticmethod
    def insert_repository_language_file(repo_lang_id, file_path):
        DbManager._run_query(
            "INSERT INTO repository_language_file (repository_language_id, file_path) "
            "VALUES (%s, %s)",
            [repo_lang_id, file_path]
        )
