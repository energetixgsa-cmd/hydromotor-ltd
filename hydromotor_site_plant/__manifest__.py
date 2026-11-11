{
    'name': 'Hydromotor Sites and Concrete Plants',
    'version': '19.0.1.0.5',
    'license': 'LGPL-3',
    'author': 'Hydromotor',
    'depends': ['purchase', 'project', 'hydromotor_machine_sales', 'hydromotor_parts_kits'],
    'data': ['security/security.xml', 'security/ir.model.access.csv', 'models/machine_fields.xml', 'views/views.xml', 'views/quick_order.xml', 'report/location_reports.xml', 'report/amount_labels.xml'],
    'installable': True,
    'application': False,
    'uninstall_hook': 'uninstall_hook',
}
