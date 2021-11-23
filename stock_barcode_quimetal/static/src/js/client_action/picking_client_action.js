odoo.define('stock_barcode.QuimetalClientAction', function (require) {
    'use strict';

    var PickingClientAction = require('stock_barcode.picking_client_action');
    var ViewsWidget = require('stock_barcode.ViewsWidget');

    var QuimetalClientAction = PickingClientAction.include({
        custom_events: _.extend({}, PickingClientAction.prototype.custom_events, {
            'print_line': '_onPrintLine',
        }),
        /**
         * @override
         */
        _instantiateViewsWidget: function (defaultValues, params) {
            debugger;
            return new ViewsWidget(
                this,
                'product.template',
                'stock_barcode_quimetal.barcode_quimetal_product',
                defaultValues,
                params
            );
        },
        /**
         * Handles the `edit_product` OdooEvent. It destroys `this.linesWidget` and displays an instance
         * of `ViewsWidget` for the line model.
         *
         * Editing a line should not "end" the barcode flow, meaning once the changes are saved or
         * discarded in the opened form view, the user should be able to scan a destination location
         * (if the current flow allows it) and enforce it on `this.scanned_lines`.
         *
         * @private
         * @param {OdooEvent} ev
         */
        _onPrintLine: function (ev) {
            debugger;

            ev.stopPropagation();
            this.linesWidgetState = this.linesWidget.getState();
            this.linesWidget.destroy();
            this.headerWidget.toggleDisplayContext('specialized');

            // If we want to edit a not yet saved line, keep its virtual_id to match it with the result
            // of the `applyChanges` RPC.
            var virtual_id = _.isString(ev.data.id) ? ev.data.id : false;

            var self = this;
            var self = this;
            this.mutex.exec(function () {
                return self._save().then(function () {
                    var id = ev.data.id;
                    if (virtual_id) {
                        var currentPage = self.pages[self.currentPageIndex];
                        var rec = _.find(currentPage.lines, function (line) {
                            return line.dummy_id === virtual_id;
                        });
                        id = rec.id;
                    }

                    self.ViewsWidget = self._instantiateViewsWidget({}, {currentId: id});
                    return self.ViewsWidget.appendTo(self.$('.o_content'));
                });
            });
        },


    });

    return QuimetalClientAction;

});
