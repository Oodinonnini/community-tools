##############################################################################
#
#    Author: Pierre Faniel, Roland Bura, Alexandre Dutry
#    Copyright 2017 Niboo SRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################
import csv
import logging

from odoo import _, api, exceptions, models, registry

_logger = logging.getLogger(__name__)


def clean_header_columns(columns):
    cleaned_columns = []
    for column in columns:
        cleaned_columns.append(column.strip())
    return cleaned_columns


class ImportAbstract(models.AbstractModel):
    _description = "Abstract Import Model"
    _name = "import.abstract"

    _inherit = "import.sqlhelper"

    columns_mapping = {}
    csv_temp_directory = "/tmp/import_handler"
    session = None
    date_format = "%Y/%m/%d %H:%M:%S"

    @api.model
    def execute_import_chunk(self, offset, limit, company_id, job=False):
        """
        Abstract method.
        This method should by overwritten by each import
        :param offset: Current offset
        :param limit: The chunk size
        :param company_id: res.company id
        :return: Raise an NotImplementedError
        """
        raise NotImplementedError("Subclasses should implement this!")

    def _get_extra_header_columns(self, columns):
        index = 0
        extra_columns = {}
        for column in columns:
            if column not in self.columns_mapping:
                extra_columns[index] = column
            index += 1
        return extra_columns

    def copy_data_from_csv(self, file_path):
        """
        Copy the CSV into the import table
        """
        with open(file_path, "r", encoding="utf-8-sig") as file:
            # Read the first line as we don't want to send the headers to SQL
            reader = csv.reader(file, delimiter=self.delimiter)
            file_columns = next(reader)
            file_columns = clean_header_columns(file_columns)

            odoo_columns = [
                self.columns_mapping.get(column, column) for column in file_columns
            ]

            if not odoo_columns:
                self.error(_("No columns in file."))
                raise exceptions.MissingError(_("No columns in file."))

            uid = self._uid
            context = self._context
            with registry(self._cr.dbname).cursor() as cr:
                env = api.Environment(cr, uid, context)

                copy_query = f"""
                    COPY {self._table} ({",".join(odoo_columns)})
                    FROM STDIN
                    WITH DELIMITER '{self.delimiter}' CSV;
                    """

                # Copy the value of the file in the table
                env.cr.copy_expert(copy_query, file=file)
                env.cr.commit()

    def get_import_length(self):
        with registry(self._cr.dbname).cursor() as cr:

            query = "SELECT COUNT(*) FROM %s;" % (self._table)
            cr.execute(query)
            size = cr.dictfetchone().get("count", 0)
            cr.commit()  # pylint: disable=E8102
        return size
