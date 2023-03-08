##############################################################################
#
#    Author: Pierre Faniel
#    Copyright 2017 Niboo SRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################
import re

from odoo import fields, models


class ExecuteImport(models.TransientModel):
    _name = "execute.import"
    _description = "execute.import"

    import_model_id = fields.Many2one("import.model", "Import File")
    limit = fields.Integer("Amount of Rows to Import")
    reimport_source_file = fields.Boolean("Reimport Source File", default=True)

    domain_element_ids = fields.One2many("import.domain.element", "wizard_id", "Domain")
    date_format = fields.Char("Date format", default="%Y/%m/%d %H:%M:%S")
    model_name = fields.Char(related="import_model_id.model_id.model")
    offset = fields.Integer("Offset")

    def _create_domain(self):
        regex = r"[ ](?=[ ])|[^-_%,A-Za-z0-9 ]+"
        domain_list = []

        table_name = self.model_name.replace(".", "_")

        for domain_element in self.domain_element_ids:
            value = re.sub(regex, "", domain_element.value, 0)
            domain_list.append(
                "%s.%s %s '%s'"
                % (
                    table_name,
                    domain_element.field_id.name,
                    domain_element.operator,
                    value,
                )
            )

        return " OR ".join(domain_list)

    def execute_import(self):
        self.ensure_one()

        self.import_model_id.execute_import(
            date_format=self.date_format,
            offset=self.offset,
            limit=self.limit,
            reimport_source_file=self.reimport_source_file,
        )


class DomainElement(models.TransientModel):
    _name = "import.domain.element"
    _description = "import.domain.element"

    field_id = fields.Many2one("ir.model.fields", "Fields", required=True)
    operator = fields.Selection(
        [("=", "="), ("ILIKE", "ilike")], "Operator", required=True
    )
    value = fields.Char("Value", required=True)

    model_name = fields.Char(related="wizard_id.model_name")

    wizard_id = fields.Many2one("execute.import", "Wizard")
