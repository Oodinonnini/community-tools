# © 2022 Albin Gilles
# © 2022 Niboo SRL (<https://www.niboo.com/>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    "name": "Home Background Image",
    "summary": """
        Set a background image for the Odoo company.
    """,
    "author": "Niboo",
    "website": "https://www.niboo.com",
    "category": "Customizations",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["web_enterprise"],
    "data": [
        "views/views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'home_background_image/static/src/js/*.js',
            'home_background_image/static/src/xml/*.xml',
            'home_background_image/static/src/scss/*.scss',
        ],
    },
    "installable": True,
    "application": False,
}
