# Apple iCloud for Windows (`iCloudPhotos.exe`) — Root-Cause Analysis, Binary Audit & Fix Report

- **Target Binary**: `C:\Program Files\WindowsApps\AppleInc.iCloud_15.10.39.0_x64__nzyj5cx40ttqa\iCloud\iCloudPhotos.exe`
- **Package Version**: `15.10.0.39` (File version `810.14.0.24`, x64)
- **Database**: `%LOCALAPPDATA%\Packages\AppleInc.iCloud_nzyj5cx40ttqa\LocalCache\Local\Apple Inc\iCloudPhotoLibrary\client.db` (`1.75 GB`, `117,543` -> `120,016+` rows in `server_items`)
- **Date**: 2026-10-28

---

## Executive Summary

For 6 years, `iCloudPhotos.exe` consumed **100% of one CPU core continuously**, wrote **60–80 MB of log files per day** (`1.0 GB` accumulated in `LocalCache\Local\Logs`), and stalled synchronization of **5,376 newer photos** (plus thousands more waiting in CloudKit).

Static binary analysis of `iCloudPhotos.exe` (`.rdata` SQL format strings) and forensic inspection of `client.db` revealed **six interacting bugs in Apple's C++ implementation of `WP::SyncDown`**:

1. **Bug #1 — Variadic Format-String Type Mismatch (`%lld` vs `bool`/`int`, CWE-686) Leaking Uninitialized 64-bit Stack/Register Memory into SQLite**:
   In `SaveResourceAndMetadata.cpp`, `CPLMaster` `UPDATE` queries pass `%lld` (64-bit `int64_t`) to `sqlite3_mprintf` for `is_deleted` and `is_expunged` while supplying narrower boolean/integer arguments on the x64 call stack. As a result, 70 rows in `server_items` contained raw 64-bit stack/register garbage in `is_deleted` (e.g. `2512555868161 = 0x249_00000001`) and `is_expunged` (e.g. `648540061696 = 0x97_00000000`).
2. **Bug #2 — Missing `AND asset_id IS NOT NULL` Guard + `WHERE asset_id = NULL` No-Op Update (Infinite Poison-Pill Loop)**:
   The `WP::SyncDown::CreateOrUpdatePlaceholder` work-queue query checks `asset_id IS NOT NULL` for non-deleted items (`is_deleted = 0`), but **omits `AND asset_id IS NOT NULL`** in the `OR (is_deleted = 1 ...)` branch. When orphaned `CPLMaster` rows (`asset_id IS NULL`, `is_deleted = 1`) exist, they are selected at the head of every `LIMIT` batch. When `CreateOrUpdatePlaceholder` attempts to mark them as processed via:
   ```sql
   UPDATE server_items SET is_deleted_locally = 1 WHERE asset_id = NULL
   ```
   SQL `= NULL` evaluates to `UNKNOWN` (0 rows updated). The same 21 `asset_id IS NULL` rows remained at the head of the queue forever, blocking all 5,376 subsequent photos and repeating every 4 seconds.
3. **Bug #3 — Missing SQLite Index on `server_items` Work-Queue Columns (`518.33 ms` Full-Table Scan Every 4s)**:
   `server_items` stores raw serialized CloudKit protobuf/plist blobs (`master_rec BLOB`, `asset_rec BLOB`), inflating the table to **1.75 GB** for 117k items, yet had **no index** on `is_deleted`, `placeholder_processed`, or `is_deleted_locally`. Every 4-second retry loop performed full table scans (`518.33 ms` of pure CPU per query).
4. **Bug #4 — Redundant Index on `fingerprint_paths(fingerprint)` Instead of Indexing `path` (`1,110x` Slowdown)**:
   `fingerprint_paths` (`109,888` rows) defined `PRIMARY KEY(fingerprint, path)` plus a 100% redundant index `CREATE INDEX fingerprint_paths_fingerprint ON fingerprint_paths(fingerprint)`, while omitting an index on `path`. Every local file check (`WHERE fingerprint_paths.path = ?`) scanned all 109,888 rows (`30.60 ms` per file $\times$ 109,884 files = **56 minutes of 100% CPU** on startup).
