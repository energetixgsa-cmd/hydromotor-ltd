{
    "name": "Hydromotor TREMOL Fiscal",
    "version": "19.0.1.0.0",
    "summary": "TREMOL M23 fiscal receipts from Odoo invoices through ZFPLabServer",
    "author": "Hydromotor",
    "license": "LGPL-3",
    "depends": ["account", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizard/tremol_receipt_wizard_views.xml",
        "views/account_move_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hydromotor_tremol_fiscal/static/src/js/tremol_bridge.js",
            "hydromotor_tremol_fiscal/static/src/xml/tremol_bridge.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

