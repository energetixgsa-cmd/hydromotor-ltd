{
    'name': 'Hydromotor - Комплекти части за машини',
    'version': '19.0.1.0.0',
    'summary': 'Комплекти резервни части по машина и добавяне към сервизна оферта',
    'author': 'Hydromotor',
    'license': 'LGPL-3',
    'depends': ['hydromotor_service', 'sale_management'],
    'data': [
        'models/definitions.xml',
        'security/access.xml',
        'views/views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'pre_init_hook': 'pre_init_hook',
}
