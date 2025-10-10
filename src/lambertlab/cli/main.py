# cli/main.py
# Set matplotlib backend before any imports to ensure it works in subprocess/headless mode
import sys
import os
print(f"DEBUG main.py: MPLBACKEND env var = {os.environ.get('MPLBACKEND', 'NOT SET')}", file=sys.stderr, flush=True)
import matplotlib
matplotlib.use('Agg', force=True)
print(f"DEBUG main.py: Set matplotlib backend to: {matplotlib.get_backend()}", file=sys.stderr, flush=True)

import argparse
from ..viz.ui import run_em_grid, run_flyby, run_mc_screen, run_emc_chain, run_chain3

def add_common(p):
    p.add_argument("--kernels", action="append", required=True)
    p.add_argument("--outdir", default="artifacts")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--time-scale", choices=["UTC","TDB"], default="TDB")
    p.add_argument("--frame", choices=["J2000","ECLIPJ2000"], default="J2000")
    p.add_argument("--format", choices=["table","json","csv"], default="table")
    p.add_argument("--save", action="store_true")
    p.add_argument("--log-level", default="INFO")

def build_parser():
    ap = argparse.ArgumentParser("lambertlab")
    sp = ap.add_subparsers(dest="cmd", required=True)

    # em-grid
    p1 = sp.add_parser("em-grid"); add_common(p1)
    p1.add_argument("--dep-start", required=True)
    p1.add_argument("--dep-end", required=True)
    p1.add_argument("--dep-step", type=int, default=3)
    p1.add_argument("--tof-min", type=int, required=True)
    p1.add_argument("--tof-max", type=int, required=True)
    p1.add_argument("--tof-step", type=int, default=10)
    p1.add_argument("--dep-id", type=int, default=399)
    p1.add_argument("--arr-id", type=int, default=499)
    p1.add_argument("--c3-cap", type=float, default=None)
    p1.add_argument("--export-csv", action="store_true")
    p1.add_argument("--export-min", action="store_true")

    # flyby
    p2 = sp.add_parser("flyby"); add_common(p2)
    p2.add_argument("--epoch", required=True)
    p2.add_argument("--planet-id", type=int, default=499)
    p2.add_argument("--target-id", type=int, required=True, help="Target body NAIF ID for post-flyby trajectory")
    p2.add_argument("--mu", type=float, default=None)
    p2.add_argument("--r-body", type=float, required=True)
    p2.add_argument("--alt-min", type=float, default=300.0)
    p2.add_argument("--vinf-in", nargs=3, type=float, required=True, help='"x y z" km/s')
    p2.add_argument("--b-hat", nargs=3, type=float, help='"x y z" unit')
    p2.add_argument("--rp", type=float, default=None)
    p2.add_argument("--use-mock", action="store_true")

    # mc-screen
    p3 = sp.add_parser("mc-screen"); add_common(p3)
    p3.add_argument("--dep-epoch", required=True)
    p3.add_argument("--arr-window", required=True)
    p3.add_argument("--tof-min", type=int, required=True)
    p3.add_argument("--tof-max", type=int, required=True)
    p3.add_argument("--tof-step", type=int, default=10)
    p3.add_argument("--dep-id", type=int, default=499)
    p3.add_argument("--arr-id", type=int, default=20000001)
    p3.add_argument("--c3-cap", type=float, default=None)
    p3.add_argument("--export-csv", action="store_true")

    # emc-chain
    p4 = sp.add_parser("emc-chain"); add_common(p4)
    p4.add_argument("--em-dep-start", required=True)
    p4.add_argument("--em-dep-end", required=True)
    p4.add_argument("--em-dep-step", type=int, default=3)
    p4.add_argument("--em-tof-min", type=int, required=True)
    p4.add_argument("--em-tof-max", type=int, required=True)
    p4.add_argument("--em-tof-step", type=int, default=10)
    p4.add_argument("--min-alt", type=float, default=300.0)
    p4.add_argument("--b-hat-mode", choices=["pro","retro","auto"], default="auto")
    p4.add_argument("--candidates", type=int, default=10)
    p4.add_argument("--mc-tof-min", type=int, required=True)
    p4.add_argument("--mc-tof-max", type=int, required=True)
    p4.add_argument("--mc-tof-step", type=int, default=10)
    p4.add_argument("--use-mock", action="store_true")
    p4.add_argument("--allow-mock", action="store_true")
    p4.add_argument("--export-summary")
    p4.add_argument("--export-csv")

    # chain3 (generic three-body chain)
    p5 = sp.add_parser("chain3", help="Three-body chain: Origin → Flyby → Destination"); add_common(p5)
    p5.add_argument("--dep-body", type=int, required=True, help="Departure body NAIF ID")
    p5.add_argument("--flyby-body", type=int, required=True, help="Flyby body NAIF ID")
    p5.add_argument("--arr-body", type=int, required=True, help="Arrival body NAIF ID")
    p5.add_argument("--dep-window", required=True, help="Departure window start:end (YYYY-MM-DD:YYYY-MM-DD)")
    p5.add_argument("--dep-step", type=int, default=2, help="Departure step in days")
    p5.add_argument("--leg1-tof", required=True, help="Leg 1 TOF min:max:step in days")
    p5.add_argument("--leg2-tof", required=True, help="Leg 2 TOF min:max:step in days")
    p5.add_argument("--rp-bounds", required=True, help="Periapsis bounds min_km:max_km")
    p5.add_argument("--bplane-theta", default="-30:30:7", help="B-plane theta min:max:n in degrees")
    p5.add_argument("--max-solutions", type=int, default=200, help="Maximum solutions to keep")
    p5.add_argument("--dv-tol", type=float, default=100.0, help="DV match tolerance in m/s")
    p5.add_argument("--checkpoint", action="store_true", help="Use checkpointed/resumable computation")
    p5.add_argument("--tile-size", type=int, default=10, help="Tile size for checkpointed mode")
    p5.add_argument("--checkpoint-sec", type=int, default=30, help="Checkpoint heartbeat interval (seconds)")
    p5.add_argument("--resume", action="store_true", default=True, help="Resume from existing checkpoint")

    return ap

def main():
    ap = build_parser()
    args = ap.parse_args()
    if args.cmd == "em-grid":       run_em_grid(args)
    elif args.cmd == "flyby":       run_flyby(args)
    elif args.cmd == "mc-screen":   run_mc_screen(args)
    elif args.cmd == "emc-chain":   run_emc_chain(args)
    elif args.cmd == "chain3":      run_chain3(args)

if __name__ == "__main__":
    main()
