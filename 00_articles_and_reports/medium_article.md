# How an AI Agent Uncovered a Chain of 6-Year-Old C++/SQLite Bugs Burning $1,000 of California Electricity on My Workstation

*When your Ryzen 9 5900X is running autonomous AI coding agents and compiling Rust 24/7, losing two CPU cores to background daemons stops being a minor annoyance—and turns into a systems engineering investigation.*

---

## The Context: Every Core Counts

I use a 12-core / 24-thread **AMD Ryzen 9 5900X** workstation (64 GB RAM) in Marina del Rey, California. Lately, this machine runs at nearly 100% utilization around the clock, driving autonomous AI coding agents and continuous **Rust + CUDA/wgpu** builds. When `rustc` and the MSVC linker are compiling large workspaces non-stop, every hardware thread and every megabyte of L3 cache matters.

Yet for years, every time I opened Task Manager, two background processes were constantly pegging a full logical CPU core at 100% each:

1. **`CompatTelRunner.exe`** (Microsoft Compatibility Appraiser) — stuck in a single-core loop for **4+ days straight** (**100.2 CPU hours** accumulated in a single process).
2. **`iCloudPhotos.exe`** (iCloud for Windows photo sync daemon) — pinning another core at 100% continuously. This issue had lived on my machine for **six years**. Ending the task never helped: Windows DCOM (`-Embedding`) or `iCloudHome.exe` would respawn it within seconds, right back to 100% single-core load.

So I asked my AI coding agent (**Antigravity**) a simple question:
> *"Can you check why `CompatTelRunner.exe` is constantly eating 100% of a core? And while you're at it, audit the workstation for other background waste—and figure out what `iCloudPhotos.exe` has actually been doing on that one core for the last six years."*

What followed was a 15-minute automated forensic investigation across process trees, PE binary `.rdata` sections, and a 1.75 GB SQLite database—uncovering a **chain of six interacting C++ and SQLite bugs**.

---

## Part 1: Resolving the 100-Hour Telemetry Loop (`CompatTelRunner.exe`)

First, the agent inspected the process hierarchy for `CompatTelRunner.exe`:

```text
ProcessId       : 29324
ParentProcessId : 23840 (svchost.exe -k InvSvcGroup -p -s InventorySvc)
CommandLine     : C:\WINDOWS\system32\compattelrunner.exe -m:aeinv.dll -f:UpdateSoftwareInventoryW invsvc
StartTime       : 10/24/2026 2:24:24 AM
Total CPU Time  : 360,728.8 seconds (100.2 hours of 100% single-core burn)
```

`InventorySvc` had triggered `UpdateSoftwareInventoryW` inside `aeinv.dll` at 2:24 AM four days earlier to inventory installed applications, getting bogged down traversing deep developer directories (`target/`, `.git`, `vcpkg`).

Disabling the scheduled tasks under `\Microsoft\Windows\Application Experience\*` and stopping `InventorySvc` immediately freed the first CPU core.

Then the agent turned to the six-year mystery: **`iCloudPhotos.exe`**.

---

## Part 2: Inside `iCloudPhotos.exe` and the 1.75 GB SQLite Database

