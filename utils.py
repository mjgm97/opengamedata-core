## @namespace utils
#  A module of utility functions used in the feature_extraction_to_csv project
import datetime
import http
import json
import logging
import math
import MySQLdb
import os
import sshtunnel
import traceback
import typing
from config import settings
from google.cloud import bigquery

## Function to open a given JSON file, and retrieve the data as a Python object.
#  @param filename  The name of the JSON file. If the file extension is not .json,
#                       then ".json" will be appended.
#  @param path      The path (relative or absolute) to the folder containing the
#                       JSON file. If path does not end in /, then "/" will be appended.
#  @return          A python object parsed from the JSON.
def loadJSONFile(filename: str, path:str = "./") -> object:
    if not filename.lower().endswith(".json"):
        Logger.toStdOut(f"Got a filename that didn't end with .json: {filename}, appending .json", logging.DEBUG)
        filename = filename + ".json"
    if not path.endswith("/"):
        path = path + "/"
    ret_val = None
    try:
        json_file = open(path+filename, "r")
        ret_val = json.loads(json_file.read())
        json_file.close()
    except Exception as err:
        Logger.toStdOut(f"Could not read file at {path+filename}\nFull error message: {str(err)}\nCurrent directory: {os.getcwd()}",
                        logging.ERROR)
        raise err
    return ret_val

## Function that converts a datetime object into a filename-friendly format.
#  Yes, there is undoubtedly a built-in way to do this, but this is what I've got.
#  @param date  The datetime object to be formatted.
#  @return      Formatted string representing a date.
def dateToFileSafeString(date: datetime.datetime):
    return f"{date.month}-{date.day}-{date.year}"

## Dumb struct to collect data used to establish a connection to a SQL database.
class SQLLogin:
    def __init__(self, host: str, port: int, user: str, pword: str, db_name: str):
        self.host    = host
        self.port    = port
        self.user    = user
        self.pword   = pword
        self.db_name = db_name

## Dumb struct to collect data used to establish a connection over ssh.
class SSHLogin:
    def __init__(self, host: str, port: int, user: str, pword: str):
        self.host    = host
        self.port    = port
        self.user    = user
        self.pword   = pword

