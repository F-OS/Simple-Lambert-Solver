# cli.py
import argparse
from .viz.ui import run_em_grid, run_flyby, run_mc_screen, run_emc_chain

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

    return ap

def main():
    ap = build_parser()
    args = ap.parse_args()
    if args.cmd == "em-grid":       run_em_grid(args)
    elif args.cmd == "flyby":       run_flyby(args)
    elif args.cmd == "mc-screen":   run_mc_screen(args)
    elif args.cmd == "emc-chain":   run_emc_chain(args)

if __name__ == "__main__":
    main()
