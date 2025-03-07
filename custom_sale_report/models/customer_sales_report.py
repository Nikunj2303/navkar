from odoo import models, fields, tools, api


class CustomerSalesReport(models.Model):
    _name = "customer.sales.report"
    _description = "Customer Sales Report"
    # _auto = False

    order_id = fields.Many2one("sale.order", string="Order")
    order_date = fields.Datetime("Order Date")
    partner_id = fields.Many2one("res.partner", string="Customer")
    product_id = fields.Many2one("product.product", string="Product")
    product_uom_qty = fields.Float("Quantity Sold")
    price_unit = fields.Float("Unit Price")
    price_subtotal = fields.Float("Subtotal")
    invoice_id = fields.Many2one("account.move", string="Invoice")
    invoice_date = fields.Date("Invoice Date")
    invoice_amount = fields.Float("Invoiced Amount")
    delivery_id = fields.Many2one("stock.picking", string="Delivery")
    delivery_date = fields.Date("Delivery Date")
    delivered_qty = fields.Float("Delivered Quantity")
    salesperson_id = fields.Many2one("res.users", string="Salesperson")

    # partner_id = fields.Many2one("res.partner", string="Customer")
    # date_from = fields.Date("Start Date")
    # date_to = fields.Date("End Date")
    # user_id = fields.Many2one("res.users", string="Salesperson")

    # @api.model
    # def populate_sales_report(self):
    #     self.search([]).unlink()
    #
    #     sale_details = self.env["sale.details.wiz"].search([])
    #     print("\nself")
    #     if not sale_details:
    #         return False
    #
    #     for record in sale_details:
    #         self.create({
    #             "order_id": record.sale_order_id.id,
    #             "order_date": record.order_date,
    #             "partner_id": record.sale_order_id.partner_id.id if record.sale_order_id else False,
    #             "product_id": record.product_template_id.product_variant_id.id if record.product_template_id else False,
    #             "product_uom_qty": record.product_uom_qty,
    #             "price_unit": record.price_unit,
    #             "price_subtotal": record.price_subtotal,
    #             "invoice_id": record.invoice_id.id,
    #             "invoice_date": record.invoice_date,
    #             "invoice_amount": record.invoice_amount,
    #             "delivery_id": record.delivery_id.id,
    #             "delivery_date": record.delivery_date,
    #             "delivered_qty": record.delivery_qty,
    #             "salesperson_id": record.sale_order_id.user_id.id if record.sale_order_id else False,
    #         })
    #     return True
    #
    # def action_generate_report(self):
    #     self.populate_sales_report()
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'reload',
    #     }

    def _query(self):
        # Generates the SQL query to fetch sales data from sale.details.wiz
        return f"""
            SELECT {self._select_sale_details()}
            FROM {self._from_sale_details()}
            WHERE {self._where_sale_details()}
            GROUP BY {self._group_by_sale_details()}
        """

    def _select_sale_details(self):
        # Defines the fields to be fetched from sale.details.wiz
        return f"""
            MIN(w.id) AS id,
            w.sale_order_id AS order_id,
            w.order_date AS order_date,
            so.partner_id AS partner_id,
            pt.id AS product_id,
            w.product_uom_qty AS product_uom_qty,
            w.price_unit AS price_unit,
            w.price_subtotal AS price_subtotal,
            w.invoice_id AS invoice_id,
            w.invoice_date AS invoice_date,
            w.invoice_amount AS invoice_amount,
            w.delivery_id AS delivery_id,
            w.delivery_date AS delivery_date,
            w.delivery_qty AS delivered_qty,
            so.user_id AS salesperson_id
        """

    def _from_sale_details(self):
        # Defines the tables and joins to be used in the report
        return """
            sale_details_wiz w
            LEFT JOIN sale_order so ON w.sale_order_id = so.id
            LEFT JOIN product_template pt ON w.product_template_id = pt.id
        """

    def _where_sale_details(self):
        # Defines filtering conditions
        return "w.sale_order_id IS NOT NULL"

    def _group_by_sale_details(self):
        # Groups the data to avoid duplicates
        return """
            w.sale_order_id,
            w.order_date,
            so.partner_id,
            pt.id,
            w.product_uom_qty,
            w.price_unit,
            w.price_subtotal,
            w.invoice_id,
            w.invoice_date,
            w.invoice_amount,
            w.delivery_id,
            w.delivery_date,
            w.delivery_qty,
            so.user_id
        """

    @property
    def _table_query(self):
        # Returns the SQL query for the report
        return self._query()

    @api.onchange("partner_id", "date_from", "date_to", "user_id", "salesperson_id")
    def _onchange_filter_sales_report(self):
        """Dynamically fetch Sale Order, Delivery, and Invoice details when filters change."""


        self.sale_details_ids = False
        if not self.partner_id:
            self.sale_details_ids = [(5, 0, 0)]

            return


        # Fetch Sale Orders
        domain = [('partner_id', '=', self.partner_id.id)]
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        if self.user_id:
            domain.append(('user_id', '=', self.user_id.id))

        sale_orders = self.env['sale.order'].search(domain)

        # Fetch Deliveries
        delivery_domain = [('partner_id', '=', self.partner_id.id), ('state', '=', 'done')]
        if self.date_from:
            delivery_domain.append(('date_done', '>=', self.date_from))
        if self.date_to:
            delivery_domain.append(('date_done', '<=', self.date_to))

        deliveries = self.env['stock.picking'].search(delivery_domain)

        # Fetch Invoices
        invoice_domain = [('partner_id', '=', self.partner_id.id), ('move_type', '=', 'out_invoice'),
                          ('state', '=', 'posted')]
        if self.date_from:
            invoice_domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            invoice_domain.append(('invoice_date', '<=', self.date_to))

        invoices = self.env['account.move'].search(invoice_domain)

        # Mapping Deliveries and Invoices to Sale Order Lines
        delivery_map = {}
        for delivery in deliveries:
            for move in delivery.move_ids_without_package:
                if move.sale_line_id:
                    delivery_map.setdefault(move.sale_line_id.id, []).append((delivery, move))

        invoice_map = {}
        for invoice in invoices:
            for inv_line in invoice.invoice_line_ids:
                if inv_line.sale_line_ids:
                    for sale_line in inv_line.sale_line_ids:
                        invoice_map.setdefault(sale_line.id, []).append((invoice, inv_line))

        sale_details_list = []

        for so in sale_orders:
            for sol in so.order_line:
                delivery_lines = delivery_map.get(sol.id, [])
                invoice_lines = invoice_map.get(sol.id, [])

                max_lines = max(1, len(delivery_lines), len(invoice_lines))

                for i in range(max_lines):
                    delivery = delivery_lines[i][0] if i < len(delivery_lines) else False
                    invoice = invoice_lines[i][0] if i < len(invoice_lines) else False

                    delivery_qty = delivery_lines[i][1].quantity_done if i < len(delivery_lines) else 0
                    delivery_date = delivery.date_done if delivery else False
                    carrier_id = delivery.carrier_id.id if delivery and delivery.carrier_id else False

                    invoice_qty = invoice_lines[i][1].quantity if i < len(invoice_lines) else 0
                    invoice_amount = invoice_lines[i][1].price_total if i < len(invoice_lines) else 0
                    invoice_date = invoice.invoice_date if invoice else False
                    aj_lr_number = invoice.aj_lr_number if invoice and hasattr(invoice, 'aj_lr_number') else ''
                    aj_lr_date = invoice.aj_lr_date if invoice and hasattr(invoice, 'aj_lr_date') else False

                    sale_details_list.append((0, 0, {
                        'sale_order_id': so.id,
                        'sale_line_reference': f"SL{sol.id}",
                        'order_date': so.date_order,
                        'product_template_id': sol.product_id.product_tmpl_id.id,
                        'product_uom_qty': sol.product_uom_qty,
                        'price_unit': sol.price_unit,
                        'mrp_price': sol.product_id.lst_price,
                        'price_subtotal': sol.price_subtotal,
                        'delivery_id': delivery.id if delivery else False,
                        'delivery_qty': delivery_qty,
                        'delivery_date': delivery_date,
                        'carrier_id': carrier_id,
                        'invoice_id': invoice.id if invoice else False,
                        'invoice_qty': invoice_qty,
                        'invoice_amount': invoice_amount,
                        'invoice_date': invoice_date,
                        'aj_lr_number': aj_lr_number,
                        'aj_lr_date': aj_lr_date
                    }))

        self.sale_details_ids = sale_details_list
