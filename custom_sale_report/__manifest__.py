{
    "name": "Sale Order Report",
    "version": "1.0",
    "summary": "Provides details of Sale Orders, Delivery Orders, and Invoices",
    "description": """
        This module fetches and displays all related details of Sale Orders,
        including their Delivery Orders and Invoice Orders.
    """,
    "author": "Entrivis Tech Pvt. Ltd.",
    "website": "https://entrivistech.com",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": ["base", "sale", "stock", "account", "delivery", "spreadsheet_dashboard"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "wizard/sale_order_report.xml",
        "views/customer_sales_report.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
