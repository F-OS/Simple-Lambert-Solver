# Checkpointing System - Technical Documentation

## Overview

The checkpointing system provides **crash-proof, resumable execution** for long-running computations in LambertLab. It uses tile-based parallelization with atomic artifact writes and SQLite-based progress tracking.

## Architecture

### Components

1. **Checkpoint Module** (`src/lambertlab/core/checkpoint.py`)
   - Core infrastructure for checkpointing
   - Atomic file I/O
   - SQLite index database
   - Tile management
   - Progress tracking

2. **Tiled Computation** (`src/lambertlab/flows/chain3_tiled.py`)
   - Implements chain3 using checkpointing
   - Divides work into independent tiles
   - Deterministic per-tile computation
   - Automatic resumability

### Key Features

✅ **Crash Recovery**: If computation fails, rerunning continues from last checkpoint  
✅ **Atomic Writes**: No partial files, either complete or doesn't exist  
✅ **Progress Tracking**: Real-time heartbeats with ETA estimates  
✅ **Reproducibility**: Code hashing, seed tracking, configuration logging  
✅ **Parallelizable**: Tiles are independent (future: multi-process/cluster)  

## Directory Structure

When running a checkpointed computation, the output directory contains:

```
<outdir>/
├── meta.json              # Configuration, code hash, units
├── index.sqlite           # Tile completion index
├── run.state              # Latest progress snapshot
├── tiles/                 # Individual tile outputs
│   ├── chain3_d0000-0049_t0000-0049.csv
│   ├── chain3_d0050-0099_t0000-0049.csv
│   └── ...
├── chain3_solutions.csv       # Merged top solutions
└── chain3_all_solutions.csv   # All solutions (for reference)
```

### File Descriptions

#### `meta.json`
Configuration snapshot and reproducibility metadata:
```json
{
  "created": "2025-10-07T21:10:26",
  "config": { /* all input parameters */ },
  "code_hash": "0b7c77ad...",
  "units": {
    "length": "km",
    "speed": "km/s",
    "time_scale": "TDB",
    "frame": "J2000"
  }
}
```

#### `index.sqlite`
SQLite database tracking tile status:
- Table: `tiles(id, kind, params_json, seed, status, started_at, ended_at, out_path, out_hash, n_records, retry_count, last_error)`
- Statuses: `todo`, `running`, `done`, `error`
- Supports queries for progress, resume, and debugging

#### `run.state`
JSON heartbeat updated every N seconds:
```json
{
  "timestamp": 1759893026.67,
  "iso_time": "2025-10-07T21:10:26",
  "total": 100,
  "done": 45,
  "running": 2,
  "error": 1,
  "todo": 52,
  "progress_pct": 45.0,
  "eta_seconds": 1234.5
}
```

## Usage

### Command Line

Enable checkpointing with the `--checkpoint` flag:

```bash
python -m lambertlab.cli.main chain3 \
  --dep-body 399 \
  --flyby-body 499 \
  --arr-body 20000001 \
  --dep-window 2035-04-01:2035-09-01 \
  --leg1-tof 150:380:10 \
  --leg2-tof 180:600:20 \
  --rp-bounds 3696.2:13396.2 \
  --bplane-theta=-30:30:7 \
  --checkpoint \              # Enable checkpointing
  --tile-size 20 \            # Points per tile dimension
  --checkpoint-sec 30 \       # Heartbeat interval
  --resume \                  # Resume from existing (default: true)
  --outdir results/emc_2035 \
  --save
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--checkpoint` | Enable checkpointed/resumable mode | `false` |
| `--tile-size` | Number of points per tile dimension | `10` |
| `--checkpoint-sec` | Heartbeat update interval (seconds) | `30` |
| `--resume` | Resume from existing checkpoint | `true` |
| `--outdir` | Output directory for artifacts | `artifacts` |

### Resuming a Run

Simply **run the same command again**:

```bash
# Initial run (crashes or interrupted)
python -m lambertlab.cli.main chain3 ... --checkpoint

# Resume run (detects existing progress)
python -m lambertlab.cli.main chain3 ... --checkpoint
```

The system automatically:
1. Loads `index.sqlite`
2. Checks which tiles are `done`
3. Resets any `running` tiles to `todo` (crash recovery)
4. Continues with pending tiles only

