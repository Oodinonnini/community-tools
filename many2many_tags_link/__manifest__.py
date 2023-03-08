# -*- coding: utf-8 -*-
{
    'name' : 'Many2many Tag Link',
    'version' : '1.1',
    'author' : 'Ngasturi',
    'summary': 'Many2many Tag Widget With Link',
    'description': '',
    'category': '',
    'website': 'https://github.com/znry27/many2many_tags_link',    
    'depends': ['web'],
    'data': [],
    'demo': [
    ],
    'assets': {
            'web.assets_backend': [
                'many2many_tags_link/static/src/js/widget.js',
            ],
            'web.assets_qweb': [
                'many2many_tags_link/static/src/xml/**/*',
            ],
    },
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
