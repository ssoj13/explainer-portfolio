# LinkedIn Post Drafts (Standalone, Decoupled from Medium — Corporate-Safe Engineering Tone)

---

## Option 1 — English (Standalone LinkedIn Post)

My 12-core Ryzen 9 5900X workstation in Marina del Rey runs autonomous AI coding agents and heavy Rust/CUDA builds 24/7. When your machine is compiling non-stop, every CPU thread counts.

For years, two background processes had been quietly pinning a full CPU core at 100% each:
1️⃣ `CompatTelRunner.exe` (which had accumulated 100.2 CPU hours over the last 4 days)
2️⃣ `iCloudPhotos.exe` — a persistent single-core loop that had lived on my machine for 6 years and respawned whenever terminated.

Today I asked my AI coding agent (Antigravity) to audit the workstation and figure out what `iCloudPhotos.exe` was actually doing on that core for the past 6 years.

In 15 minutes, the agent inspected 1.0 GB of local logs, analyzed the 1.75 GB `client.db` SQLite database (117,543 rows), extracted the SQL queries from the binary, and uncovered a chain of **six classic systems bugs**:

🔍 **1. Variadic Format-String Mismatch (`%lld` vs `%d`):** In `SaveResourceAndMetadata.cpp`, `CPLMaster` `UPDATE` queries used `is_deleted=%lld, is_expunged=%lld` (64-bit `int64_t`) in `sqlite3_mprintf` for boolean flags, causing 32 bits of uninitialized stack state to be written into 70 rows of `client.db`.

🔍 **2. The `WHERE asset_id = NULL` Infinite Loop:** In `WP::SyncDown::CreateOrUpdatePlaceholder`, the work-queue query checked `AND asset_id IS NOT NULL` for active photos, but omitted it in the `OR (is_deleted = 1 ...)` branch. When attempting to mark 21 orphaned rows (`asset_id IS NULL`) as processed via `UPDATE server_items SET is_deleted_locally = 1 WHERE asset_id = NULL`, SQL evaluated `= NULL` as `UNKNOWN` (0 rows updated). Those 21 rows stayed at the head of the queue forever—blocking 5,376 newer photos and retrying every 4 seconds.

🔍 **3. Missing Index on a 1.75 GB Table:** `server_items` had no index on those status flags, forcing a 1.75 GB full-table scan (`518.33 ms`) every 4 seconds.

🔍 **4. Indexing the Wrong Column on `fingerprint_paths`:** The table had `PRIMARY KEY (fingerprint, path)` plus a redundant index on `(fingerprint)`, but **no index on `path`**—making every path lookup across 109,884 files take `30.60 ms` instead of `0.027 ms`!

🔍 **5. Inverted `WHERE '<id>' IN (master_id, asset_id)` Scan:** As soon as the 6-year queue unblocked and new cloud records started arriving, we spotted `SELECT owner_id FROM server_items WHERE '<id>' IN (master_id, asset_id)`. Putting the string literal on the left of `IN (col1, col2)` defeated SQLite's B-Tree point seeks, forcing another 1.75 GB scan (`616.93 ms`) per incoming photo.

🔍 **6. Multi-Row `OR` Update Collision (`UNIQUE constraint failed`):** In `SaveAssetRecordToDB`, `UPDATE server_items SET asset_id = Y WHERE (master_id = X AND asset_id IS NULL) OR asset_id = Y` matched *both* an orphaned placeholder row and an existing asset row simultaneously, aborting with `SQLite[2067]: UNIQUE constraint failed`.

⚡ **The Southern California Edison (Marina del Rey) Math & Global Scale:**
Keeping 1–2 cores boosted to 4.9 GHz on a 5900X adds ~40–70W at the wall. At SCE rates (~$0.42–$0.58/kWh), that single stuck loop burned ~$15/month (**~$1,000 of electricity over 6 years**) on one desktop.
More importantly: **hundreds of millions of people** run these tools daily. At global scale, a missing `IS NOT NULL` check or missing SQLite index translates into megawatts of wasted power worldwide. A genuine question for the engineering teams at @Apple and @Microsoft: how do infinite retry loops like this slip past client performance telemetry for years?

🛠️ **Before -> After (Fixed In-Place Inside SQLite Without Touching the Binary):**
✅ Sanitized the 70 affected rows & installed `AFTER INSERT/UPDATE` SQLite triggers so `client.db` self-heals automatically and purges duplicate null-asset placeholders on the fly
✅ Added covering B-Tree indexes:
  • Queue query: **`518.33 ms` → `2.52 ms` (205× faster)**
  • File path lookup: **`30.60 ms` → `0.0276 ms` (1,110× faster)**
  • Owner lookup (`IN (master_id, asset_id)`): **`616.93 ms` → `25.82 ms` (24× faster)** via a 7 MB covering index
✅ Disabled unnecessary telemetry & legacy background services (`~$300/year` saved on the SCE bill, and 2 full cores returned to `rustc`).

💡 **The Takeaway:**
Going from a noisy fan to diagnosing C++ format strings, fixing inverted SQLite query plans, and injecting self-healing triggers took 15 minutes with an AI agent. This superpower is no longer exclusive—anyone can use it today. The bottleneck is no longer having the superpower; it’s knowing how to apply it and what questions to ask.

#SystemsEngineering #RustLang #SQLite #PerformanceEngineering #AIAgents #Windows11 #Apple #Microsoft #SoftwareEngineering

---

## Option 2 — На русском (самодостаточный пост для LinkedIn / Telegram, без отсылок к Medium)

Моя рабочая станция (Ryzen 9 5900X, 64 GB RAM) в Marina del Rey сейчас нагружена 24/7: на ней круглосуточно работают AI-агенты и идут сборки Rust + CUDA/wgpu. Когда компилятор и линкер работают нон-стоп, каждый поток процессора на счету.

