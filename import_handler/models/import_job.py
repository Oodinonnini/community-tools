##############################################################################
#
#    Author: Pierre Faniel
#    Copyright 2017 Niboo SRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################

import csv
import logging
import os
import shutil
import traceback
from datetime import datetime
from math import ceil

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

from odoo import api, fields, models, registry

_logger = logging.getLogger(__name__)


def clean_header_columns(columns):
    cleaned_columns = []
    for column in columns:
        cleaned_columns.append(column.strip())
    return cleaned_columns


class ImportJob(models.Model):
    _description = "Job for Imports"
    _name = "import.job"
    _order = "date_start DESC"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    LOGGER_STATE = [
        ("waiting", "Waiting"),
        ("progress", "In Progress"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("skip", "Skipped"),
        ("error", "Error"),
        ("stopped", "Stopped"),
    ]

    name = fields.Char("Name", required=True)

    file_path = fields.Char("Filepath")
    date_start = fields.Datetime(
        "Date start", default=lambda self: fields.Datetime.now()
    )
    date_end = fields.Datetime("Date end")
    line_ids = fields.One2many(
        "import.job.log", "job_id", auto_join=True, string="Lines", ondelete="cascade"
    )
    state = fields.Selection(LOGGER_STATE, "Status")
    info = fields.Text("Information")
    import_model_id = fields.Many2one("import.model", string="Import Model")
    import_model = fields.Char(
        "Import Model Name",
        index=True,
        related="import_model_id.model_id.model",
        compute_sudo=True,
        readonly=True,
    )

    number_of_chunks = fields.Integer("# of chunks")
    number_of_chunks_executed = fields.Integer("# chunks done")
    number_of_line = fields.Integer("# lines")
    progress = fields.Float("Progress", compute="_compute_progress")

    number_of_queue_jobs = fields.Integer("# Queue Jobs", compute="_compute_queue_jobs")
    number_of_queue_jobs_executed = fields.Integer(
        "# Queue Jobs done", compute="_compute_queue_jobs"
    )
    number_of_queue_jobs_failed = fields.Integer(
        "# Queue Jobs failed", compute="_compute_queue_jobs"
    )

    domain = fields.Char("Domain", readonly=True)
    delimiter = fields.Char("Delimiter", compute="_compute_delimiter")
    offset = fields.Integer("Initial Offset")
    limit = fields.Integer("Amount Of Rows To Import", default=0)
    limit_by_chunk = fields.Integer("Amount of rows to import by chunk", default=0)
    date_format = fields.Char("Date Format")
    todo_ids = fields.Text("Ids")
    reimport_source_file = fields.Boolean("Reimport source file")

    def _compute_delimiter(self):
        for job in self:
            job.delimiter = job.env[job.import_model].delimiter

    def button_stop(self):
        self.state = "stopped"

    def _compute_progress(self):
        for job in self:
            chunks = job.number_of_chunks or 1
            job.progress = job.number_of_chunks_executed / chunks * 100

    def _compute_queue_jobs(self):
        for job in self:
            queue_jobs = self.env["queue.job"].search(
                [
                    ("model_name", "=", "import.job"),
                    ("method_name", "=", "import_chunk"),
                    ("func_string", "ilike", "import.job(%d,)%%" % job.id),
                ]
            )
            executed_queue_jobs = queue_jobs.filtered(
                lambda queue_job: queue_job.state == "done"
            )
            failed_queue_jobs = queue_jobs.filtered(
                lambda queue_job: queue_job.state == "failed"
            )
            job.number_of_queue_jobs_executed = len(executed_queue_jobs)
            job.number_of_queue_jobs = len(queue_jobs)
            job.number_of_queue_jobs_failed = len(failed_queue_jobs)

    def remove_all_logs(self):
        logs = self.env["import.job.log"].search([("job_id", "in", self.ids)])
        logs.unlink()

    def __to_error(self):
        self.ensure_one()
        self.state = "error"
        self.date_end = fields.Datetime.now()

    def exception(self, message, detail="", line=False, category=""):
        _logger.exception(message)
        self.log("error", message, detail, line, category)
        self.__to_error()

    def info(self, message, detail="", line=False, category=""):
        _logger.info(message)
        self.log("info", message, detail, line, category)

    def warning(self, message, detail="", line=False, category=""):
        _logger.warning(message)
        self.log("warning", message, detail, line, category)

    def error(self, message, detail="", line=False, category=""):
        _logger.error(message)
        self.log("error", message, detail, line, category)
        self.__to_error()

    def log(self, level, message, detail="", line=False, category=""):
        self.ensure_one()
        self.line_ids.create(
            {
                "level": level,
                "name": message,
                "detail": detail,
                "line": line,
                "category": category,
                "time": fields.Datetime.now(),
                "job_id": self.id,
            }
        )

    def __treat_improper_csv_header(self):
        """
        Determine if the file header is containing extra columns like
        unidentified or empty
        :param file:
        :param file_columns:
        :return:
        """
        with open(self.file_path, "r", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=self.delimiter)
            file_columns = next(reader)
            file_columns = clean_header_columns(file_columns)

            model = self.env[self.import_model]
            extra_columns = model._get_extra_header_columns(file_columns)
            if extra_columns:
                self.info(
                    "There are new columns in the file: %s"
                    % ", ".join(extra_columns.values())
                )

            second_line = file.readline()
            is_extra_columns = False
            if len(file_columns) < len(second_line.split(self.delimiter)):
                is_extra_columns = True
                if is_extra_columns:
                    self.info("There are unnamed new columns in the file")

            if is_extra_columns or extra_columns:
                return self.__create_tmp_cleaned_csv_file(extra_columns)
        return False

    def __init_import(self):
        """
        Import initialization
            1. Vacuum the import table (eg: import.campaign => vacuum the table
            import_campaign)
            2. Verify validity of CSV and create a tmp cleaned file if needed
            3. Copy the CSV into the import table
        :param file_path: str - The path to the file to import
        :param import_file: the import.model to import
        """
        file_path = False
        model = self.env[self.import_model]

        # If reimported, we truncate the table and check for improper csv
        if self.reimport_source_file:
            try:
                model.truncate_table(model._table)
            except psycopg2.Error as error:
                self.error(f"Cannot truncate the table {self._table}.{error}")
                raise
            if self.import_model_id.is_handle_improper_csv:
                # Extra columns without column names or unidentified
                file_path = self.__treat_improper_csv_header()
            try:
                model.copy_data_from_csv(file_path or self.file_path)
            except psycopg2.Error as error:
                self.exception(
                    f"Cannot copy the file {file_path or self.file_path} "
                    f"into {self._table}.",
                    detail=f"{error}",
                    category="Init",
                )
                raise
            finally:
                if file_path:
                    self.remove_tmp_cleaned_file(file_path)
            self.info("File re-imported")

        else:
            self.info("File not re-imported, data used from last import")

        return model.get_import_length()

    def __create_tmp_cleaned_csv_file(self, extra_columns):
        """
        Create a new csv without the columns not present in Odoo table
        :param file_path:
        :param extra_columns:
        :return:
        """
        with open(self.file_path, "r", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=self.delimiter)
            new_file_path = (
                self.file_path[: self.file_path.rfind(".csv")] + "_modified.csv"
            )
            with open(new_file_path, "w") as modified_file:
                writer = csv.writer(modified_file, delimiter=self.delimiter)
                first_line = next(reader)
                max_col = len(first_line)
                self.__check_csv_line(writer, first_line, extra_columns)
                for row in reader:
                    self.__check_csv_line(writer, row[:max_col], extra_columns)
        return new_file_path

    def __check_csv_line(self, writer, row, extra_columns):
        values = []
        for column_index in range(len(row)):
            if column_index not in extra_columns.keys():
                values.append(row[column_index])
        writer.writerow(values)

    def remove_tmp_cleaned_file(self, file_path):
        """
        Remove the modified file
        :param is_to_remove:
        :param file_path:
        :return:
        """
        os.remove(file_path)

    def close_import(self):
        """
        This method will merge all temporary logs (wrote in the data base
        import.logger.line.temp) and set the state of the logger
        :param file_path: The file path
        :return:
        """
        if self.state != "error":
            shutil.move(
                self.file_path, self.import_model_id.destination_folder_path + "/"
            )
            self.state = "success"
        else:
            shutil.move(self.file_path, self.file_path + ".error")
        self.date_end = fields.Datetime.now()

    def init_and_get_chunks(self):
        """
        Init the import and return all information about chunks
        :param file_to_import: str - The path to the file to import
        :param import_model_id: int - The ID of the import.model
        :return: dict - Return a dictionary with information about chunks
        """
        # Initialization
        self.ensure_one()
        try:
            size = self.__init_import()
        except psycopg2.Error:
            return False
        except Exception:
            self.error("Cannot init the file", traceback.format_exc())
            return False

        # Reduce the length by the offset
        if self.offset:
            size = size - self.offset

        nbr_of_chunk = ceil(size / self.limit_by_chunk)

        if self.limit > 0:
            nbr_of_chunk_by_limit = ceil(self.limit / self.limit_by_chunk)
            if nbr_of_chunk_by_limit < nbr_of_chunk:
                nbr_of_chunk = nbr_of_chunk_by_limit
                size = self.limit

        self.number_of_chunks = nbr_of_chunk
        self.number_of_line = size
        self.state = "progress"

        self.info(
            "Import length: %d, Amount of chunks: %d, Chunk size: %d"
            % (size, nbr_of_chunk, self.limit_by_chunk)
        )
        return nbr_of_chunk

    def import_chunk(self, offset, number=0):
        """
        This method will, at first, clean the to_log and to_info parameter
        (used for the job).
        After that, this method will call the method execute_import_chunk.
        At the end, the method will commit alls logs with the method
        commit_logs(job_id)

        :param offset: Offset in the DB (eg: if offset = 1000 => the system
        will ignore 1000 first elements)
        :return: the environment context
        """
        self.ensure_one()

        if self.state == "stopped":
            self.error(
                "Stopped during the import %s with offset %s (limit: %s)"
                % (self._description or self._name, offset, self.limit_by_chunk)
            )
            raise Exception()

        if self.offset:
            offset += self.offset
        company_id = self.import_model_id.company_id.id

        self.info(
            "Start of chunk %d" % number,
            detail="import %s with offset %s (limit: %s)"
            % (self.name, offset, self.limit_by_chunk),
        )
        self._cr.commit()  # pylint: disable=E8102

        # Date start - Use for stat
        date_start = datetime.now()

        with registry(self.env.cr.dbname).cursor() as new_cr:
            new_cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            job = self.with_env(env)

            # Execute the import himself
            try:
                model = job.with_context(importing=True).env[self.import_model]
                model.execute_import_chunk(offset, self.limit_by_chunk, company_id, job)
            except Exception as e:
                # Write the traceback on the job
                # We need to create an another cursor
                traceback_str = traceback.format_exc()
                self.error(e.args[0], traceback_str)
                raise Exception(e)

        # Date end - Use for stat
        date_end = datetime.now()

        duration = date_end - date_start
        # duration_by_elem = duration / self.limit_by_chunk
        duration_in_secs = duration.total_seconds()
        # duration_by_elem_in_secs = duration_by_elem.total_seconds()

        self.info(
            "End of chunk %d" % number,
            detail="Total time = %s seconds" % duration_in_secs,
        )

        self.number_of_chunks_executed += 1

        queue_jobs = self.env["queue.job"].search(
            [
                ("model_name", "=", "import.job"),
                ("method_name", "=", "import_chunk"),
                ("func_string", "ilike", "import.job(%d,)%%" % self.id),
            ]
        )
        running_queue_jobs = queue_jobs.filtered(
            lambda queue_job: queue_job.state in ["pending", "enqueued", "started"]
        )

        queue_jobs_length = len(running_queue_jobs)
        if queue_jobs_length == 1 and running_queue_jobs.uuid == self._context.get(
            "job_uuid"
        ):
            failed_queue_jobs = queue_jobs.filtered(
                lambda queue_job: queue_job.state == "failed"
            )
            if failed_queue_jobs:
                self.state = "error"
            self.close_import()


class ImportJobLog(models.Model):
    _description = "Logger for imports"
    _name = "import.job.log"

    LOG_LEVEL = [
        ("stat", "Stat"),
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    name = fields.Char("Message", required=True)
    detail = fields.Text("Details")
    level = fields.Selection(
        LOG_LEVEL, string="Level", default="warning", required=True
    )
    job_id = fields.Many2one(
        "import.job", string="Logger", required=True, ondelete="cascade", index=True
    )
    category = fields.Char()
    line = fields.Integer("Line")
    time = fields.Datetime("Time")
