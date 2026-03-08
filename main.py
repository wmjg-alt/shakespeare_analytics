"""
main.py
Orchestrator script to run the Shakespeare parsing, NLP, and analytics pipeline.
"""
import json
import logging
import os
import argparse

from src.models import Play
from src.parser import PlayParser
from src.analyzer import PlayAnalyzer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def ensure_dirs(filepath: str):
    """Utility to ensure destination directories exist before writing."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def main():
    parser = argparse.ArgumentParser(description="Shakespeare Parser & Analytics Engine")
    parser.add_argument("-p", "--play", type=str, default="Romeo_and_Juliet",
                        help="Name of the play to process (e.g., Romeo_and_Juliet, Macbeth).")
    parser.add_argument("-r", "--rebuild", action="store_true", 
                        help="Force rebuild both the JSON parse and the NLP CSV from raw text.")
    parser.add_argument("-t", "--top", type=int, default=5,
                        help="Number of characters to display in the top N rankings (default: 5)")
    args = parser.parse_args()

    # Dynamic Path Formatting
    play_id       = args.play
    play_title    = play_id.replace("_", " ") # Converts "Romeo_and_Juliet" to "Romeo and Juliet"
    
    raw_filepath  = os.path.join("data", "raw", f"{play_id}-Shakespeare-raw.txt")
    json_outpath  = os.path.join("data", "processed", f"{play_id}-Parsed.json")
    csv_outpath   = os.path.join("data", "processed", f"{play_id}-Stats.csv")
    report_outpath= os.path.join("data", "reports", f"{play_id}-Report.txt")

    # Upfront Validation: Do we have what we need to run?
    needs_parse = args.rebuild or not os.path.exists(json_outpath)
    if needs_parse and not os.path.exists(raw_filepath):
        logger.error(f"Missing Raw File: Expected to find '{raw_filepath}'.")
        logger.error(f"Ensure your file follows the format: <Play_Name>-Shakespeare-raw.txt")
        return

    # Ensure output directories exist
    for path in [json_outpath, csv_outpath, report_outpath]:
        ensure_dirs(path)

    parsed_play = None

    # ==========================================
    # PHASE 1: TEXT PARSING
    # ==========================================
    if not needs_parse:
        logger.info(f"Found existing {json_outpath}. Loading structural schema...")
        with open(json_outpath, 'r', encoding='utf-8') as f:
            parsed_play = Play.from_dict(json.load(f))
    else:
        p_parser = PlayParser(title=play_title)
        parsed_play = p_parser.parse_file(raw_filepath)
        
        with open(json_outpath, 'w', encoding='utf-8') as f:
            json.dump(parsed_play.to_dict(), f, indent=4)
        logger.info(f"Successfully saved schema to {json_outpath}")

    # ==========================================
    # PHASE 2: NLP ANALYTICS & REPORTING
    # ==========================================
    analyzer = PlayAnalyzer(parsed_play)

    if os.path.exists(csv_outpath) and not args.rebuild:
        # Load entirely from CSV - bypasses NLP / SpaCy!
        analyzer.load_from_csv(csv_outpath)
    else:
        # Run heavy SpaCy extraction
        analyzer.analyze()         
        analyzer.export_csv(csv_outpath)
    
    # Generate parameterized report
    analyzer.generate_report(report_filepath=report_outpath, play_title=play_title, top_n=args.top) 

if __name__ == "__main__":
    main()