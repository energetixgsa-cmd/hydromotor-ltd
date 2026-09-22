{
    "name": "Hydromotor Bilingual PDF Naming",
    "version": "19.0.1.0.3",
    "summary": "Bulgarian/English PDF filenames and document user names based on partner language",
    "category": "Hidden/Tools",
    "author": "Hydromotor OOD",
    "license": "LGPL-3",
    "depends": ["sale", "account", "stock", "purchase"],
    "data": [
        "views/res_users_views.xml",
        "views/report_user_names.xml",
        "data/report_actions.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