## @class SQL
#  A utility class containing some functions to assist in retrieving from a database.
#  Specifically, helps to connect to a database, make selections, and provides
#  a nicely formatted 500 error message.
class SQL:
    ## Function to set up a connection to a database, via an ssh tunnel if available.
    #  @return A tuple consisting of the tunnel and database connection, respectively.
    @staticmethod
    def prepareDB(db_settings, ssh_settings, bigquery_settings=None, use_bigquery = False) -> typing.Tuple[object, object]:
        if use_bigquery:
            Logger.toStdOut("We're preparing database with bigquery.", logging.INFO)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = bigquery_settings["CREDENTIAL_PATH"]
            try:
                client = bigquery.Client()
                return (None, client)
            except:
                Logger.toStdOut("Could not connect with bigquery.", logging.INFO)
        # Load settings, set up consts.
        DB_NAME_DATA = db_settings["DB_NAME_DATA"]
        DB_USER = db_settings['DB_USER']
        DB_PW = db_settings['DB_PW']
        DB_HOST = db_settings['DB_HOST']
        DB_PORT = db_settings['DB_PORT']
        SSH_USER = ssh_settings['SSH_USER']
        SSH_PW = ssh_settings['SSH_PW']
        SSH_HOST = ssh_settings['SSH_HOST']
        SSH_PORT = ssh_settings['SSH_PORT']

        # set up other global vars as needed:
        sql_login = SQLLogin(host=DB_HOST, port=DB_PORT, user=DB_USER, pword=DB_PW, db_name=DB_NAME_DATA)
        Logger.toStdOut("We're preparing database.", logging.INFO)
        if (SSH_HOST != "" and SSH_USER != "" and SSH_PW != ""):
            Logger.toStdOut(f"Setting up ssh host connection.", logging.INFO)
            ssh_login = SSHLogin(host=SSH_HOST, port=SSH_PORT, user=SSH_USER, pword=SSH_PW)
            tunnel,db_cursor = SQL.connectToMySQLViaSSH(sql=sql_login, ssh=ssh_login)
        else:
            Logger.toStdOut("Skipping SSH part of login.", logging.INFO)
            db_cursor = SQL.connectToMySQL(login=sql_login)
            tunnel = None
        return (tunnel, db_cursor)

    ## Function to help connect to a mySQL server.
    #  Simply tries to make a connection, and prints an error in case of failure.
    #
    #  @param host      The name of the database host server.
    #  @param port      The database server port to which we want to connect.
    #  @param user      Username for connecting to the database.
    #  @param password  The given user's password.
    #  @param database  The actual name of the database on the host.
    #  @return          An open connection to the database if successful,
    #                       otherwise None.
    @staticmethod
    def connectToMySQL(login: SQLLogin):
        try:
            return MySQLdb.connect(host = login.host, port = login.port,
                                           user = login.user, password = login.pword,
                                           database = login.db_name, charset='utf8')
        except MySQLdb.connections.Error as err:
            Logger.toStdOut(f"Could not connect to the MySql database: " + str(err), logging.ERROR)
            Logger.toPrint(f"Could not connect to the MySql database: {str(err)}", logging.ERROR)
            traceback.print_tb(err.__traceback__)
            return None

    ## Function to help connect to a mySQL server over SSH.
    #  Simply tries to make a connection, and prints an error in case of failure.
    #
    #  @param host      The name of the database host server.
    #  @param port      The database server port to which we want to connect.
    #  @param user      Username for connecting to the database.
    #  @param password  The given user's password.
    #  @param database  The actual name of the database on the host.
    #  @return          An open connection to the database if successful,
    #                       otherwise None.
    @staticmethod
    def connectToMySQLViaSSH(sql: SQLLogin, ssh: SSHLogin):
        try:
            tunnel = sshtunnel.SSHTunnelForwarder(
                (ssh.host, ssh.port), ssh_username=ssh.user, ssh_password=ssh.pword,
                remote_bind_address=(sql.host, sql.port), logger=Logger.std_logger
            )
            tunnel.start()
            Logger.toStdOut(f"Connected to SSH at {ssh.host}:{ssh.port}, {ssh.user}", logging.INFO)
            conn = MySQLdb.connect(host = sql.host, port = tunnel.local_bind_port,
                                           user = sql.user, password = sql.pword,
                                           database = sql.db_name, charset='utf8')
            Logger.toStdOut(f"Connected to SQL at {sql.host}:{sql.port}/{sql.db_name}, {sql.user}", logging.INFO)
            return (tunnel, conn)
        except Exception as err:
            Logger.toStdOut("Could not connect to the MySql database: " + str(err), logging.ERROR)
            Logger.toPrint(f"Could not connect to the MySql database {str(err)}", logging.ERROR)
            if tunnel is not None:
                tunnel.stop()
            return (None, None)

    @staticmethod
    def disconnectMySQLViaSSH(tunnel, db):
        if db is not None:
            db.close()
            Logger.toStdOut("Closed database connection", logging.INFO)
        else:
            Logger.toStdOut("No db to close.", logging.INFO)
        if tunnel is not None:
            tunnel.stop()
            Logger.toStdOut("Stopped tunnel connection", logging.INFO)
        else:
            Logger.toStdOut("No tunnel to stop", logging.INFO)



    ## Function to build and execute SELECT statements on a database connection.
    #  @param cursor        A database cursor, retrieved from the active connection.
    #  @param db_name       The name of the database to which we are connected.
    #  @param table         The name of the table from which we want to make a selection.
    #  @param columns       A list of columns to be selected. If empty (or None),
    #                           all columns will be used (SELECT * FROM ...).
    #                           Default: None
    #  @param filter        A string giving the constraints for a WHERE clause.
    #                           (The "WHERE" term itself should not be part of the filter string)
    #                           Default: None
    #  @param limit         The maximum number of rows to be selected. Use -1 for no limit.
    #                           Default: -1
    #  @param sort_columns  A list of columns to sort results on. The order of columns
    #                           in the list is the order given to SQL
    #                           Default: None
    #  @param sort_direction The "direction" of sorting, either ascending or descending.
    #                           Default: "ASC"
    #  @param grouping      A column name to group results on. Subject to SQL rules for grouping.
    #                           Default: None
    #  @param distinct      A bool to determine whether to select only rows with
    #                           distinct values in the column.
    #                           Default: False
    #  @param distinct      A bool to determine whether all results should be fetched and returned.
    #                           Default: True
    #  @return              A collection of all rows from the selection, if fetch_results is true,
    #                           otherwise None.
    @staticmethod
    def SELECT(cursor, db_name: str, table:str, columns: typing.List[str] = None, filter: str = None, limit: int = -1,
               sort_columns: typing.List[str] = None, sort_direction = "ASC", grouping: str = None,
               distinct: bool = False, fetch_results: bool = True, use_bigquery: bool = False) -> typing.List[typing.Tuple]:
        query = SQL._prepareSelect(db_name=db_name, table=table, columns=columns, filter=filter, limit=limit,
                                   sort_columns=sort_columns, sort_direction=sort_direction, grouping=grouping,
                                   distinct=distinct)
        return SQL.SELECTfromQuery(cursor=cursor, query=query, fetch_results=fetch_results, use_bigquery=use_bigquery)
    @staticmethod
    def SELECTfromQuery(cursor, query: str, fetch_results: bool = True, use_bigquery=False) -> typing.List[typing.Tuple]:

        with_bigquery = " with bigquery" if use_bigquery else "without bigquery"
        Logger.toStdOut(f"Running query{with_bigquery}: " + query, logging.INFO)

        # print(f"running query: {query}")
        start = datetime.datetime.now()
        if not use_bigquery:
            cursor.execute(query)
            query_job = None
        else:
            query_job = cursor.query(query)
        time_delta = datetime.datetime.now()-start
        num_min = math.floor(time_delta.total_seconds()/60)
        num_sec = time_delta.total_seconds() % 60
        Logger.toStdOut(f"Query execution completed, time to execute: {num_min:d} min, {num_sec:.3f} sec", logging.INFO)
        # print("Query execution completed, time to execute: {:d} min, {:.3f} sec".format( \
        #     math.floor(time_delta.total_seconds()/60), time_delta.total_seconds() % 60 ) \
        # )
        if not use_bigquery:
            result = cursor.fetchall() if fetch_results else None
            num_results = len(result)
        else:
            result = query_job.result() if fetch_results else None
            num_results = result.total_rows
        time_delta = datetime.datetime.now()-start
        num_min = math.floor(time_delta.total_seconds()/60)
        num_sec = time_delta.total_seconds() % 60
        Logger.toStdOut(f"Query fetch completed, total query time:    {num_min:d} min, {num_sec:.3f} sec to get {num_results:d} rows", logging.INFO)
        # print("Query fetch completed, total query time:    {:d} min, {:.3f} sec to get {:d} rows".format( \
        #     math.floor(time_delta.total_seconds()/60), time_delta.total_seconds() % 60, len(result) ) \
        # )
        return result

    @staticmethod
    def _prepareSelect(db_name: str, table:str, columns: typing.List[str] = None, filter: str = None, limit: int = -1,
               sort_columns: typing.List[str] = None, sort_direction = "ASC", grouping: str = None,
               distinct: bool = False):
        d = "DISTINCT " if distinct else ""
        cols      = ",".join(columns)      if columns is not None      and len(columns) > 0      else "*"
        sort_cols = ",".join(sort_columns) if sort_columns is not None and len(sort_columns) > 0 else None
        table_path = db_name + "." + str(table)

        sel_clause   = "SELECT " + d + cols + " FROM " + table_path
        where_clause = "" if filter    is None else " WHERE {}".format(filter)
        group_clause = "" if grouping  is None else " GROUP BY {}".format(grouping)
        sort_clause  = "" if sort_cols is None else " ORDER BY {} {} ".format(sort_cols, sort_direction)
        lim_clause   = "" if limit < 0         else " LIMIT {}".format(str(limit))

        return sel_clause + where_clause + group_clause + sort_clause + lim_clause + ";"

    @staticmethod
    def Query(cursor, query: str, fetch_results: bool = True, use_bigquery: bool = False) -> typing.List[typing.Tuple]:
        Logger.toStdOut("Running query: " + query, logging.INFO)
        start = datetime.datetime.now()
        if not use_bigquery:
            cursor.execute(query)
            query_job = None
        else:
            query_job = cursor.query(query)
        Logger.toStdOut(f"Query execution completed, time to execute: {datetime.datetime.now()-start}", logging.INFO)
        if not use_bigquery:
            result = cursor.fetchall() if fetch_results else None
        else:
            result = query_job.result() if fetch_results else None
        return [col[0] for col in result] if fetch_results else None

    ## Simple function to construct and log a nice server 500 error message.
    #  @param err_msg A more detailed error message with info to help debugging.
    @staticmethod
    def server500Error(err_msg: str):
        Logger.toStdOut("HTTP Response: {}{}".format(http.HTTPStatus.INTERNAL_SERVER_ERROR.value, \
                                http.HTTPStatus.INTERNAL_SERVER_ERROR.phrase ), logging.ERROR)
        Logger.toStdOut(f"Error Message: {err_msg}", logging.ERROR)

