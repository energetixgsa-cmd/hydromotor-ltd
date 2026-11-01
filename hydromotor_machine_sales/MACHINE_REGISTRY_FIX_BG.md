# Конфигуратор → сервизно досие — локален staging кандидат

**Не е внедрено.** Работно копие на `Testovo`, основа `0475819`.
Няма commit/push, записи в Odoo или включване на адаптера. `x_enabled=False`
остава непроменено в `data/defaults.xml` (noupdate). Кандидатни версии:
`hydromotor_machine_sales=19.0.1.0.7`, `hydromotor_service=19.0.1.0.5`.

## Установена причина от действителния XML

- Настройката за регистъра е изключена: потвърждението умишлено се отказва.
- Общият bridge mapping изисква записваемо продуктово поле, но
  `x_hm_machine.x_product_id` е readonly related `x_lot_id.product_id`.
- `x_lot_id` е required и валидаторът незабавно фиксира идентичност по lot.
  Създаването преди доставка без сериен номер не е представимо коректно.
- Старото сервизно регистриране търси само company/lot и няма връзка с
  предварителния запис по `HM/SOL/<sale_line_id>/<unit_number>`.
- Bridge/source/serial идентичностите нямат уникални DB индекси в модула.

## Точно поведение на кандидата

1. Проверка/публикуване на конфигурацията запазва старите fingerprint и
   release проверки. Само потвърдена продажба със съществуваща активирана
   фирмена настройка за **x_hm_machine** създава досиета.
2. Положително цяло количество N създава N предварителни досиета и N bridge
   връзки със стария ключ `HM/SOL/<line.id>/<1..N>`. Продуктът трябва вече да е
   с `tracking='serial'`; кодът не променя проследяването на артикули.
3. Предварителното досие има име, клиент, дружество, първоначална продажба,
   модел в `x_model_label`, непроменено описание на оборудването в
   `x_hms_quote_description` и състояние в `x_hms_order_state`.
   **Няма фиктивен stock.lot.** `x_product_id` и `x_serial` остават празни
   related полета до действителния lot. Не се измисля гаранционен начален срок.
4. Единствената промяна на бизнес schema е `x_lot_id.required=False`.
   Валидаторът отказва досие без lot, ако то няма configurator source key и
   продажба за същите клиент/дружество. След първия lot старата идентичност
   е неизменяема и lot не може да се премахва. Не са добавени бизнес полета.
5. След стандартния `stock.picking._action_done()` завършените изходящи
   движения със сериен номер се отнасят към **същите** предварителни досиета,
   по пореден bridge номер. Записват се `x_lot_id`, `x_delivery_id`,
   `x_delivery_date`; related продуктът и серийният текст идват от реалния lot.
   Частична доставка оставя останалите досиета предварителни.
6. Ръчното „Регистрирай доставените машини“ използва същия път за конфигурирани
   редове; старият път остава за обикновени неконфигурирани машини.
7. Повторна синхронизация/регистрация не създава нови досиета. Отказ обновява
   само състоянието, не изтрива досие/bridge/serial. Повторно потвърждение със
   същия release използва същите IDs. Връщания към склада не освобождават serial.
   Смяна на машина, препродажба и автоматично сливане не са включени.
8. Вече използван serial в друго досие, липсваща връзка, изтрит target,
   различна фирма/продажба/release или повече доставени serials от досиетата
   отказват операцията, вместо да създават заместители. Odoo транзакцията
   трябва да върне и sale/stock операцията при грешка.
9. UI показва „Предварително досие“, оборудването и състоянието. За source-linked
   досиета lot е readonly в UI — попълва го доставката, не ръчно измислен номер.

## Идемпотентност и достъп

- Обновяване на съществуващия `sale.order.x_hm_sync_revision` + изричен
  `flush_recordset` **преди** търсене/разпределяне сериализира една продажба.
  При REPEATABLE READ конкуренцията се предава на Odoo request retry; няма
  локално повторение със стар snapshot и няма ръчен commit.