To understand what `iCloudPhotos.exe` (`v15.10.0.39` / build `810.14.0.24`) was doing, the agent inspected its local package storage under `%LOCALAPPDATA%\Packages\AppleInc.iCloud_nzyj5cx40ttqa\LocalCache\Local\` and found:

1. **1.0 GB of plain-text logs** (`200` log files in `Local\Logs\`), with `iCloudPhotos` writing **64 to 77 MB of logs every single day**.
2. **A 1.75 GB SQLite database (`client.db`)** containing `117,543` rows in `server_items` and `109,888` rows in `fingerprint_paths` for a 109,884-photo library.

In yesterday’s 64 MB log file, a single worker thread (`TID 59072`) was printing the exact same 7 warnings and errors **every 4 seconds, 24 hours a day**:

```text
WARN  WP::SyncDown::CreateOrUpdatePlaceholder WARNING: Asset  has been deleted, but at an unknown bounced name. Another asset B05D0A64-4721-4981-AA45-27F7B604688D is at path C:\Users\...\iCloud Photos\Photos\IMG_6559.HEIC
WARN  WP::SyncDown::CreateOrUpdatePlaceholder WARNING: Asset  has been deleted, but at an unknown bounced name. Another asset 4C2B95A2-5AEB-47F4-A1D1-54B8DE8608F8 is at path C:\Users\...\iCloud Photos\Photos\IMG_6554.MOV
...
ERROR WP::GetPlaceholderInfo Couldn't open file 'C:\Users\...\iCloud Photos\Photos\IMG_7520.MOV' to read placeholder info: 2
ERROR WP::GetPlaceholderInfo Couldn't open file 'C:\Users\...\iCloud Photos\Photos\IMG_7537.DNG' to read placeholder info: 2
```

Notice the double space in `WARNING: Asset  has been deleted`? The asset UUID was **empty (`NULL`)**.

By extracting the SQL format strings from `iCloudPhotos.exe` and inspecting `client.db`, the agent uncovered **six interacting bugs**—four in the local placeholder loop, and two more that immediately surfaced the moment the 6-year floodgate opened:

### 1. Variadic Format-String Mismatch (`%lld` vs. `%d`) Writing Uninitialized Stack Bits into SQLite

When `iCloudPhotos.exe` formats SQL strings via `sqlite3_mprintf`, its `CPLAsset` `UPDATE` statements properly use `%d` for boolean flags:
```sql
UPDATE %Q SET asset_id=%Q, ..., isHidden=%d, is_deleted=%d, is_expunged=%d, has_edits=%d ...
```
However, in `SaveResourceAndMetadata.cpp`, the `CPLMaster` `UPDATE` statements use **`%lld`** (64-bit `int64_t`) for `is_deleted` and `is_expunged`:
```sql
UPDATE %Q SET master_id=%Q, master_etag=%Q, filename=%Q, dataclass_type=%lld, item_type=%Q,
              is_deleted=%lld, is_expunged=%lld, year=%d, creation_date=%f ...
```
On 64-bit Windows, reading a narrower `bool`/`int` argument as `%lld` in a variadic function pulls the upper 32 bits from uninitialized stack/register state. Consequently, 70 rows in `server_items` had corrupted 64-bit integers stored in boolean columns:
- `is_deleted = 2512555868161` (`0x00000249_00000001`)
- `is_expunged = 648540061696` (`0x00000097_00000000`)

### 2. Missing `AND asset_id IS NOT NULL` + `WHERE asset_id = NULL` (The Infinite Poison-Pill Loop)

Every 4 seconds, `WP::SyncDown::CreateOrUpdatePlaceholder` queries `server_items` for pending work:

```sql
SELECT master_id, asset_id, ... FROM server_items
WHERE ((placeholder_processed = 0) AND is_deleted = 0 AND asset_id IS NOT NULL AND master_id IS NOT NULL)
   OR (is_deleted = 1 AND master_id IS NOT NULL AND (is_deleted_locally IS NULL OR is_deleted_locally = 0))
