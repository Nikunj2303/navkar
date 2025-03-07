from odoo import api, fields, models


class SaleDetails(models.TransientModel):
    _name = 'sale.details.wiz'

    sale_order_id = fields.Many2one("sale.order", "Order")
    sale_line_reference = fields.Char("Order Line")
    order_date = fields.Date("Date")
    product_template_id = fields.Many2one("product.template", "Product")
    product_uom_qty = fields.Float("Quantity")
    price_unit = fields.Float("Price")
    mrp_price = fields.Float("MRP")
    price_subtotal = fields.Float("Subtotal")
    delivery_id = fields.Many2one("stock.picking", "Delivery")
    delivery_date = fields.Date("Delivery Date")
    delivery_qty = fields.Float("Delivered Qty")
    carrier_id = fields.Many2one("delivery.carrier", "Carrier")
    invoice_id = fields.Many2one("account.move", "Invoice")
    invoice_date = fields.Date("Invoice Date")
    invoice_qty = fields.Float("Quantity")
    aj_lr_number = fields.Char("LR Number")
    aj_lr_date = fields.Date("LR Date")
    invoice_amount = fields.Float("Invoiced Amount")
    order_id = fields.Many2one("sale.order.report.wizard", "Sale Report", ondelete="cascade")