5. **Bug #5 — Inverted `WHERE '<constant>' IN (master_id, asset_id)` Predicate Defeating B-Tree Seeks (`616.93 ms` Full-Table Scan per Incoming Record)**:
   Once the 6-year queue unblocked and CloudKit resumed delivering new records, `IdentifyCorrectDBRecord` / `SaveMasterRecordToDB` executed:
   ```sql
   SELECT owner_id FROM server_items WHERE '<id>' IN (master_id, asset_id)
   ```
   Placing the string literal on the left side of `IN (master_id, asset_id)` prevented SQLite from using point B-Tree seeks on the unique indexes, forcing a **1.75 GB full-table scan (`616.93 ms`) on every single incoming cloud record**. Adding a compact covering index `idx_server_items_owner_covering ON server_items (master_id, asset_id, owner_id)` allowed SQLite's query planner to use `SCAN server_items USING COVERING INDEX` (~7 MB in L3 cache instead of 1.75 GB), cutting query time from **`616.93 ms` to `25.82 ms` (24x speedup)**.
6. **Bug #6 — Multi-Row `OR` Update Collision (`SQLite[2067]: UNIQUE constraint failed: server_items.asset_id`) in `SaveAssetRecordToDB`**:
   When `SaveAssetRecordToDB` attaches a `CPLAsset` to a `CPLMaster`, it runs:
   ```sql
   UPDATE server_items SET asset_id = '<A>', ...
   WHERE (master_id = '<M>' AND asset_id IS NULL) OR asset_id = '<A>'
   ```
   If an orphaned placeholder row `(master_id = '<M>', asset_id = NULL)` and an existing asset row `(asset_id = '<A>')` both exist in `server_items` simultaneously, **both rows match the `OR` predicate**, causing SQLite to attempt setting the same `UNIQUE` `asset_id` on two rows at once (`Code 19 / 2067: UNIQUE constraint failed: server_items.asset_id`).

---

## Summary of Fixes Applied to `client.db`

| Bug / Bottleneck | Root Cause in `iCloudPhotos.exe` | In-Place SQLite Fix Applied | Measured Result |
| :--- | :--- | :--- | :--- |
| **#1: 64-bit Stack Garbage in Booleans** | `is_deleted=%lld, is_expunged=%lld` in `CPLMaster` `UPDATE` | Normalized 70 rows + installed `trg_sanitize_apple_syncdown_bug_insert/update` | `0` corrupted rows |
| **#2: `WHERE asset_id = NULL` Loop** | Missing `AND asset_id IS NOT NULL` in `is_deleted = 1` branch | Marked 66 `NULL` rows processed + auto-sanitizing triggers | `5,376` blocked photos synced immediately (`todo = 0`) |
| **#3: `CreateOrUpdatePlaceholder` Scan** | Missing index on queue status columns (`1.75 GB` table) | `CREATE INDEX idx_server_items_syncdown_todo` | **`518.33 ms` $\rightarrow$ `2.52 ms` (205x faster)** |
| **#4: `fingerprint_paths` Scan** | Duplicate index on `fingerprint`, no index on `path` | `CREATE INDEX idx_fingerprint_paths_path ON fingerprint_paths(path, fingerprint)` | **`30.60 ms` $\rightarrow$ `0.0276 ms` (1,110x faster)** |
| **#5: `WHERE '<id>' IN (master_id, asset_id)`** | Constant on left of `IN (col1, col2)` forces table scan | `CREATE INDEX idx_server_items_owner_covering ON server_items(master_id, asset_id, owner_id)` | **`616.93 ms` $\rightarrow$ `25.82 ms` (24x faster)** |
| **#6: `UNIQUE constraint failed: asset_id`** | `WHERE (master_id=? AND asset_id IS NULL) OR asset_id=?` matches 2 rows | Purged 9 duplicate null-asset rows + installed `trg_dedup_null_asset_after_insert/update` | `0` constraint errors |