LIMIT %lld
```

Look at the two branches of the `OR`:
- The first branch (`is_deleted = 0`) explicitly checks **`AND asset_id IS NOT NULL AND master_id IS NOT NULL`**.
- The second branch (`is_deleted = 1`) **omits `AND asset_id IS NOT NULL`**.

When an orphaned `CPLMaster` record exists with `asset_id IS NULL` and `is_deleted = 1` (there were 21 such rows starting at `rowid 111043`), it is selected at the very top of the `LIMIT` batch.

`CreateOrUpdatePlaceholder` cannot resolve a local file path for `asset_id = NULL`, and when the cleanup path attempts to mark the record as processed:

```sql
UPDATE server_items SET is_deleted_locally = 1 WHERE asset_id = %Q
```

Because `asset_id` is `NULL`, `WHERE asset_id = NULL` evaluates to `UNKNOWN` in SQL and **updates 0 rows**. Those 21 rows remained permanently at the front of the queue—blocking **5,376 valid newer photos** behind them from ever syncing.

### 3. Missing Index on a 1.75 GB Table (`518.33 ms` per Query)

Because `server_items` stores raw serialized CloudKit records (`master_rec BLOB`, `asset_rec BLOB`), the table occupies **1.75 GB**. Yet there was no index on `(is_deleted, placeholder_processed, is_deleted_locally)`. Every 4-second retry triggered a full 1.75 GB table scan (`518.33 ms` of pure CPU).

### 4. Redundant Index on `fingerprint_paths` Instead of Indexing `path` (`1,110×` Slowdown)

Even more remarkably, look at the schema of `fingerprint_paths` (`109,888` rows):
```sql
CREATE TABLE 'fingerprint_paths' (
    fingerprint TEXT NOT NULL,
    asset_key TEXT,
    path TEXT NOT NULL,
    downloaded_manually INTEGER DEFAULT 0,
    PRIMARY KEY(fingerprint, path)
);
CREATE INDEX 'fingerprint_paths_fingerprint' ON 'fingerprint_paths' (fingerprint);
```
Because `fingerprint` is already the leading column of `PRIMARY KEY(fingerprint, path)`, `fingerprint_paths_fingerprint` is 100% redundant—while **`path` had no index at all**!

Every time `iCloudPhotos.exe` executed `WHERE fingerprint_paths.path = %Q` across a 109,884-file library, SQLite had to scan all 109,888 rows (`30.60 ms` per lookup $\times$ 109,884 files = **56 minutes of 100% single-core CPU**!).

### 5. What Happened When the 6-Year Floodgate Opened: Inverted `WHERE '<id>' IN (master_id, asset_id)` (`616.93 ms` per Photo)

The moment we cleared the 21 stuck rows, `todo` dropped from `5,397` to `0` in under two minutes—and for the first time since 2020, `iCloudPhotos.exe` began pulling down thousands of newer CloudKit records (`117,543` $\rightarrow$ `120,016+` rows).

Immediately, we noticed each incoming cloud record was taking **~600 ms** of CPU time to insert. Inspecting the binary's `SaveMasterRecordToDB` and `IdentifyCorrectDBRecord` functions revealed why:

```sql
SELECT owner_id FROM server_items WHERE '%s' IN (master_id, asset_id)
```

By placing the constant string on the **left** side of `IN (master_id, asset_id)`, the query prevented SQLite from performing a B-Tree point seek on `master_id` or `asset_id`—forcing yet another **1.75 GB full-table scan (`616.93 ms`) on every single incoming photo**!

Even without modifying the binary, we tricked SQLite's query planner into optimizing that exact query by creating a lightweight covering index:
```sql
CREATE INDEX idx_server_items_owner_covering ON server_items (master_id, asset_id, owner_id);
```
Because all three columns referenced by the query now live inside a compact ~7 MB index (instead of the 1.75 GB main table with BLOBs), SQLite automatically switched its plan to `SCAN server_items USING COVERING INDEX`, dropping execution time from **`616.93 ms` to `25.82 ms` (24× faster)**.

### 6. The Multi-Row `OR` Update Collision (`UNIQUE constraint failed: server_items.asset_id`)

As CloudKit records streamed in, the log also revealed `SQLite[2067]: UNIQUE constraint failed: server_items.asset_id` inside `WP::SyncDown::SaveAssetRecordToDB`:

```sql
UPDATE 'server_items' SET asset_id='61165770-...', ...
WHERE (master_id = 'AdkvAAywxbu/...' AND asset_id IS NULL)
   OR asset_id = '61165770-...'
