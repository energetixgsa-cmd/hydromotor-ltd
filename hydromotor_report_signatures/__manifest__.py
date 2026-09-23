{
    "name": "Hydromotor Report Signatures",
    "version": "19.0.1.0.0",
    "summary": "Bilingual signature blocks for Hydromotor invoices and quotations",
    "author": "Hydromotor",
    "license": "LGPL-3",
    "depends": ["account", "sale"],
    "post_init_hook": "post_init_hook",
    "data": [
        "views/res_users_views.xml",
        "report/report_invoice_signatures.xml",
        "report/report_sale_signatures.xml",
    ],
    "installable": True,
    "application": False,
}
