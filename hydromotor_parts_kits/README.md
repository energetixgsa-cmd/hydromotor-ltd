# Hydromotor Parts Kits (Odoo 19.0)

Adds reusable spare-parts kits to Hydromotor machine dossiers.

## Workflow
1. Create a kit under **Машини и сервиз -> Комплекти части**.
2. Add products and quantities to the kit.
3. Open a machine dossier and assign one or more allowed kits in **Комплекти части**.
4. Open/create a service job, select a kit, and click **Добави комплекта към офертата**.
5. The module creates/reuses the service quotation and adds the kit products as sale order lines.

The action blocks duplicate insertion of the same kit into the same service job quotation.
