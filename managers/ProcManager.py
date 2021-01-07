# import standard libraries
import json
import logging
import traceback
import typing
# import local files
import GameTable
import utils
from feature_extractors.WaveExtractor import WaveExtractor
from feature_extractors.JowilderExtractor import JowilderExtractor
from schemas.Schema import Schema

## @class ProcManager
#  Class to extract and manage features for a processed csv file.
class ProcManager:
    ## Constructor for the ProcManager class.
    #  Simply stores some data for use later, including the type of extractor to
    #  use.
    #
    #  @param ExtractorClass The type of data extractor to use for input data.
    #         This should correspond to whatever game_id is in the GameTable.
    #  @param game_table    A data structure containing information on how the db
    #                       table assiciated with the given game is structured. 
    #  @param game_schema   A dictionary that defines how the game data itself
    #                       is structured.
    #  @param proc_csv_file The output file, to which we'll write the processed
    #                       feature data.
    def __init__(self, ExtractorClass: type, game_table: GameTable, game_schema: Schema,
                 proc_csv_file: typing.IO.writable):
        ## Define instance vars
        self._ExtractorClass:     type               = ExtractorClass
        self._game_table:         GameTable          = game_table
        self._game_schema:        Schema             = game_schema
        self._proc_file:          typing.IO.writable = proc_csv_file
        self._session_extractors: typing.Dict[str, self._ExtractorClass] = {}

    ## Function to handle processing of a single row of data.
    #  Basically just responsible for ensuring an extractor for the session
    #  corresponding to the row already exists, then delegating the processing
    #  to that extractor.
    #  @param row_with_complex_parsed A tuple of the row data. We assume the
    #                      event_data_complex has already been parsed from JSON.
    def ProcessRow(self, row_with_complex_parsed: typing.Tuple):
        session_id = row_with_complex_parsed[self._game_table.session_id_index]
        # ensure we have an extractor for the given session:
        if not session_id in self._session_extractors.keys():
            if row_with_complex_parsed[2] == 'LAKELAND':
                self._session_extractors[session_id] = self._ExtractorClass(session_id, self._game_table, self._game_schema, self._proc_file)
            else:
                self._session_extractors[session_id] = self._ExtractorClass(session_id, self._game_table, self._game_schema)
        self._session_extractors[session_id].extractFromRow(row_with_complex_parsed, self._game_table)

    ##  Function to empty the list of lines stored by the ProcManager.
    #   This is helpful if we're processing a lot of data and want to avoid
    #   eating too much memory.
    def ClearLines(self):
        utils.Logger.toStdOut(f"Clearing {len(self._session_extractors)} entries from ProcManager.", logging.DEBUG)
        self._session_extractors = {}

    ## Function to calculate aggregate features of all extractors created by the
    #  ProcManager. Just calls the function once on each extractor.
    def calculateAggregateFeatures(self):
        for extractor in self._session_extractors.values():
            extractor.calculateAggregateFeatures()

    ## Function to write out the header for a processed csv file.
    #  Just runs the header writer for whichever Extractor subclass we were given.
    def WriteProcCSVHeader(self):
        self._ExtractorClass.writeCSVHeader(game_table=self._game_table, game_schema=self._game_schema, file=self._proc_file)

    ## Function to write out all data for the extractors created by the
    #  ProcManager. Just calls the "write" function once for each extractor.
    def WriteProcCSVLines(self):
        for extractor in self._session_extractors.values():
            extractor.writeCurrentFeatures(file=self._proc_file)

    def SetSurveyTSVFile(self, survey_tsv_file: typing.IO.writable):
        self._survey_tsv_file = survey_tsv_file

    def WriteSurveyTSV(self):
        for extractor in self._session_extractors.values():
            if type(extractor) is JowilderExtractor:
                extractor.writeTSVHeader(self._game_table, self._game_schema, self._survey_tsv_file)
                extractor.writeSurveyFeatures(self._game_table, self._game_schema, self._survey_tsv_file)
