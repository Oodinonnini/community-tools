##############################################################################
#
#    Author: Pierre Faniel
#    Copyright 2017 Niboo SPRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################

{
    "name": "Log Extension",
    "category": "Base",
    "summary": "Logging inside Odoo",
    "website": "https://www.niboo.be/",
    "version": "16.0.1.0.0",
    "license": "Other proprietary",
    "description": """
    - Adds a "view record" button on logs that allow us to preview the record that
    created the log.
    - Enhanced log views to ease the understanding of what's going on.
    - allow logs to be stored on Database.
    """,
    "author": "Niboo",
    "depends": ["base"],
    "data": ["data/ir_config_parameter.xml", "views/ir_logging.xml"],
    "installable": True,
    "application": False,
}
