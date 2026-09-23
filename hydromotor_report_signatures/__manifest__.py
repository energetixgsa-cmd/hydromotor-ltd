{
    "name": "Hydromotor Report Signatures",
    "version": "19.0.1.1.0",
    "summary": "Bilingual signatures for invoices, quotations, orders and invoice-style pro-formas",
    "author": "Hydromotor",
    "license": "LGPL-3",
    "depends": ["account", "sale"],
    "post_init_hook": "post_init_hook",
    "data": [
        "views/res_users_views.xml",
        "report/report_invoice_signatures.xml",
        "report/report_sale_signatures.xml",
        "report/report_external_layout_signatures.xml",
        "report/report_proforma_invoice.xml",
    ],
    "installable": True,
    "application": False,
}
