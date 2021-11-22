odoo.define('stock_barcode_quimetal.LinesWidget', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var LinesWidget = require('stock_barcode.LinesWidget');


    var QWeb = core.qweb;
    var QuimetalLinesWidget = LinesWidget.include({
        init: function (parent, page, pageIndex, nbPages) {
            this._super.apply(this, arguments);
            console.log('Entrando a la herencia');
        },
        /**
         * Called when the client action asks to add a line to the current page. Note that the client
         * action already has the new line in its current state. This method will render the template
         * of the new line and prepend it to the body of the current page.
         *
         * @param {Object} lineDescription: and object with all theinformation needed to render the
         *                 line's template, including the qty to add.
         */
        addProduct: function (lineDescription, model, doNotClearLineHighlight) {
            var $body = this.$el.filter('.o_barcode_lines');
            var $line = $(QWeb.render('stock_barcode_lines_template', {
                lines: [lineDescription],
                groups: this.groups,
                model: model,
                isPickingRelated: this.isPickingRelated,
                requireLotNumber: this.requireLotNumber,
            }));
            $body.prepend($line);
            $line.on('click', '.o_edit', this._onClickEditLine.bind(this));
            $line.on('click', '.o_print', this._onClickPrintLine.bind(this));
            $line.on('click', '.o_package_content', this._onClickTruckLine.bind(this));
            this._updateIncrementButtons($line);
            this._highlightLine($line, doNotClearLineHighlight);

            this._handleControlButtons();

            if (lineDescription.qty_done === 0) {
                this._toggleScanMessage('scan_lot');
                this._highlightLotIcon($line);
            } else if (this.mode === 'receipt') {
                this._toggleScanMessage('scan_more_dest');
            } else if (['delivery', 'inventory'].indexOf(this.mode) >= 0) {
                this._toggleScanMessage('scan_more_src');
            } else if (this.mode === 'internal') {
                this._toggleScanMessage('scan_more_dest');
            } else if (this.mode === 'no_multi_locations') {
                this._toggleScanMessage('scan_products');
            }

        },
        /**
         * Render the header and the body of this widget. It is called when rendering a page for the
         * first time. Once the page is rendered, the modifications will be made by `incrementProduct`
         * and `addProduct`. When another page should be displayed, the parent will destroy the current
         * instance and create a new one. This method will also toggle the display of the control
         * button.
         *
         * @private
         * @param {Object} linesDescription: description of the current page
         * @param {Number} pageIndex: the index of the current page
         * @param {Number} nbPages: the total number of pages
         */
        _renderLines: function () {
            debugger;
            if (this.mode === 'done') {
                if (this.model === 'stock.picking') {
                    this._toggleScanMessage('picking_already_done');
                } else if (this.model === 'stock.inventory') {
                    this._toggleScanMessage('inv_already_done');
                }
                return;
            } else if (this.mode === 'cancel') {
                this._toggleScanMessage('picking_already_cancelled');
                return;
            }

            // Render and append the page summary.
            var $header = this.$el.filter('.o_barcode_lines_header');
            var $pageSummary = $(QWeb.render('stock_barcode_summary_template', {
                locationName: this.page.location_name,
                locationDestName: this.page.location_dest_name,
                nbPages: this.nbPages,
                pageIndex: this.pageIndex + 1,
                mode: this.mode,
                model: this.model,
                isPickingRelated: this.isPickingRelated,
                sourceLocations: this.sourceLocations,
                destinationLocations: this.destinationLocations,
            }));
            $header.append($pageSummary);

            // Render and append the lines, if any.
            var $body = this.$el.filter('.o_barcode_lines');
            if (this.page.lines.length) {
                var $lines = $(QWeb.render('stock_barcode_lines_template', {
                    lines: this.getProductLines(this.page.lines),
                    packageLines: this.getPackageLines(this.page.lines),
                    model: this.model,
                    groups: this.groups,
                    isPickingRelated: this.isPickingRelated,
                    istouchSupported: this.istouchSupported,
                    requireLotNumber: this.requireLotNumber,
                }));
                $body.prepend($lines);
                for (const line of $lines) {
                    if (line.dataset) {
                        this._updateIncrementButtons($(line));
                    }
                }
                $lines.on('click', '.o_edit', this._onClickEditLine.bind(this));
                $lines.on('click', '.o_print', this._onClickPrintLine.bind(this));
                $lines.on('click', '.o_package_content', this._onClickTruckLine.bind(this));
            }
            // Toggle and/or enable the control buttons. At first, they're all displayed and enabled.
            var $next = this.$('.o_next_page');
            var $previous = this.$('.o_previous_page');
            var $validate = this.$('.o_validate_page');
            if (this.nbPages === 1) {
                $next.prop('disabled', true);
                $previous.prop('disabled', true);
            }
            if (this.pageIndex + 1 === this.nbPages) {
                $next.toggleClass('o_hidden');
                $next.prop('disabled', true);
            } else {
                $validate.toggleClass('o_hidden');
            }

            if (!this.page.lines.length && this.model !== 'stock.inventory') {
                $validate.prop('disabled', true);
            }

            this._handleControlButtons();

            if (this.mode === 'receipt') {
                this._toggleScanMessage('scan_products');
            } else if (['delivery', 'inventory'].indexOf(this.mode) >= 0) {
                this._toggleScanMessage('scan_src');
            } else if (this.mode === 'internal') {
                this._toggleScanMessage('scan_src');
            } else if (this.mode === 'no_multi_locations') {
                this._toggleScanMessage('scan_products');
            }

            var $summary_src = this.$('.o_barcode_summary_location_src');
            var $summary_dest = this.$('.o_barcode_summary_location_dest');

            if (this.mode === 'receipt') {
                $summary_dest.toggleClass('o_barcode_summary_location_highlight', true);
            } else if (this.mode === 'delivery' || this.mode === 'internal') {
                $summary_src.toggleClass('o_barcode_summary_location_highlight', true);
            }
        },
        /**
         * Handles the click on the `edit button` on a line.
         *
         * @private
         * @param {jQuery.Event} ev
         */
        _onClickPrintLine: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var id = $(ev.target).parents('.o_barcode_line').data('id');
            console.log('id', id, ' => ', ev);
            this.trigger_up('print_line', {id: id});
        },
    });

    return QuimetalLinesWidget;

});
