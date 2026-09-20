{
    'name': 'Hydromotor Machine Catalog BG / EN',
    'author': 'Hydromotor',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['hydromotor_machine_sales'],
    'data': ['data/fields.xml'],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
