# `x_catalog_product_id`: search fix / проверка само в staging

## Статус

Локална реализация върху `Testovo`, изходен commit
`19b93ea2d6f96ed53b85e2c4d9afd345f7c3e51d`. Няма commit, push, deploy,
достъп до ключове или промени в бизнес данни. Не е изпълняван Odoo upgrade.
Версията остава `19.0.1.1.0`: patch bump се отлага до успешен реален Odoo 19
integration run. Това не е твърдение за проверен staging deploy.

## Защо този механизъм

Полето и моделът са XML/manual. Не ги заменяме с Python модел и не променяме
`store`, compute, depends или съществуващи записи. Не използваме директен
`_inherit = 'x_hm_parts_kit'`: registry setup пресъздава manual моделите.
Обикновено Python разширение може да липсва при зареждане или да бъде изгубено
при следващото пресъздаване.

Използваме Odoo `_register_hook` на съществуващия Python abstract service,
след създаването на manual моделите/полетата. Той задава callable `Field.search`
само на конкретното поле. Callback получава търсещия recordset и използва неговия
`env`, а не административния env на registry hook. `_unregister_hook` премахва
само собствения callback. Повторният register е идемпотентен. Несъвместимо поле
или чужд search callback водят до явна грешка вместо тихо презаписване.

### Проверени официални източници

Odoo `19.0` source snapshot: `38c403f4401d01738dc8965992b2ee65f046c84a`.
Сравнени SHA-256 на шестте основни изтеглени файла с този commit: всички еднакви.
Това е source verification, НЕ изпълнение на Odoo registry.

