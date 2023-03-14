##############################################################################
#
#    Author: Pierre Faniel
#    Copyright 2017 Niboo SPRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

from odoo import api, fields, models, registry


class IrLogging(models.Model):
    _inherit = "ir.logging"
    _rec_name = "name"

    levels_order = {"debug": 0, "info": 1, "warn": 2, "error": 3, "fatal": 4}
    level = fields.Selection(
        [
            ("debug", "Debug"),
            ("info", "Information"),
            ("warn", "Warning"),
            ("error", "Error"),
            ("fatal", "Fatal"),
        ],
        "Level",
    )
    model = fields.Char("Model", required=True, index=True)
    res_id = fields.Integer("Record ID", index=True)
    user_id = fields.Many2one("res.users", "User")

    @api.model
    def log(self, res_id, message, level="debug", name="", model=None, user_id=None):
        """
        Create a log entry
        :param res_id: Technical id of the record
        :param message: Log message
        :param level: Log level (debug, info, warn, error, fatal)
        :param name: Name of the log
        :param model: Model of the log
        :param user_id: Id of the user that generated the log
        """
        with registry(self.env.cr.dbname).cursor() as cursor:
            cursor._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
            self = self.with_env(api.Environment(cursor, self._uid, self.env.context))
            self.create(
                {
                    "message": message,
                    "res_id": res_id,
                    "level": level,
                    "model": model or self._name,
                    "name": name,
                    "user_id": user_id or self._uid,
                }
            )
            cursor.commit()

    @api.model
    def create(self, values):
        log_level = self.env.ref("log.log_level")
        if self.levels_order.get(
            values.get("level", "info").lower()
        ) < self.levels_order.get(log_level.value, 1):
            return

        if not values.get("name"):
            message = values.get("message")
            values["name"] = message[0:64] if len(message) > 64 else message

        if not values.get("line"):
            values["line"] = 1

        if not values.get("func"):
            values["func"] = "func"

        if not values.get("path"):
            values["path"] = "path"

        if not values.get("type"):
            values["type"] = "server"
        return super(IrLogging, self).create(values)

    def view_record(self):
        """
        :return: Form view of the record linked to the log line
        """
        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": self.model,
            "context": {"init": True},
            "res_id": self.res_id,
        }