class Logger:
    # Set up loggers
    err_logger = logging.getLogger("err_logger")
    file_handler = logging.FileHandler("ExportErrorReport.log", encoding='utf-8')
    err_logger.addHandler(file_handler)
    err_logger.setLevel(level=logging.DEBUG)
    std_logger = logging.getLogger("std_logger")
    stdout_handler = logging.StreamHandler()
    std_logger.addHandler(stdout_handler)
    std_logger.setLevel(level=logging.DEBUG)
    err_logger.debug("Testing error logger")
    std_logger.debug("Testing standard out logger")

    @staticmethod
    def toFile(message, level):
        if level == logging.DEBUG:
            Logger.err_logger.debug(message)
        elif level == logging.INFO:
            Logger.err_logger.info(message)
        elif level == logging.WARNING:
            Logger.err_logger.warn(message)
        elif level == logging.ERROR:
            Logger.err_logger.error(message)

    @staticmethod
    def toStdOut(message, level):
        if level == logging.DEBUG:
            Logger.std_logger.debug(message)
        elif level == logging.INFO:
            Logger.std_logger.info(message)
        elif level == logging.WARNING:
            Logger.std_logger.warn(message)
        elif level == logging.ERROR:
            Logger.std_logger.error(message)

    @staticmethod
    def toPrint(message, level):
        if level == logging.DEBUG:
            print(f"debug: {message}")
        elif level == logging.INFO:
            print(f"info: {message}")
        elif level == logging.WARNING:
            print(f"warning: {message}")
        elif level == logging.ERROR:
            print(f"error: {message}")