import io
import base64
import xlsxwriter
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    file_name = fields.Char(string="File Name", default="Sale_Order_Report.xlsx")
    file_data = fields.Binary(string="File", readonly=True)

    def action_sales_report(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Report list'),
            'view_mode': 'form',
            'res_model': 'sale.order.report.wizard',
            'context': {'default_partner_id': self.id}
        }