- `_register_hook` добавя 3 частични UNIQUE индекса: bridge source, dossier
  source и dossier `(x_company_id, x_lot_id)`. Това са DDL, не SQL бизнес записи.
  Налични дубликати блокират upgrade; няма автоматично почистване/сливане.
- Новият service работи с ACL/record rules на извикващия за поръчка, настройки,
  bridge четене, досие и склад. Само конкретният вътрешен `bridge.create` е със
  sudo, след проверките; няма sudo върху target модела.
- Изисква се реално разрешена комбинация Продажби + Машини и сервиз, и складови
  права за оператора на доставката. Не са разширявани ACL или назначавани роли.
  Предходните sudo в recovered publish/fingerprint guards не са преработвани.
- За native `x_hm_machine` договорът е фиксиран по проверените полета, не по
  произволни mappings; readonly related product не се записва. Други target
  модели се отказват от sync service. Съществуващите optional настройки не
  добавят непроверени полета/гаранционни дати.

## Тестове и граници на доказателството

Локално: `python -m unittest discover -s tests_local -v` — **24/24 PASS**, от
които **15 нови** за dossier bridge и 9 съществуващи catalog regression tests.
`git diff --check` — PASS; парснати са 33 XML server actions и Python файловете.
Новият `tests_local/test_machine_registry.py` изпълнява действителния Python
service и извлечен XML `hm_mapping`, но **ORM, ACL и cursor са doubles**.
Допълнително има статични проверки на wiring/UI/SQL декларациите.
Наблюдавани са RED → GREEN за липсващ bridge service, реален serial към същото
досие, optional lot, XML routing, DB backstop декларации, принудителен flush,
stock hook, readonly product mapping, serial tracking, UI и повреден target.
Покрити са още replay, cancel/reconfirm, частична доставка, конфликтен serial,
забранен ACL, чуждо дружество и изключен адаптер.

`hydromotor_machine_sales/tests/test_machine_registry.py` съдържа **4 реални
Odoo TransactionCase теста, НЕИЗПЪЛНЕНИ тук**: sale/cancel/reconfirm, стандартна
stock доставка + ръчен replay, PostgreSQL unique source и повторен registry hook.
`importlib.util.find_spec('odoo')` върна False. Python/XML синтаксисът е проверен;
това не доказва реален registry, PostgreSQL, ACL или stock lifecycle.

## Задължителни staging проверки преди приемане

1. Backup/restore план, само изолирана staging test DB. Upgrade **на двата**
   модула; само версия на machine_sales не обновява service XML/schema.
2. Проверка за съществуващи дубликати и PostgreSQL индекси; при конфликт — стоп,
   без автоматично изтриване. Cold registry load и повторен setup на manual models.
3. Изпълнение с Odoo test runner, например върху изрично избрана disposable DB:
   `odoo-bin -d <disposable-test-db> -u hydromotor_service,hydromotor_machine_sales --test-enable --test-tags hm_machine_registry --stop-after-init`.
   Това е инструкция за одобрен staging оператор, не изпълнена команда тук.
4. Проверка с действителните sales/service/stock потребители, не само admin;
   целеви count, source keys, dossier IDs, serial, related product и delivery read-back.
5. Истински две едновременни заявки: confirm/sync, manual registration срещу
   stock completion, две частични доставки. След retry точно N dossiers и N
   bridges, всеки serial еднократно. Моковете/индекс декларациите **не доказват**
   успешен PostgreSQL race тест.
6. Отказ, replay, backorder, връщане, опит за различен release и rollback при
   конфликт. Изключването на x_enabled не премахва досиета и не е schema rollback.

Rollback след реално създадени предварителни досиета изисква backup restore или
отделна миграция; прост revert към required lot ще е несъвместим с тях.
Не се препоръчва production deployment преди горните проверки.