- [model_classes.py, 172–177, 301–326, 535–577](https://github.com/odoo/odoo/blob/38c403f4401d01738dc8965992b2ee65f046c84a/odoo/orm/model_classes.py):
  Python extension изисква съществуващ registry модел; manual моделите се
  добавят при setup, а старите custom класове се премахват/пресъздават.
- [loading.py, 588–595](https://github.com/odoo/odoo/blob/38c403f4401d01738dc8965992b2ee65f046c84a/odoo/modules/loading.py#L588):
  `_register_hook` на всеки модел след зареждането.
- [registry.py, 421–425, 509–529](https://github.com/odoo/odoo/blob/38c403f4401d01738dc8965992b2ee65f046c84a/odoo/orm/registry.py#L421):
  unregister/setup/register при повторен setup на готов registry.
- [fields.py, 66–81, 289, 1927–1929](https://github.com/odoo/odoo/blob/38c403f4401d01738dc8965992b2ee65f046c84a/odoo/orm/fields.py#L66):
  `search` приема callable; `determine_domain` го извиква с текущия recordset.
- [domains.py, 956–1055, 1412–1474](https://github.com/odoo/odoo/blob/38c403f4401d01738dc8965992b2ee65f046c84a/odoo/orm/domains.py#L956):
  custom field search, positive/negative fallback, relational display_name и
  empty-pattern правила.
- [fields exports](https://github.com/odoo/odoo/blob/38c403f4401d01738dc8965992b2ee65f046c84a/odoo/fields/__init__.py#L20):
  официален `from odoo.fields import Domain`.
- [ORM 19](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html),
  [Testing 19](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html),
  [CLI 19](https://www.odoo.com/documentation/19.0/developer/reference/cli.html).

## Семантика и сложност

- `_assembly_product` и `_catalog_code` са непроменени: explicit relation има
  предимство, иначе точният case-sensitive Python regex извлича code като текст;
  `default_code = code`, `sale_ok=True`, shared/kit company, текущи ACL/record
  rules, текущ `active_test`, `limit=2`, резултат само при един видим match.
- ID, False, `=`, `!=`, `in`, `not in`, name equality/membership и стандартните
  `like`/`ilike` варианти се поддържат. Неизвестен оператор не става тихо equality.
  Odoo-generated `any`/`not any` product-domain условия се обработват чрез ORM.
- Explicit branch остава native ORM many2one domain. Implicit branch чете само
  достъпни комплекти без explicit relation и с `x_note like 'Възел'`, на keyset
  batches до 200, без общ `search([])` Python scan.
- Точният regex се изпълнява в Python (вкл. Unicode whitespace/digits). Resolve
  се кешира само за текущото търсене по точния `(code, kit_company_id)`.
- Няма `sudo`, direct SQL или business writes в новата реализация. Външният ORM
  search запазва ACL/rules, композиция на domain, order/offset/limit/count.
- Няма stored поле/backfill и съответно няма stale SQL стойност при промяна на
  product code, продажбена допустимост, архивиране, company или duplicates.
- Общият брой candidate комплекти НЕ е ограничен до 200: трябва да се прегледат
  всички marker-bearing implicit кандидати за точна динамична семантика.
  В най-лош случай това е линейно спрямо тях; броят exceptions/cache също може
  да расте. Outer `limit` не отменя тази работа. Не е benchmark-вано на staging.
  За големи каталози е нужен измерен performance gate, не обещание за O(1).
- Съществуващият compute cache и неговите depends не се преработват; при сравнение
  след промени на products тестовете изчистват cache на computed полето.
- `x_catalog_code` остава nonstored/nonsearchable; не е предмет на този patch.

## Тестове и ограничения

Локално (Python standard library):

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests_local -v
```

Тестовете изпълняват реалните нови Python функции/методи, но заместват Odoo base,
ORM searches и Domain с изрично обозначени doubles. Това НЕ доказва SQL,
registry startup, действителни ACL/record rules или UI. RED→GREEN е наблюдаван
за helper, hook, matcher и search-domain callback.

Odoo integration regressions са в `tests/test_catalog_product_search.py`,
импортирани от `tests/__init__.py`. Те сравняват search с `_assembly_product` и
computed field, ползват native explicit many2one като operator oracle, проверяват
динамични edits, duplicates, company, archive/context, ACL/rules, pagination,
metadata и manual registry re-setup. Заедно се пускат и старите quotation tests.

Този Windows host няма Odoo, PostgreSQL CLI/driver или Docker. Опитът за import
на integration теста реално завърши с `ModuleNotFoundError: No module named
'odoo'`; интеграционните тестове НЕ са изпълнени. Syntax/compile и `git diff
--check` не са заместител за тях.

## Точни следващи стъпки — само след одобрение за конкретния staging target

1. Проверете staging URL/database/project/revision; спрете, ако target е
   production. Направете възстановим backup, neutralize на копието (mail,
   payments, webhooks, cron/external integrations). Не пускайте fixture tests
   върху production. Посочените пътища/DB variables трябва да са реалните на
   staging host, не предположени от този локален checkout.
2. За първа проверка използвайте disposable neutralized clone на staging и
   изходния Odoo 19 runtime. Копирайте целия променен addon в неговия addons path;
   не смесвайте стари и нови worker процеси. Няма schema/data migration.
3. В source installation (за package/Odoo.sh използвайте еквивалентния наличен
   executable; не предполагайте несъществуваща Odoo.sh helper команда):

   ```bash
   # ODOO_BIN = реалният executable; ODOO_CONF съдържа addons_path с този checkout.
   # TEST_DB = disposable neutralized clone, НЕ production.
   "$ODOO_BIN" --config "$ODOO_CONF" --database "$TEST_DB" \
     --update hydromotor_parts_kits --test-enable \
     --test-tags /hydromotor_parts_kits --stop-after-init --workers=0 --no-http
   ```

   Изискайте exit 0 И test summary без failures/errors/skips за новия test class.
   Това пуска и съществуващите quotation tests. Същите тестове трябва да минат и
   при fresh install (`--init hydromotor_parts_kits` вместо `--update`, върху
   отделна празна test DB с налични dependencies), за проверка на cold install.
4. След green integration run bump-нете само patch до `19.0.1.1.1`, повторете
   тестовете и прегледайте diff. Едва след отделно одобрение пренесете артефакта
   върху действителния staging, спрете всичките му Odoo workers, изпълнете:

   ```bash
   "$ODOO_BIN" --config "$ODOO_CONF" --database "$STAGING_DB" \
     --update hydromotor_parts_kits --stop-after-init --workers=0 --no-http
   ```

   Стартирайте всички staging workers от еднакъв артефакт. Не се изисква ръчно
   редактиране на `ir.model.fields` или recompute/backfill.
5. Проверете след НОВ процес (cold registry), първо през `odoo-bin shell`:

   ```python
   Kit = env['x_hm_parts_kit']
   assert not Kit._fields['x_catalog_product_id'].store
   assert callable(Kit._fields['x_catalog_product_id'].search)
   assert Kit.fields_get(['x_catalog_product_id'])['x_catalog_product_id']['searchable']
   # Умишлено сменете admin shell env с предварително одобрения service reader.
   Kit = Kit.with_user(APPROVED_SERVICE_READER_ID)
   records = Kit.search([('x_catalog_product_id', '!=', False)], limit=20)
   service = Kit.env['hydromotor.parts.quotation.service']
   assert all(service._assembly_product(kit) for kit in records)
   empty_records = Kit.search([('x_catalog_product_id', '=', False)], limit=20)
   assert all(not service._assembly_product(kit) for kit in empty_records)
   env.cr.rollback()  # shell verification не прави бизнес writes
   ```

   След това упражнете оригиналния read-only API/UI domain
   `[('x_catalog_product_id', '!=', False)]`, False/negative/name domains с
   обичайния ограничен service user, проверете конкретните резултати спрямо
   compute, а не само HTTP 200. Проверете response на всеки worker/cold restart
   и latency при реалния обем. Fixture integration tests остават в disposable DB.
6. Rollback при дефект: спрете всички staging workers, върнете предишния addon
   артефакт и рестартирайте всички. Този patch няма бизнес/data migration;
   старият search дефект ще се върне. Ако междувременно е имало други upgrades,
   използвайте одобрения backup/restore план вместо частично връщане на DB.

Нито една от deployment стъпките по-горе не е изпълнена от този локален patch.
