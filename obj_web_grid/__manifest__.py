# © 2021 Aurore Chevalier
# © 2021 Niboo SRL (<https://www.niboo.com/>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Tools - grid with Objects",
    "category": "Tools",
    "summary": "Allows you to use the grid view with object instead of range",
    "website": "https://www.niboo.com/",
    "license": "AGPL-3",
    "version": "14.0.1.0.0",
    "description": """
    -disable the range renderer in JS (which is used for the date)
    -will display a column at 0 by default if no value is provided
    -wil use the domain of the col field if given (to reduce the number of columns)
    """,
    "images": [],
    "author": "Niboo",
    "depends": ["web_grid"],
    "data": ["views/assets.xml"],
    "installable": True,
    "application": False,
}
