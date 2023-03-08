odoo.define('obj_web_grid.GridView', function (require) {
    "use strict";

    var WebGridView = require('web_grid.GridView');
    var viewRegistry = require('web.view_registry');

    var ObjGridView = WebGridView.extend({
        // Needed to allow grid to work without ranges
        _default_context: {'name': 'bla'},
        _extract_ranges: function () {
            return [this._default_context];
        },
    });

    viewRegistry.add('obj_web_grid', ObjGridView);

    return ObjGridView;
});
