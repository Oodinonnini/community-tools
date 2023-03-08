# © 2021 Aurore Chevalier
# © 2021 Niboo SRL (<https://www.niboo.com/>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import ast
import collections

from odoo import models

ColumnMetadata = collections.namedtuple(
    "ColumnMetadata", "grouping domain prev next initial values format"
)


class Base(models.AbstractModel):
    _inherit = "base"

    def _grid_column_info(self, name, col_range):
        """
        Get the information of a given column.
        :param name: the field name linked to that column
        :param col_range: the range of the column
        :type name: str
        :type col_range: None | dict
        :return: a ColumnMetadata object representing the information of that column.
        :rtype: ColumnMetadata
        """
        field = self._fields[name]
        if field.type == "many2one" and field.domain:
            return ColumnMetadata(
                grouping=name,
                domain=[],
                prev=False,
                next=False,
                initial=False,
                values=[
                    {
                        "values": {name: v},
                        "domain": [(name, "=", v[0])],
                        "is_current": False,
                    }
                    for v in self.env[field.comodel_name]
                    .search(ast.literal_eval(field.domain))
                    .name_get()
                ],
                format=lambda a: a and a[0],
            )
        return super(Base, self)._grid_column_info(name, col_range)
