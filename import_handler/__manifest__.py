##############################################################################
#
#    Author: Pierre Faniel
#    Copyright 2017 Niboo SRL - All Rights Reserved
#
#    Unauthorized copying of this file, via any medium is strictly prohibited
#    Proprietary and confidential
#
##############################################################################
{
    "name": "Import Handler Module",
    "category": "Import",
    "summary": "Handles the import of data from external sources",
    "website": "https://www.niboo.com/",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "description": """
Import helper that handles with a queue system the import of data from
external sources.
    """,
    "author": "Niboo",
    "depends": ["queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "views/import_job.xml",
        "views/import_model.xml",
        "wizards/execute_import.xml",
    ],
    "installable": True,
    "application": True,
}
