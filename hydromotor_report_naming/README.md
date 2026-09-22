## Поправка 19.0.2.0.1
Заглавието на колоната в PDF се избира директно от езика на документа: „Артикулен номер“ за bg и „Article Number“ за останалите езици. След Upgrade генерирайте PDF отново; старите изтеглени файлове не се променят.

# Hydromotor Bilingual PDF Naming — 19.0.2.0.0

Актуализация на съществуващия модул `hydromotor_report_naming` за Odoo 19.0.

## Какво се променя

- Отделна колона „Артикулен номер“ (EN: Article Number), взета от вътрешната референция на избрания вариант на продукта.
- Колоната се показва в списъците с продукти/варианти, офертите и поръчките за продажба, покупките, редовете на фактурите, складовите движения, подробните операции и наличностите.
- Добавена е в стандартните PDF оферта/поръчка/проформа, фактура/кредитно известие, покупка/запитване, доставка и складова операция. Покрити са комплектите, секциите, обобщените доставки, серийните номера и остатъчните доставки.
- Стандартното генерирано име на продукта е без добавен `[код]`; Odoo продължава да определя вариантите, езика и доставчическото наименование и да проверява достъпа.
- Търсенето по вътрешна референция/баркод използва оригиналните методи на Odoo.
- Старите описания се показват без точния начален `[текущ артикулен номер] `, като останалият текст се запазва. Не се премахват произволни скоби, различни доставчически кодове или кодове, които са част от действителното име. Секциите и бележките се запазват.
- Българските и английските имена на PDF файловете и новите двуезични имена на потребителите от версия 19.0.1.0.3 се запазват.

## Качване без объркване на папките

1. Разархивирайте архива. Вътре има една папка `hydromotor_report_naming` с целия актуализиран модул.
2. Първо използвайте development клона. В основната папка на GitHub репото изберете Add file → Upload files и плъзнете ЦЯЛАТА папка `hydromotor_report_naming`, без да отделяте файловете от нея.
3. Преди Commit проверете показаните пътища. Трябва да започват с `hydromotor_report_naming/`, например `hydromotor_report_naming/__manifest__.py` и `hydromotor_report_naming/views/article_reference_views.xml`.
4. След билда в Odoo → Приложения намерете `hydromotor_report_naming` / Hydromotor Bilingual PDF Naming и използвайте Upgrade / Надграждане. Ако модулът още не е инсталиран, използвайте Activate.
5. Обновете браузъра с Ctrl+F5, за да зареди новия JavaScript.
6. Проверете примерен артикул, оферта с бележка и секция, фактура и доставка. След успешната проверка прехвърлете същата папка в main и надградете модула там.

Не е необходим повторен импорт на продукти. Модулът не прави масова промяна на записаните имена/описания и не променя цени, количества или данъци. Ако изрично редактирате показаното описание, промяната се записва в оригиналното описание на реда.

Вече съхранените PDF прикачени файлове не се преработват. Новият формат се отнася за ново генерирани отчети. Самостоятелни Studio или външни PDF шаблони, които не наследяват стандартните отчети, се нуждаят от отделна проверка в базата. Този пакет не добавя колони в екрана или бележката на Point of Sale и не променя TREMOL/myPOS.

## Проверки

- Използван е действителният механизъм за наследяване на XML от Odoo 19 срещу официалните изгледи: 29 изгледа/отчета, 78 операции.
- Българският PO файл е проверен с действителния PoFileReader на Odoo 19.
- Проверени са Python/JavaScript синтаксисът и случаи за запазване на многострочни описания, скоби, нули и специални знаци в номерата.
- Включени са Odoo тестове за изпълнение с работеща Odoo база.
- В тази среда няма Odoo сървър/PostgreSQL база. Пълна инсталация, браузърен интерфейс и действително PDF генериране не са изпълнени тук; проверката в development е необходимата следваща стъпка.

Изходна версия на проекта: main, commit 4b7b4c38d864021aadb7d36f5f7d67a12167dabc. Файловете models/report_filename.py, models/res_users.py, data/report_actions.xml, views/report_user_names.xml и views/res_users_views.xml са запазени.

## Existing bilingual-user documentation

# Hydromotor Bilingual PDF Naming

Odoo 19 module for dynamic Bulgarian/English PDF filenames and bilingual employee/user names in customer documents.

## Language rule
- Partner language starts with `bg` -> Bulgarian document name
- Any other language -> English document name

## PDF filenames
Examples:
- `Оферта - S00045.pdf` / `Offer - S00045.pdf`
- `Фактура - INV-2026-0045.pdf` / `Invoice - INV-2026-0045.pdf`

## Bilingual user / "Prepared by" names (v19.0.1.0.3)
Each Odoo user gets two optional fields:
- **Document Name (Bulgarian)** - e.g. `Иван Иванов`
- **Document Name (English)** - e.g. `Ivan Ivanov`

The normal Odoo user name remains unchanged. Reports use the partner language and fall back to the normal user name if the corresponding document-name field is empty.

The module enables this report-name context for Sales, Customer Invoices/Credit Notes, Purchase Orders/RFQs and Delivery Notes. It is designed to work automatically when the report prints a user as a many2one field (`t-field="...user_id"`).

If a custom/Studio invoice template explicitly prints `.name` (for example `o.invoice_user_id.name`) instead of the user field, that exact custom template must be adjusted to call `_hm_report_name(...)`; the standard Odoo 19 invoice template does not itself contain a "Prepared by" user line.

## Upgrade
1. Replace the old `hydromotor_report_naming` folder.
2. Push/merge to the Odoo.sh branch.
3. Apps -> Update Apps List.
4. Upgrade **Hydromotor Bilingual PDF Naming**.
5. Open your user -> Preferences -> **Document Names** and fill both fields.
6. Test one Bulgarian partner and one English/foreign partner.