```

Look closely at that `WHERE` clause: if an orphaned master row `(master_id = X, asset_id IS NULL)` and an existing asset row `(asset_id = Y)` **both** exist in `server_items`, the `OR` condition matches **two rows simultaneously** and tries to set both rows to the same `UNIQUE` `asset_id = Y`!

Adding an `AFTER INSERT / UPDATE` deduplication trigger (`trg_dedup_null_asset_after_insert/update`) that automatically purges any leftover `(master_id = X, asset_id IS NULL)` placeholder the instant a non-null `asset_id` arrives eliminated the constraint collision completely.

---

## Part 3: Fixing the Database In-Place (Zero Binary Patches Needed)

Without modifying a single byte of the signed `WindowsApps` binary, the agent repaired the entire chain directly inside `client.db`:

1. **Cleaned the 70 affected rows & 9 duplicate placeholders**: Normalized the 64-bit `is_deleted`/`is_expunged` values back to `0`/`1`, marked the 66 orphaned `asset_id IS NULL` rows as processed, and removed duplicate null-asset rows.
2. **Created the missing B-Tree & Covering Indexes**:
   - `idx_server_items_syncdown_todo` $\rightarrow$ queue query dropped from **`518.33 ms` to `2.52 ms` (205× faster)**.
   - `idx_fingerprint_paths_path` $\rightarrow$ local path lookup dropped from **`30.60 ms` to `0.0276 ms` (1,110× faster)**.
   - `idx_server_items_owner_covering` $\rightarrow$ `WHERE '<id>' IN (master_id, asset_id)` dropped from **`616.93 ms` to `25.82 ms` (24× faster)**.
3. **Installed Self-Healing SQLite Triggers**:
   Added `trg_sanitize_apple_syncdown_bug_insert/update` and `trg_dedup_null_asset_after_insert/update` inside `client.db` so that any future `%lld` boolean write, `asset_id IS NULL` deletion, or duplicate master placeholder is healed automatically inside the SQLite transaction.

---

## Part 4: The Southern California Edison Math—and the Global Scale

Let’s look at what this costs in **Marina del Rey, CA** (where our utility provider is **Southern California Edison — SCE**):

- On an **AMD Ryzen 9 5900X**, a single core pinned at 100% boosts continuously to ~4.9 GHz at ~1.45V, preventing the core, L3 cache, and I/O die from entering deep C-states. At the wall, 1 pinned core adds **~40W** of continuous draw; 2 pinned cores (`iCloudPhotos.exe` + `CompatTelRunner.exe` + background polling) add **~70W** (plus extra A/C cooling load).
- At SCE residential Time-of-Use rates (~**$0.42/kWh** blended, up to **$0.58/kWh** during 4–9 PM peak):
  - **1 pinned core (`iCloudPhotos.exe` alone)**: `~35 kWh/month` $\approx$ **$14.70/month** (**~$176/year**). Over **6 years**, one missing `AND asset_id IS NOT NULL` predicate burned **~2,500 kWh** — roughly **$1,050 of California electricity** on a single workstation!
  - **All cleaned-up background tasks combined**: `~60 kWh/month` $\approx$ **$25/month** (**~$300/year**).

### The Bigger Question for `@Apple` and `@Microsoft`

What bothers me most isn’t even my own electricity bill or the two lost cores on my workstation.

It’s the scale. **Hundreds of millions of people** use Windows and iCloud for Windows every single day. Most of them aren’t systems engineers inspecting `.rdata` sections or running `EXPLAIN QUERY PLAN` on AppX SQLite caches—they just notice their laptop battery dying in two hours, their fans spinning loudly at idle, and assume their computer is getting old.

When a missing `AND asset_id IS NOT NULL`, an inverted `IN (master_id, asset_id)` scan, or a missing index on `fingerprint_paths(path)` runs across millions of machines worldwide for years, that translates into **megawatts of continuous global power waste**. It raises a genuine engineering question for the teams at **Apple** and **Microsoft**: *How do infinite retry loops and unindexed multi-gigabyte SQLite scans slip past client performance telemetry for so many years without raising an alert?*

---

## Before vs. After Workstation Summary

| Metric | Before Audit | After Optimization |
| :--- | :--- | :--- |
| **Idle Background CPU Waste** | **2 full cores pinned at 100%** (24/7) | **0% idle waste** (all 24 threads available for Rust & AI agents) |
| **`CompatTelRunner.exe`** | `100.2 CPU hours` burned in 4 days | Stopped, `InventorySvc` disabled |
| **`iCloudPhotos` Queue Query (`server_items`)** | **`518.33 ms`** (1.75 GB Full Table Scan) | **`2.52 ms`** (**205× faster** via composite index) |
| **`iCloudPhotos` Path Lookup (`fingerprint_paths`)** | **`30.60 ms`** (109,888-row scan per file) | **`0.0276 ms`** (**1,110× faster** via `(path, fingerprint)` index) |
| **`iCloudPhotos` Owner Lookup (`IN (master_id, asset_id)`)** | **`616.93 ms`** (1.75 GB Full Table Scan per record) | **`25.82 ms`** (**24× faster** via covering index) |
| **Stuck iCloud Photos Queue & Collisions** | `5,376` photos blocked + `UNIQUE` collisions | `0` stuck rows; self-healing SQLite triggers active |
| **`iCloudPhotos` Daily Log Spam** | `64–77 MB/day` (`1.0 GB` accumulated) | Resolved |
| **Estimated SCE Electricity Waste (Marina del Rey)** | **~$25/month (~$300/year)** | **$0/month** |

---

## Final Thought: The New Superpower

Going from *"why is my fan loud?"* to extracting SQL queries from a compiled C++ binary, diagnosing six interacting C++/SQLite bugs, and injecting self-healing SQLite triggers took **15 minutes** of conversation with an AI agent.

And here is the most fascinating part: **this superpower is no longer exclusive.** Anyone with access to modern agentic AI tools has this exact capability on their desktop today.

The bottleneck is no longer having the superpower—it’s knowing how to apply it, refusing to accept broken software as "normal," and asking the right questions.
