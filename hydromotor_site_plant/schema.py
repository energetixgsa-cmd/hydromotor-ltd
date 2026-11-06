"""DDL only: composite foreign keys guard cross-company races and reparenting."""
from psycopg2 import sql

# Fixed identifiers only. No caller-controlled SQL or business SQL writes.
REFERENCES = [
    ('hm_concrete_plant', 'project_id,company_id', 'project_project', 'id,company_id'),
    ('hm_machine_assignment', 'project_id,company_id', 'project_project', 'id,company_id'),
    ('hm_machine_assignment', 'plant_id,project_id,company_id', 'hm_concrete_plant', 'id,project_id,company_id'),
    ('sale_order', 'hm_target_project_id,company_id', 'project_project', 'id,company_id'),
    ('sale_order', 'hm_target_plant_id,hm_target_project_id,company_id', 'hm_concrete_plant', 'id,project_id,company_id'),
    ('sale_order_line', 'hm_target_project_id,company_id', 'project_project', 'id,company_id'),
    ('sale_order_line', 'hm_target_plant_id,hm_target_project_id,company_id', 'hm_concrete_plant', 'id,project_id,company_id'),
]
INDEXES = [('hm_site_project_company_unique', 'project_project', 'id,company_id'),
           ('hm_site_plant_scope_unique', 'hm_concrete_plant', 'id,project_id,company_id')]


def install_scope(cr):
    for name, table, columns in INDEXES:
        cr.execute(sql.SQL('CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} ({})').format(
            sql.Identifier(name), sql.Identifier(table), sql.SQL(columns)))
    for i, (table, columns, target, keys) in enumerate(REFERENCES):
        name = 'hm_site_scope_' + str(i)
        cr.execute('SELECT 1 FROM pg_constraint WHERE conname=%s AND conrelid=%s::regclass', [name, table])
        if not cr.fetchone():
            cr.execute(sql.SQL('ALTER TABLE {} ADD CONSTRAINT {} FOREIGN KEY ({}) REFERENCES {} ({}) ON DELETE RESTRICT ON UPDATE RESTRICT').format(
                sql.Identifier(table), sql.Identifier(name), sql.SQL(columns), sql.Identifier(target), sql.SQL(keys)))


def uninstall_hook(env):
    for i, (table, *_rest) in enumerate(REFERENCES):
        env.cr.execute(sql.SQL('ALTER TABLE IF EXISTS {} DROP CONSTRAINT IF EXISTS {}').format(sql.Identifier(table), sql.Identifier('hm_site_scope_'+str(i))))
    for name, *_rest in reversed(INDEXES):
        env.cr.execute(sql.SQL('DROP INDEX IF EXISTS {}').format(sql.Identifier(name)))
