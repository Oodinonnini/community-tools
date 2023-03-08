##############################################################################
#
#    Author: Sami Farhat
#    Copyright 2021 Niboo SRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, models
from odoo.tools import config


class QueueJob(models.Model):
    _inherit = "queue.job"

    @api.model
    def _cron_clear_zombie_jobs(self):
        """
        Get and cancel all jobs taht started too long time ago, and should
        be considered zombies.
        """
        limit_time_cpu = config['limit_time_cpu']
        relative = relativedelta(seconds=limit_time_cpu)

        acceptable_start_date = datetime.now() - relative

        zombies = self.env['queue.job'].search([('state', '=', 'started'), (
            'date_started', '<', acceptable_start_date)])

        zombies.cancel_job()
