"""
pipelines.py
Houses the high-level orchestration logic for parsing, NLP analysis, and SRT extraction.
"""
import os
import json
import glob
import csv
import re
import logging

from src.models import Play
from src.parser import PlayParser
from src.analyzer import PlayAnalyzer
from src.srt_utils import load_srt, shift_srt_timestamps, conform_srt_filenames
from src.srt_mapper import SRTMapper

logger = logging.getLogger(__name__)

def ensure_dirs(filepath: str):
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def get_raw_file(play_dir: str) -> str:
    matches = glob.glob(os.path.join(play_dir, "*raw*.txt"))
    return matches[0] if matches else None

def run_parse(play_id: str, rebuild: bool = False, top_n: int = 5, gimmicks: list = None):
    """Executes the raw text parsing and NLP analysis pipeline."""
    play_title = play_id.replace("_", " ")
    play_dir = os.path.join("data", play_id)
    
    raw_filepath = get_raw_file(play_dir)
    json_outpath = os.path.join(play_dir, f"{play_id}-Parsed.json")
    csv_outpath  = os.path.join(play_dir, f"{play_id}-Stats.csv")
    report_outpath = os.path.join(play_dir, f"{play_id}-Report.txt")
    
    for path in[json_outpath, csv_outpath, report_outpath]:
        ensure_dirs(path)

    needs_parse = rebuild or not os.path.exists(json_outpath)
    
    # 1. Structural Parse
    if needs_parse:
        if not raw_filepath:
            logger.error(f"Missing Raw File: No '*raw*.txt' found in {play_dir}")
            return
        logger.info(f"Parsing raw structural text for {play_title}...")
        parser = PlayParser(title=play_title)
        parsed_play = parser.parse_file(raw_filepath)
        with open(json_outpath, 'w', encoding='utf-8') as f:
            json.dump(parsed_play.to_dict(), f, indent=4)
    else:
        logger.info(f"Loading existing schema from {json_outpath}...")
        with open(json_outpath, 'r', encoding='utf-8') as f:
            parsed_play = Play.from_dict(json.load(f))

    # 2. NLP Analytics
    analyzer = PlayAnalyzer(parsed_play, gimmick_chars=gimmicks)
    if os.path.exists(csv_outpath) and not rebuild:
        analyzer.load_from_csv(csv_outpath)
    else:
        analyzer.analyze()         
        analyzer.export_csv(csv_outpath)
    
    analyzer.generate_report(report_filepath=report_outpath, play_title=play_title, top_n=top_n) 

def run_extract(play_id: str):
    """Executes the SRT Locality-Sensitive Hashing timestamp alignment pipeline."""
    play_dir = os.path.join("data", play_id)
    json_inpath = os.path.join(play_dir, f"{play_id}-Parsed.json")
    srt_dir = os.path.join(play_dir, "srt")
    out_csv = os.path.join(play_dir, f"{play_id}-Timelines.csv")
    
    if not os.path.exists(json_inpath):
        logger.error(f"Cannot extract. Missing parsed JSON: {json_inpath}. Run 'parse' first.")
        return
        
    with open(json_inpath, 'r', encoding='utf-8') as f:
        play_schema = json.load(f)

    if not os.path.exists(srt_dir):
        logger.warning(f"No SRT directory found at {srt_dir}")
        return

    # Conform dirty filenames automatically
    conform_srt_filenames(srt_dir, play_id)

    # Group SRTs by Year to handle -fixed/-validated preferences
    all_srts =[f for f in os.listdir(srt_dir) if f.endswith(".srt")]
    year_groups = {}
    year_pattern = re.compile(r"(19\d{2}|20\d{2})")
    
    for srt in all_srts:
        match = year_pattern.search(srt)
        if match:
            year = match.group(1)
            if year not in year_groups: year_groups[year] = []
            year_groups[year].append(srt)

    preferred_srts = []
    for year, files in year_groups.items():
        fixed_files =[f for f in files if "-fixed" in f or "-validated" in f]
        if fixed_files:
            preferred_srts.append(fixed_files[0])
        else:
            base_files = [f for f in files if f == f"{play_id}-{year}.srt"]
            if base_files: preferred_srts.append(base_files[0])

    if not preferred_srts:
        logger.warning(f"No valid formatted SRT files found in {srt_dir}.")
        return

    combined_results = []
    all_fieldnames = ["Film"]

    for srt_file in preferred_srts:
        srt_path = os.path.join(srt_dir, srt_file)
        logger.info(f"--- Extracting timestamps from {srt_file} ---")
        
        try:
            srt_data = load_srt(srt_path)
            mapper = SRTMapper(play_schema, srt_data)
            film_timeline = mapper.extract_timeline()
            
            film_tag = srt_file.replace('.srt', '')
            print("\n" + "="*50)
            print(f"🎬 ALIGNMENT EXTRACTED: {play_id.replace('_', ' ')} ({film_tag})")
            print("="*50)
            
            row_dict = {"Film": film_tag}
            for key, val in film_timeline.items():
                if key not in all_fieldnames: all_fieldnames.append(key)
                row_dict[key] = val
                
                # Print only Starts for console brevity
                if "Start" in key:
                    end_key = key.replace("Start", "End")
                    end_val = film_timeline.get(end_key, "N/A")
                    scene_name = key.replace(" Start", "")
                    print(f"{scene_name:<15} | Start: {val} -> End: {end_val}")
                    
            print("="*50 + "\n")
            combined_results.append(row_dict)
            
        except ValueError as e:
            logger.error(f"Failed to process {srt_file}: {e}")

    # Write the master combined CSV
    if combined_results:
        with open(out_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_fieldnames)
            writer.writeheader()
            writer.writerows(combined_results)
        logger.info(f"Successfully compiled all films into {out_csv}")