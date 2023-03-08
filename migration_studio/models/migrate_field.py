# © 2022 Nico Darnis, Albin Gilles
# © 2022 Niboo SRL (<https://www.niboo.com/>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class StudioMigration(models.Model):
    _name = "studio.migration"
    _description = "Studio Migration"

    @api.model
    def message_post_field_name(self, record, field):
        value = getattr(record, field)
        record.message_post(body=f"{field}: {value}")

    @api.model
    def move_studio_binary(self, record, studio_binary_field, message=True):
        # Move New File to chatter
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", record._name),
                ("res_field", "=", studio_binary_field),
                ("res_id", "=", record.id),
            ]
        )
        if attachment:
            attachment.name = getattr(record, f"{studio_binary_field}_filename")

            if message:
                record.message_post(attachment_ids=[attachment.id])

            attachment.res_field = False
            setattr(record, studio_binary_field, False)

    @api.model
    def move_field(self, record, old_field, new_field, message=True):
        setattr(record, new_field, getattr(record, old_field))

        if message:
            self.message_post_field_name(record, old_field)

    @api.model
    def move_fields(self, record, fields_to_migrate, message=True):
        for old_field, new_value in fields_to_migrate.items():
            self.move_field(record, old_field, new_value, message)
