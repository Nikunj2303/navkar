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

    @api.onchange("partner_id", "date_from", "date_to", "user_id")
    def _onchange_filter_sales_report(self):
        """Dynamically fetch sales report data when filters change."""
        self.order_id = False
        self.order_date = False
        self.product_id = False
        self.product_uom_qty = 0.0
        self.price_unit = 0.0
        self.price_subtotal = 0.0
        self.invoice_id = False
        self.invoice_date = False
        self.invoice_amount = 0.0
        self.delivery_id = False
        self.delivery_date = False
        self.delivered_qty = 0.0
        self.salesperson_id = False

        if not self.partner_id:
            return

        # Fetch Sale Order
        sale_order = self.env["sale.order"].search([
            ("partner_id", "=", self.partner_id.id),
            ("date_order", ">=", self.date_from) if self.date_from else (),
            ("date_order", "<=", self.date_to) if self.date_to else (),
            ("user_id", "=", self.user_id.id) if self.user_id else (),
        ], limit=1)

        if not sale_order:
            return

        sale_line = sale_order.order_line[:1]

        # Fetch Delivery
        delivery = self.env["stock.picking"].search([
            ("partner_id", "=", self.partner_id.id),
            ("state", "=", "done"),
            ("date_done", ">=", self.date_from) if self.date_from else (),
            ("date_done", "<=", self.date_to) if self.date_to else (),
        ], limit=1)

        delivery_qty = sum(delivery.mapped('move_ids_without_package.quantity_done')) if delivery else 0.0

        # Fetch Invoice
        invoice = self.env["account.move"].search([
            ("partner_id", "=", self.partner_id.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", self.date_from) if self.date_from else (),
            ("invoice_date", "<=", self.date_to) if self.date_to else (),
        ], limit=1)

        invoice_amount = sum(invoice.mapped('amount_total')) if invoice else 0.0

        self.update({
            "order_id": sale_order.id,
            "order_date": sale_order.date_order,
            "product_id": sale_line.product_id.id if sale_line else False,
            "delivered_qty": delivery_qty,
            "invoice_amount": invoice_amount,
        })