Но годами в фоне висели две задачи, каждая из которых постоянно занимала по 100% одного ядра:
1️⃣ `CompatTelRunner.exe` (накопивший 100.2 часа процессорного времени за последние 4 дня).
2️⃣ `iCloudPhotos.exe` — фоновый процесс, который 6 лет подряд грузил одно ядро на 100% и автоматически перезапускался при попытке его закрыть.

Сегодня я попросил своего AI-агента (Antigravity) провести аудит системы и разобраться, что именно `iCloudPhotos.exe` делает на этом ядре все 6 лет.

За 15 минут агент проанализировал 1 ГБ логов, изучил 1.75-гигабайтную базу `client.db` (117 543 строк), извлёк SQL-запросы из бинарника и нашёл цепочку из **шести классических системных багов**:

🔍 **1. Ошибка форматной строки (`%lld` вместо `%d`):** В `SaveResourceAndMetadata.cpp` в запросах обновления `CPLMaster` для булевых флагов `is_deleted` и `is_expunged` в `sqlite3_mprintf` указан спецификатор `%lld` (64-битный `int64_t`) вместо `%d`. Из-за чтения старших 32 бит со стека в 70 строках БД оказались числа вроде `2512555868161`.

🔍 **2. Вечный цикл `WHERE asset_id = NULL`:** В запросе очереди `WP::SyncDown::CreateOrUpdatePlaceholder` в первой ветке `WHERE` есть проверка `AND asset_id IS NOT NULL`, а во второй (`OR is_deleted = 1 ...`) она пропущена. В результате 21 запись с `asset_id IS NULL` всегда попадала в начало `LIMIT`, а запрос `UPDATE server_items SET is_deleted_locally = 1 WHERE asset_id = NULL` в SQL всегда возвращает `UNKNOWN` (0 строк обновлено). Эти 21 строки годами висели в начале очереди, блокируя синхронизацию 5 376 новых фотографий и перезапуская цикл каждые 4 секунды.

🔍 **3. Отсутствие индекса на таблице 1.75 ГБ:** Таблица `server_items` не имела индекса по флагам очереди, из-за чего каждые 4 секунды выполнялся полный скан 1.75 ГБ (`518.33 мс`).

🔍 **4. Дублирующий индекс вместо индекса по `path`:** В таблице `fingerprint_paths` (`109 888` строк) при наличии `PRIMARY KEY (fingerprint, path)` был создан дублирующий индекс по `(fingerprint)`, но **не было индекса по `path`**. Каждый поиск по пути занимал `30.60 мс` вместо `0.027 мс`.

🔍 **5. Инвертированный предикат `WHERE '<id>' IN (master_id, asset_id)`:** Как только шестилетняя пробка рассосалась и с облака полились новые фотографии, всплыл запрос `SELECT owner_id FROM server_items WHERE '<id>' IN (master_id, asset_id)`. Из-за константы слева от `IN (col1, col2)` SQLite не мог использовать точечный B-Tree поиск и снова сканировал все 1.75 ГБ (`616.93 мс`) на каждую новую фотографию!

🔍 **6. Коллизия `UNIQUE constraint failed` на `OR`-обновлении:** Запрос `UPDATE server_items SET asset_id = Y WHERE (master_id = X AND asset_id IS NULL) OR asset_id = Y` в `SaveAssetRecordToDB` при наличии осиротевшей записи с `asset_id IS NULL` и уже существующей записи с `asset_id = Y` пытался присвоить один и тот же `UNIQUE` `asset_id` сразу двум строкам, падая с ошибкой `SQLite[2067]`.

⚡ **Электричество в Калифорнии (Southern California Edison) и глобальный масштаб:**
Два залоченных в бусте ядра на Ryzen 9 5900X — это ~40–70 Вт лишнего потребления 24/7. По тарифам SCE в Marina del Rey (~$0.42–$0.58/кВт·ч) один этот цикл стоил ~$15/месяц (**~$1 000 за 6 лет** на одной рабочей станции).
Но главное даже не моя станция: этими продуктами пользуются **сотни миллионов людей каждый день**. В масштабах планеты один пропущенный `IS NOT NULL` или забытый индекс в SQLite — это мегаватты впустую сжигаемой энергии. Большой риторический вопрос к инженерным командам @Apple и @Microsoft: как такие бесконечные циклы годами проходят мимо внутренней телеметрии производительности?

🛠️ **Before / After (починили прямо внутри SQLite без модификации бинарников):**
✅ Очистили 70 проблемных строк и добавили самовосстанавливающиеся SQLite-триггеры (`AFTER INSERT/UPDATE`), которые на лету чистят мусорные биты и удаляют дублирующиеся `NULL`-заглушки
✅ Добавили покрывающие B-Tree индексы:
  • Запрос очереди: **`518.33 мс` → `2.52 мс` (в 205 раз быстрее)**
  • Поиск по пути файла: **`30.60 мс` → `0.0276 мс` (в 1 110 раз быстрее)**
  • Проверка владельца (`IN (master_id, asset_id)`): **`616.93 мс` → `25.82 мс` (в 24 раза быстрее)** за счёт компактного покрывающего индекса
✅ Отключили лишнюю телеметрию и неиспользуемые службы (+2 свободных ядра под Rust и ~$300/год экономии на счетах SCE).

💡 **Главный вывод:**
Путь от «почему шумит кулер?» до анализа `.rdata` в бинарнике и внедрения самовосстанавливающихся триггеров в SQLite занял 15 минут диалога с агентом. И эта суперспособность сегодня доступна каждому — проблема больше не в том, чтобы получить суперспособность, а в том, как её применять и какие вопросы задавать.
