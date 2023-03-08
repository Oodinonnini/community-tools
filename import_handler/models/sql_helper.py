##############################################################################
#
#    Author: Pierre Faniel, Roland Bura, Alexandre Dutry
#    Copyright 2017 Niboo SRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################
import logging

from psycopg2.extensions import AsIs

import odoo
from odoo import api, fields, models, registry

_logger = logging.getLogger(__name__)


class SQLHelper(models.AbstractModel):
    _description = "SQL Helper"
    _name = "import.sqlhelper"

    def sql_insert(self, table, values):
        """
        Inserts a new row into the table
        :param table: Table of the new row
        :param values: Values for the new row
        :return: Id of the created row
        """
        values.update(
            {
                "create_date": fields.Datetime.now(),
                "create_uid": 1,
                "write_date": fields.Datetime.now(),
                "write_uid": 1,
            }
        )

        fields_to_insert = ", ".join(list(values.keys()))
        values_to_insert = ", ".join(["%%(%s)s" % x for x in values])

        # pylint: disable=E8103
        query = "INSERT INTO {} ({}) VALUES ({});".format(
            table, fields_to_insert, values_to_insert
        )
        self.env.cr.execute(query, values)
        self.env.cr.execute("SELECT LASTVAL()")
        return self.env.cr.fetchone()[0]

    def sql_insert_many2many(self, table, values):
        """
        Inserts a new row into the many2many relation table
        :param table: Table of the new row
        :param values: Values for the new row
        :return: Id of the created row
        """
        fields_to_insert = ", ".join(list(values.keys()))
        values_to_insert = ", ".join(["%%(%s)s" % x for x in values])
        # pylint: disable=E8103
        query = "INSERT INTO {} ({}) VALUES ({});".format(
            table, fields_to_insert, values_to_insert
        )
        self.env.cr.execute(query, values)

    def sql_update(self, table, primary_key, pk_value, values):
        """
        Updates the values of the row referenced by the pk_value
        :param table: Table of the row
        :param primary_key: name of the primary key column
        :param pk_value: value of the primary key
        :param values: Values of the row to be updated
        """
        values.update({"write_date": fields.Datetime.now(), "write_uid": 1})
        # pylint: disable=E8103
        query = "UPDATE %s SET " % table
        for key, value in values.items():
            query = "{} {} = '{}',".format(query, key, value)

        query = "{} WHERE {} = '{}';".format(query[:-1], primary_key, pk_value)
        self.env.cr.execute(query)

    @api.model
    def commit(self):
        """
        If we want to test imports we cannot commit in DB.
        To avoid this we can enable the test mode in import settings
        :return:
        """
        # TODO move test variable on import.model
        is_import_test_mode = self.env["ir.config_parameter"].get_param(
            "import_handler.is_import_test_mode"
        )
        if is_import_test_mode:
            return
        self.env.cr.commit()  # pylint: disable=E8102

    @api.model
    def truncate_table(self, table):
        """
        Truncate the table in parameter
        :param table:
        :return:
        """
        query = """
        TRUNCATE %(table)s;
        ALTER SEQUENCE %(table_sequence)s RESTART WITH 1;
        """
        with registry(self.env.cr.dbname).cursor() as new_cr:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            new_env.cr.execute(
                query,
                {"table": AsIs(table), "table_sequence": AsIs(table + "_id_seq")},
            )
            new_env.cr.commit()  # pylint: disable=E8102
