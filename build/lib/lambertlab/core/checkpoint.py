"""
Tile-based checkpointing system for long-running computations.

Provides crash-proof, resumable execution with atomic artifact writes.
"""

import json
import time
import hashlib
import sqlite3
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Optional, List, Dict
from contextlib import contextmanager
import pandas as pd
import numpy as np


@dataclass
class Tile:
    """Work unit for tiled computation."""
    id: str
    kind: str  # "leg1", "bplane", "leg2"
    params: Dict[str, Any]
    seed: int
    
    def filename(self) -> str:
        """Generate safe filename for this tile."""
        return f"{self.kind}_{self.id}.csv"


@dataclass
class TileResult:
    """Result of processing a tile."""
    out_path: str
    out_hash: str
    n_records: int
    walltime_s: float


class IndexDB:
    """SQLite-based task index for tracking tile completion."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tiles (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                params_json TEXT NOT NULL,
                seed INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'todo',
                started_at REAL,
                ended_at REAL,
                out_path TEXT,
                out_hash TEXT,
                n_records INTEGER,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON tiles(status)
        """)
        self.conn.commit()
    
    def ensure_tiles(self, tiles: List[Tile]):
        """Register tiles in index if not already present."""
        for tile in tiles:
            self.conn.execute("""
                INSERT OR IGNORE INTO tiles (id, kind, params_json, seed, status)
                VALUES (?, ?, ?, ?, 'todo')
            """, (tile.id, tile.kind, json.dumps(tile.params), tile.seed))
        self.conn.commit()
    
    def pending_tiles(self) -> List[Tile]:
        """Get all tiles that need processing."""
        cursor = self.conn.execute("""
            SELECT id, kind, params_json, seed
            FROM tiles
            WHERE status IN ('todo', 'error')
            ORDER BY id
        """)
        tiles = []
        for row in cursor:
            tiles.append(Tile(
                id=row[0],
                kind=row[1],
                params=json.loads(row[2]),
                seed=row[3]
            ))
        return tiles
    
    def mark_running(self, tile_id: str):
        """Mark tile as currently running."""
        self.conn.execute("""
            UPDATE tiles
            SET status = 'running', started_at = ?
            WHERE id = ?
        """, (time.time(), tile_id))
        self.conn.commit()
    
    def mark_done(self, tile_id: str, out_path: str, out_hash: str, n_records: int):
        """Mark tile as successfully completed."""
        self.conn.execute("""
            UPDATE tiles
            SET status = 'done', ended_at = ?, out_path = ?, out_hash = ?, n_records = ?
            WHERE id = ?
        """, (time.time(), out_path, out_hash, n_records, tile_id))
        self.conn.commit()
    
    def mark_error(self, tile_id: str, error_msg: str):
        """Mark tile as failed."""
        self.conn.execute("""
            UPDATE tiles
            SET status = 'error', ended_at = ?, last_error = ?, retry_count = retry_count + 1
            WHERE id = ?
        """, (time.time(), error_msg, tile_id))
        self.conn.commit()
    
    def reset_running(self):
        """Reset running tiles to todo (for crash recovery)."""
        self.conn.execute("""
            UPDATE tiles
            SET status = 'todo', started_at = NULL
            WHERE status = 'running'
        """)
        self.conn.commit()
    
    def progress_summary(self) -> Dict[str, Any]:
        """Get current progress statistics."""
        cursor = self.conn.execute("""
            SELECT status, COUNT(*) as count
            FROM tiles
            GROUP BY status
        """)
        stats = {row[0]: row[1] for row in cursor}
        
        total = sum(stats.values())
        done = stats.get('done', 0)
        
        # Estimate remaining time
        cursor = self.conn.execute("""
            SELECT AVG(ended_at - started_at) as avg_time
            FROM tiles
            WHERE status = 'done' AND started_at IS NOT NULL AND ended_at IS NOT NULL
        """)
        avg_time = cursor.fetchone()[0] or 0
        
        remaining = total - done
        eta_seconds = remaining * avg_time if avg_time > 0 else None
        
        return {
            'total': total,
            'done': done,
            'running': stats.get('running', 0),
            'error': stats.get('error', 0),
            'todo': stats.get('todo', 0),
            'progress_pct': 100.0 * done / total if total > 0 else 0,
            'eta_seconds': eta_seconds
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def atomic_write_bytes(path: Path, data: bytes):
    """Write bytes to file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        delete=False,
        suffix='.tmp'
    ) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)  # atomic on same filesystem


def atomic_write_csv(df: pd.DataFrame, path: Path):
    """Write DataFrame to CSV atomically."""
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    atomic_write_bytes(path, csv_bytes)


def atomic_write_json(data: Any, path: Path):
    """Write JSON data atomically."""
    json_bytes = json.dumps(data, indent=2).encode('utf-8')
    atomic_write_bytes(path, json_bytes)


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def sha256_string(s: str) -> str:
    """Compute SHA256 hash of string."""
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def hash_modules(module_paths: List[str]) -> str:
    """
    Compute combined hash of Python module files.
    
    Args:
        module_paths: List of module file paths relative to src/
        
    Returns:
        SHA256 hex digest of combined module content
    """
    h = hashlib.sha256()
    for mod_path in sorted(module_paths):
        try:
            # Try to read from src/ directory
            full_path = Path('src') / mod_path
            if not full_path.exists():
                # Fallback to module path as-is
                full_path = Path(mod_path)
            
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    h.update(f.read())
        except Exception:
            # If file doesn't exist, contribute its path to hash
            h.update(mod_path.encode('utf-8'))
    
    return h.hexdigest()


def write_meta(outdir: Path, config: Dict[str, Any], code_modules: List[str]):
    """
    Write run metadata to meta.json.
    
    Args:
        outdir: Output directory
        config: Configuration dictionary
        code_modules: List of module paths to hash for reproducibility
    """
    meta = {
        'created': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'config': config,
        'code_hash': hash_modules(code_modules),
        'units': {
            'length': 'km',
            'speed': 'km/s',
            'time_scale': 'TDB',
            'frame': 'J2000'
        }
    }
    
    atomic_write_json(meta, outdir / 'meta.json')


def write_state(outdir: Path, progress: Dict[str, Any]):
    """
    Write current run state (heartbeat).
    
    Args:
        outdir: Output directory
        progress: Progress dictionary from IndexDB.progress_summary()
    """
    state = {
        'timestamp': time.time(),
        'iso_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
        **progress
    }
    
    atomic_write_json(state, outdir / 'run.state')


def make_tile_id(kind: str, **kwargs) -> str:
    """
    Generate deterministic tile ID from parameters.
    
    Args:
        kind: Tile kind (e.g., 'leg1', 'bplane', 'leg2')
        **kwargs: Parameters that define the tile
        
    Returns:
        Unique tile ID string
    """
    # Sort kwargs for determinism
    param_str = '_'.join(f"{k}{kwargs[k]}" for k in sorted(kwargs.keys()))
    return f"{kind}_{param_str}"


def make_leg1_tiles(
    dep_indices: np.ndarray,
    tof_indices: np.ndarray,
    tile_size: int,
    base_seed: int
) -> List[Tile]:
    """
    Create tiles for Leg 1 (departure → flyby) grid.
    
    Args:
        dep_indices: Array of departure indices
        tof_indices: Array of TOF indices
        tile_size: Number of points per tile dimension
        base_seed: Base random seed
        
    Returns:
        List of Tile objects
    """
    tiles = []
    tile_idx = 0
    
    for i in range(0, len(dep_indices), tile_size):
        for j in range(0, len(tof_indices), tile_size):
            dep_start = i
            dep_end = min(i + tile_size, len(dep_indices))
            tof_start = j
            tof_end = min(j + tile_size, len(tof_indices))
            
            tile_id = make_tile_id(
                'leg1',
                dep_start=dep_start,
                dep_end=dep_end,
                tof_start=tof_start,
                tof_end=tof_end
            )
            
            tiles.append(Tile(
                id=tile_id,
                kind='leg1',
                params={
                    'dep_start': int(dep_start),
                    'dep_end': int(dep_end),
                    'tof_start': int(tof_start),
                    'tof_end': int(tof_end)
                },
                seed=base_seed + tile_idx
            ))
            tile_idx += 1
    
    return tiles


def merge_tile_csvs(tile_dir: Path, output_path: Path, sort_by: Optional[List[str]] = None):
    """
    Merge multiple tile CSV files into a single output.
    
    Args:
        tile_dir: Directory containing tile CSV files
        output_path: Output merged CSV path
        sort_by: Optional list of columns to sort by
    """
    csv_files = list(tile_dir.glob('*.csv'))
    
    if not csv_files:
        # Create empty file
        pd.DataFrame().to_csv(output_path, index=False)
        return
    
    # Read and concatenate
    dfs = [pd.read_csv(f) for f in csv_files]
    merged = pd.concat(dfs, ignore_index=True)
    
    # Sort if requested
    if sort_by and all(col in merged.columns for col in sort_by):
        merged = merged.sort_values(by=sort_by)
    
    # Write atomically
    atomic_write_csv(merged, output_path)


@contextmanager
def checkpoint_context(outdir: Path, config: Dict[str, Any], code_modules: List[str]):
    """
    Context manager for checkpointed computation.
    
    Usage:
        with checkpoint_context(outdir, config, modules) as idx:
            # Create tiles
            tiles = make_tiles(...)
            idx.ensure_tiles(tiles)
            
            # Process tiles
            for tile in idx.pending_tiles():
                result = process_tile(tile)
                idx.mark_done(tile.id, ...)
    
    Args:
        outdir: Output directory
        config: Configuration dictionary
        code_modules: List of module paths for version tracking
        
    Yields:
        IndexDB instance
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Write metadata
    write_meta(outdir, config, code_modules)
    
    # Initialize index
    idx = IndexDB(outdir / 'index.sqlite')
    
    # Reset any running tiles (crash recovery)
    idx.reset_running()
    
    try:
        yield idx
    finally:
        # Final state write
        write_state(outdir, idx.progress_summary())
        idx.close()