## Tiling Strategy

### Chain3 Tiling

For chain3, we tile the **Leg 1 grid** (departure × TOF1):

```
Departure dates:  [t0, t1, t2, ..., tN]
TOF1 values:      [tof0, tof1, ..., tofM]

Grid: N × M points

Tiles: Each tile covers (tile_size × tile_size) points
```

**Example**: 100 departures × 50 TOFs with `tile_size=20`:
- Total points: 5,000
- Tiles created: 15 (⌈100/20⌉ × ⌈50/20⌉ = 5 × 3)
- Each tile: ~20×20 = 400 points

### Tile Characteristics

- **Independent**: Each tile can be computed without others
- **Deterministic**: Same tile + same seed = same results
- **Bounded**: Memory usage per tile is predictable
- **Atomic**: Tile success/failure is all-or-nothing

## Implementation Details

### Atomic Writes

All file writes use atomic rename:

```python
def atomic_write_bytes(path: Path, data: bytes):
    # Write to temporary file in same directory
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())  # Force to disk
        tmp_path = Path(tmp.name)
    # Atomic rename (on same filesystem)
    tmp_path.replace(path)
```

Benefits:
- No partial files visible
- Crash during write = temp file discarded
- Readers never see incomplete data

### Deterministic Seeds

Each tile gets a unique, deterministic seed:

```python
tile_seed = base_seed + tile_index
```

This ensures:
- Same tile always produces same results
- Retries are reproducible
- Different tiles get different random sequences (if needed)

### Progress Tracking

The system tracks:
- **Walltime per tile**: For ETA estimation
- **Records per tile**: For data volume tracking
- **Hash per tile**: For verification
- **Retry count**: For identifying problematic tiles

### Error Handling

When a tile fails:
1. Exception is caught
2. Error message logged to `index.sqlite`
3. Tile marked as `error`
4. `retry_count` incremented
5. Computation continues with next tile

Failed tiles can be:
- Retried (manually reset to `todo`)
- Investigated (check `last_error` in database)
- Excluded from final merge

## Advanced Usage

### Inspecting Progress

Query the SQLite database:

```bash
sqlite3 results/emc_2035/index.sqlite
```

```sql
-- Overall progress
SELECT status, COUNT(*) FROM tiles GROUP BY status;

-- Failed tiles
SELECT id, last_error, retry_count 
FROM tiles 
WHERE status = 'error';

-- Slowest tiles
SELECT id, (ended_at - started_at) as duration_s
FROM tiles
WHERE status = 'done'
ORDER BY duration_s DESC
LIMIT 10;

-- Average tile time
SELECT AVG(ended_at - started_at) as avg_seconds
FROM tiles
WHERE status = 'done';
```

### Manual Recovery

Reset specific tiles:

```sql
-- Reset all error tiles to retry
UPDATE tiles SET status = 'todo', retry_count = 0 
WHERE status = 'error';

-- Reset a specific tile
UPDATE tiles SET status = 'todo' 
WHERE id = 'chain3_d0050-0099_t0000-0049';
```

### Verifying Tile Integrity

Check file hashes match database:

```python
from pathlib import Path
import sqlite3
from lambertlab.core.checkpoint import sha256_file

db = sqlite3.connect('results/emc_2035/index.sqlite')
for row in db.execute("SELECT id, out_path, out_hash FROM tiles WHERE status='done'"):
    tile_id, path, expected_hash = row
    actual_hash = sha256_file(Path(path))
    if actual_hash != expected_hash:
        print(f"MISMATCH: {tile_id}")
```

### Parallelization (Future)

The current implementation is serial, but tiles are designed for parallel execution:

```python
# Future parallel executor
with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:
    futures = {
        ex.submit(process_chain3_tile, tile, config, outdir): tile
        for tile in idx.pending_tiles()
    }
    
    for future in concurrent.futures.as_completed(futures):
        tile = futures[future]
        try:
            result = future.result()
            idx.mark_done(tile.id, ...)
        except Exception as e:
            idx.mark_error(tile.id, str(e))
```

## Reproducibility

### Code Hashing

The system computes SHA256 hash of core modules:

```python
code_modules = [
    'lambertlab/core/lambert_io.py',
    'lambertlab/core/spice_io.py',
    'lambertlab/flows/em_only.py',
    'lambertlab/flows/chain3_tiled.py'
]
code_hash = hash_modules(code_modules)
```

