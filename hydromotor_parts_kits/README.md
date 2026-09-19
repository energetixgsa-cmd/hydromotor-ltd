# Hydromotor Parts Kits (Odoo 19.0)

Adds reusable spare-parts kits to Hydromotor machine dossiers.

## Workflow
1. Create a kit under **Машини и сервиз -> Комплекти части**.
2. Add products and quantities to the kit.
3. Open a machine dossier and assign one or more allowed kits in **Комплекти части**.
4. Open/create a service job, select a kit, and click **Добави комплекта към офертата**.
5. The module creates/reuses the service quotation and adds the kit products as sale order lines.

The action blocks duplicate insertion of the same kit into the same service job quotation.

## Поправка 19.0.1.0.2 — 19.09.2026

1. Поправен е редът на полетата в models/definitions.xml. Many2one x_kit_id
   вече се създава преди One2many x_line_ids, което го използва като обратна
   връзка. Това отстранява причината за подадения traceback от 17:01:10 GMT:
   Many2one x_kit_id on model x_hm_parts_kit_line does not exist!
2. Поправен е XPath в сервизната заявка: селекцията по преводимото @string
   е заменена със селекция по техническото име на полето x_coverage_note.
3. Премахнати са генерираните __pycache__ файлове от архива.

Запазени са техническото име на модула, XML идентификаторите, моделите,
полетата и съществуващата логика. Не се изискват деинсталиране или изтриване
на данни.

### Поставяне в Odoo.sh Development
1. Разархивирайте пакета. Заменете файловете в съществуващата папка
   hydromotor_parts_kits на Development клона и направете commit.
   Не създавайте второ копие на модула и не качвайте само ZIP файла в Git.
2. Изчакайте успешния build на Odoo.sh и отворете тестовата база на този клон.
3. В Apps намерете hydromotor_parts_kits. При неуспешна предишна инсталация
   изберете Install. Ако вече е инсталиран, изберете Upgrade.
4. Проверете, че се отварят „Комплекти части“, досието на машина и сервизна заявка.
5. В тестовата база създайте комплект с артикул и количество, маркирайте го
   „Активен“, задайте фирма и го свържете с тестова машина. В нейна сервизна
   заявка изберете комплекта и натиснете „Добави комплекта към офертата“.
   Проверете клиента, артикула, количеството и цената. Повторното натискане
   трябва да бъде блокирано като дублиране.

### Проверки и ограничения
Проверени са XML/Python синтаксисът, manifest файловете, вътрешните XML
препратки и последователността на обратната връзка One2many/Many2one.
И двата наследени XPath селектора намират точно един елемент в запазения
Hydromotor_Service_Odoo_19_0_Development.zip. Новият селектор работи и при
преведено заглавие на раздела.
Не е изпълнявана инсталация в работеща Odoo база. Текущият код в Odoo.sh
може да се различава от запазения сервизен архив. Поправката отстранява
установените дефекти; успешната инсталация и работният процес трябва да
се потвърдят в тестовата база.

Източник за правилото за XPath:
https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_ui_view.py
Метод: _valid_inheritance.
