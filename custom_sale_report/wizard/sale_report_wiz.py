from odoo import models, fields, api
import io
import base64
import xlsxwriter


class SaleOrderReportWizard(models.TransientModel):
    _name = 'sale.order.report.wizard'
    _description = 'Export Sale Order Report with Deliveries and Invoices'
    _rec_name = "partner_id"

    partner_id = fields.Many2one("res.partner", "customer")
    sale_details_ids = fields.One2many("sale.details.wiz", "order_id")
    file_name = fields.Char(string="File Name", default="Sale_Order_Report.xlsx")
    file_data = fields.Binary(string="File", readonly=True)
    date_from = fields.Date("From")
    date_to = fields.Date("To")
    user_id = fields.Many2one("res.users", "Salesperson")

    @api.onchange("partner_id", "date_from", "date_to", "user_id")
    def _onchange_filter_so_from_cust(self):
        self.sale_details_ids = False
        if not self.partner_id:
            self.sale_details_ids = [(5, 0, 0)]
            return

        domain = [('partner_id', '=', self.partner_id.id)]

        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        if self.user_id:
            domain.append(('user_id', '=', self.user_id.id))

        sale_orders = self.env['sale.order'].search(domain)

        delivery_domain = [('partner_id', '=', self.partner_id.id), ('state', '=', 'done')]
        if self.date_from:
            delivery_domain.append(('date_done', '>=', self.date_from))
        if self.date_to:
            delivery_domain.append(('date_done', '<=', self.date_to))

        deliveries = self.env['stock.picking'].search(delivery_domain)

        invoice_domain = [('partner_id', '=', self.partner_id.id), ('move_type', '=', 'out_invoice'),
                          ('state', '=', 'posted')]
        if self.date_from:
            invoice_domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            invoice_domain.append(('invoice_date', '<=', self.date_to))

        invoices = self.env['account.move'].search(invoice_domain)

        sale_details_list = []

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

    def button_print_sale_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Sale Order Report")

        headers = [
            "Sale Order", "Order Line", "Date", "Product", "Sale Qty", "Price",
            "MRP", "Subtotal", "Delivery", "Delivery Qty", "Date", "Carrier",
            "Invoice", "Date", "Invoice Qty", "LR Number", "LR Date", "Amount"
        ]

        bold = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})

        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)

        row = 1
        for line in self.sale_details_ids:
            sheet.write(row, 0, line.sale_order_id.name)
            sheet.write(row, 1, line.sale_line_reference)
            sheet.write(row, 2, str(line.order_date))
            sheet.write(row, 3, line.product_template_id.name)
            sheet.write(row, 4, line.product_uom_qty)
            sheet.write(row, 5, line.price_unit)
            sheet.write(row, 6, line.mrp_price)
            sheet.write(row, 7, line.price_subtotal)
            sheet.write(row, 8, line.delivery_id.name)
            sheet.write(row, 9, line.delivery_qty)
            sheet.write(row, 10, str(line.delivery_date) if line.delivery_date else "")
            sheet.write(row, 11, line.carrier_id.name if line.carrier_id else "")
            sheet.write(row, 12, line.invoice_id.name)
            sheet.write(row, 13, str(line.invoice_date) if line.invoice_date else "")
            sheet.write(row, 14, line.invoice_qty)
            sheet.write(row, 15, line.aj_lr_number if line.aj_lr_number else "")
            sheet.write(row, 16, str(line.aj_lr_date) if line.aj_lr_date else "")
            sheet.write(row, 17, line.invoice_amount)
            row += 1

        workbook.close()
        output.seek(0)

        self.file_data = base64.b64encode(output.read())
        self.file_name = "Sale_Order_Report.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=sale.order.report.wizard&id={self.id}&field=file_data&filename={self.file_name}&download=true",
            'target': 'new',
        }