Stored in `meta.json` for:
- Detecting code changes between runs
- Reproducibility documentation
- Version tracking

### Configuration Snapshot

Complete input configuration saved to `meta.json`:
- All CLI arguments
- NAIF body IDs
- Time windows
- TOF ranges
- Physical parameters

### Units and Frames

Explicitly documented:
```json
"units": {
  "length": "km",
  "speed": "km/s",
  "time_scale": "TDB",
  "frame": "J2000"
}
```

## Performance Considerations

### Tile Size Selection

Trade-offs:

**Small tiles** (e.g., 5×5):
- ✅ Fine-grained progress
- ✅ Low memory per tile
- ✅ Better load balancing (parallel)
- ❌ More overhead (file I/O, database updates)

**Large tiles** (e.g., 100×100):
- ✅ Less overhead
- ✅ Fewer files
- ❌ Coarse progress (long waits between updates)
- ❌ Higher memory usage
- ❌ Wasted work if tile fails near end

**Recommended**: 10-50 points per dimension, depending on:
- Point computation time
- Available memory
- Desired heartbeat frequency

### Heartbeat Frequency

`--checkpoint-sec` controls update interval:

**Frequent** (e.g., 10s):
- ✅ Real-time progress visibility
- ❌ More I/O overhead

**Infrequent** (e.g., 300s):
- ✅ Lower overhead
- ❌ Stale progress information

**Recommended**: 30-60 seconds for most runs

### Database Performance

SQLite provides excellent performance for this use case:
- Single writer (main process)
- Frequent reads acceptable
- Lightweight (<1 MB for 1000s of tiles)
- No external dependencies

For very large runs (>100k tiles), consider:
- Batching database commits
- Using Write-Ahead Logging (WAL mode)
- Periodic database vacuuming

## Troubleshooting

### "Database is locked"

If using parallel execution (future):
- Use WAL mode: `PRAGMA journal_mode=WAL;`
- Increase timeout: `sqlite3.connect(..., timeout=30)`

### Tiles stuck in "running" state

After crash, running tiles aren't auto-reset until next run.

Manual reset:
```sql
UPDATE tiles SET status = 'todo' WHERE status = 'running';
```

Or just restart the computation (automatic on startup).

### Missing tile files

If `out_path` in database but file doesn't exist:
```sql
-- Reset tiles with missing files
UPDATE tiles SET status = 'todo', out_path = NULL 
WHERE status = 'done' AND out_path NOT NULL;
```

### Disk space issues

Monitor disk usage:
- Each tile generates a CSV file
- Size depends on solutions found
- Estimate: ~1-10 KB per tile (varies widely)

For large runs, consider:
- Parquet format (more compressed)
- Streaming merge (don't keep all tiles)
- Periodic cleanup of processed tiles

## Best Practices

1. **Test with small parameters first**
   - Use short windows, coarse steps
   - Verify checkpoint/resume works
   - Then scale up

2. **Monitor progress**
   - Check `run.state` periodically
   - Query database for insights
   - Watch for stuck or slow tiles

3. **Keep configs**
   - `meta.json` documents everything
   - Archive with results
   - Enables exact reproduction

4. **Regular backups**
   - Copy `index.sqlite` periodically
   - Tiles are immutable (safe to backup anytime)
   - Worst case: recompute from meta.json

5. **Clean up old runs**
   - Each run creates new directory
   - Archive or delete completed runs
   - Keep `meta.json` for reference

## Future Enhancements

Planned improvements:

- [ ] Multi-process parallelization
- [ ] Distributed execution (cluster/cloud)
- [ ] Parquet output format option
- [ ] Incremental solution merging
- [ ] Web-based progress dashboard
- [ ] Automatic retry of failed tiles
- [ ] Tile dependency graphs (for complex workflows)
- [ ] Compression for tile artifacts

## API Reference

See source code documentation in:
- `src/lambertlab/core/checkpoint.py` - Core infrastructure
- `src/lambertlab/flows/chain3_tiled.py` - Chain3 implementation

---

For examples and usage, see:
- `test_checkpoint_chain3.py` - Demonstration script
- `CHAIN3_GUIDE.md` - User-facing documentation
