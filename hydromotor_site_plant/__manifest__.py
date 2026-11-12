{
    'name': 'Hydromotor Sites and Concrete Plants',
    'version': '19.0.1.0.11',
    'license': 'LGPL-3',
    'author': 'Hydromotor',
    'depends': ['sale_margin', 'purchase', 'project', 'hydromotor_machine_sales', 'hydromotor_parts_kits'],
    'data': ['security/security.xml', 'security/ir.model.access.csv', 'models/machine_fields.xml', 'views/views.xml', 'views/quick_order.xml', 'views/sale_margin_views.xml', 'report/location_reports.xml', 'report/amount_labels.xml'],
    'installable': True,
    'application': False,
    'uninstall_hook': 'uninstall_hook',
}
