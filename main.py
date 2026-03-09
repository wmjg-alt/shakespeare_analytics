"""
main.py
CLI Orchestrator for the Shakespeare Analytics & SRT Extraction Pipeline.
Run `python main.py -h` for full usage instructions.
"""
import argparse
import logging
from src.pipelines import run_parse, run_extract
from src.srt_utils import shift_srt_timestamps
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    parser = argparse.ArgumentParser(
        description="Shakespeare Analytics Data Engine. Parses raw text, runs NLP, and extracts film SRT timestamps."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available sub-commands")

    # Command 1: parse
    parse_cmd = subparsers.add_parser("parse", help="Parse a raw play script and generate NLP stats/reports.")
    parse_cmd.add_argument("-p", "--play", required=True, help="Play ID (e.g. Romeo_and_Juliet)")
    parse_cmd.add_argument("-r", "--rebuild", action="store_true", help="Force rebuild JSON and NLP CSV from scratch")
    parse_cmd.add_argument("-t", "--top", type=int, default=5, help="Number of Top N characters to print in report")
    parse_cmd.add_argument("-g", "--gimmicks", nargs="*", default=["ALL", "CHORUS"], help="Roles ignored by incoming mentions")

    # Command 2: extract
    extract_cmd = subparsers.add_parser("extract", help="Extract scene Start/End timestamps from all available film SRTs.")
    extract_cmd.add_argument("-p", "--play", required=True, help="Play ID to extract timestamps for")

    # Command 3: all
    all_cmd = subparsers.add_parser("all", help="Run 'parse' and then 'extract' consecutively.")
    all_cmd.add_argument("-p", "--play", required=True, help="Play ID to run the full pipeline on")
    all_cmd.add_argument("-r", "--rebuild", action="store_true", help="Force rebuild JSON and CSV during parse")
    all_cmd.add_argument("-t", "--top", type=int, default=5, help="Top N characters")
    all_cmd.add_argument("-g", "--gimmicks", nargs="*", default=["ALL", "CHORUS"])

    # Command 4: util
    util_cmd = subparsers.add_parser("util", help="Utility tools for fixing and shifting SRT files.")
    util_cmd.add_argument("-p", "--play", required=True, help="Play ID (e.g. Romeo_and_Juliet)")
    util_cmd.add_argument("--shift", nargs=2, metavar=("YEAR", "SECONDS"), help="Shift subtitle timestamps (e.g., 1968 -2.8)")

    args = parser.parse_args()

    # Route to the appropriate pipeline
    if args.command == "parse":
        run_parse(args.play, args.rebuild, args.top, args.gimmicks)
        
    elif args.command == "extract":
        run_extract(args.play)
        
    elif args.command == "all":
        logging.info(f"=== Running Full Pipeline for {args.play} ===")
        run_parse(args.play, args.rebuild, args.top, args.gimmicks)
        run_extract(args.play)
        
    elif args.command == "util":
        srt_dir = os.path.join("data", args.play, "srt")
        if args.shift:
            shift_srt_timestamps(srt_dir, args.play, args.shift[0], float(args.shift[1]))

if __name__ == "__main__":
    main()