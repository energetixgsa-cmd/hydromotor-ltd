{
    'name': 'Hydromotor Sites and Concrete Plants',
    'version': '19.0.1.0.1',
    'license': 'LGPL-3',
    'author': 'Hydromotor',
    'depends': ['project', 'hydromotor_machine_sales', 'hydromotor_parts_kits'],
    'data': ['security/security.xml', 'models/machine_fields.xml', 'views/views.xml'],
    'installable': True,
    'application': False,
    'uninstall_hook': 'uninstall_hook',
}
