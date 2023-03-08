##############################################################################
#
#    Author: Pierre Faniel, Roland Bura
#    Copyright 2017 Niboo SRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################
import glob
import logging
import os

from odoo import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)


class ImportModel(models.Model):
    _description = "Model to import"
    _name = "import.model"
    _order = "sequence"

    name = fields.Char("Name", required=True)
    active = fields.Boolean("Active", default=True)
    sequence = fields.Integer("Sequence", default=10)
    company_id = fields.Many2one("res.company", "Company", required=True)

    job_ids = fields.One2many("import.job", "import_model_id", "Jobs", readonly=True)

    file_pattern = fields.Char(
        compute="_compute_file_pattern", inverse="_inverse_set_file_pattern"
    )
    pattern = fields.Char()

    model_id = fields.Many2one(
        "ir.model", domain=[("inherited_model_ids.model", "in", ["import.abstract"])]
    )

    source_folder_path = fields.Char(required=True)
    destination_folder_path = fields.Char(required=True)

    is_handle_improper_csv = fields.Boolean("Handle improper CSV", default=False)
    last_import_time = fields.Datetime(
        "Last Import Date", compute="_compute_last_import_time"
    )

    domain = fields.Text("SQL Domain")

    def _compute_file_pattern(self):
        for import_model in self:
            import_model.file_pattern = import_model.pattern

    def _inverse_set_file_pattern(self):
        for import_model in self:
            import_model.pattern = import_model.file_pattern

    def button_delete_logs(self):
        """
        Remove all logs on all jobs
        :return:
        """
        for file in self:
            file.job_ids.remove_all_logs()

    def _compute_last_import_time(self):
        for import_file in self:
            import_file.last_import_time = False
            job = self.env["import.job"].search(
                [("import_model_id", "=", import_file.id)],
                order="date_start desc",
                limit=1,
            )
            if job:
                import_file.last_import_time = job.date_start

    @api.constrains("source_folder_path", "destination_folder_path")
    def check_folder_path(self):
        def _check_folder_path(path):  # pylint: disable=W0101
            if not os.path.isdir(path):
                raise exceptions.UserError(
                    _("%s is not a correct directory" % path)
                )  # pylint: disable=W0101
                if not os.access(path, os.W_OK):
                    raise exceptions.UserError(
                        _("You cannot write on the folder %s" % path)
                    )

        for import_model in self:
            _check_folder_path(import_model.source_folder_path)
            _check_folder_path(import_model.destination_folder_path)

    def _get_next_file_to_import(self):
        """
        Return a list of files to import according the import_model_id
        :param import_model_id: ID - the ID of the file import.model to import
        :return: A list of path
        """
        self.ensure_one()
        files_to_import = glob.glob(self.source_folder_path + "/" + self.file_pattern)
        files_to_import.sort()

        # only keep files that does not contain "modified", we don't want to
        # treat those
        files_to_keep = []
        for file in files_to_import:
            if "modified" not in file:
                files_to_keep.append(file)

        return files_to_keep and files_to_keep[0] or False

    def execute_import(
        self,
        domain=False,
        date_format=False,
        offset=False,
        limit=0,
        reimport_source_file=True,
    ):
        for import_model in self:
            _logger.info("Start the import %s" % import_model.name)

            # TODO file_path non existent here, fails if not reimport
            if reimport_source_file:
                file_path = import_model._get_next_file_to_import()

            job = self.env["import.job"].create(
                {
                    "name": self.name,
                    "state": "waiting",
                    "import_model_id": import_model.id,
                    "domain": domain,
                    "offset": offset,
                    "limit": limit,
                    "date_format": date_format,
                    "file_path": file_path,
                    "reimport_source_file": reimport_source_file,
                }
            )

            if not file_path and reimport_source_file:
                job.warning(
                    "No file found",
                    detail="No file following the pattern %s in %s"
                    % (self.file_pattern, self.source_folder_path),
                )
                job.state = "skip"
                self._cr.commit()  # pylint: disable=E8102
                raise exceptions.UserError(_("No file found"))

            job.info("Import the file %s" % file_path)
            nbr_of_chunk = job.init_and_get_chunks()

            for chunk_iterator in range(nbr_of_chunk):
                offset = chunk_iterator * job.limit_by_chunk
                # Call the method import_chunk for each chunk
                job.with_delay().import_chunk(offset, chunk_iterator + 1)
            job.info('End of the import preparation "%s"' % self.name)

    def button_execute_import(self):
        self.ensure_one()
        return {
            "name": "Execute %s" % self.name,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "execute.import",
            "type": "ir.actions.act_window",
            "target": "new",
            "view_id": self.env.ref("import_handler.wizard_execute_import_view").id,
            "context": {"default_import_model_id": self.id},
        }
