"""
srt_utils.py
Utilities for parsing, shifting, validating, and conforming SRT subtitle files.
"""
import re
import os
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

TIME_PATTERN = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})")

def parse_time(t_str: str) -> timedelta:
    h, m, s_ms = t_str.split(':')
    s, ms = s_ms.split(',')
    return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

def format_time(td: timedelta) -> str:
    if td < timedelta(0):
        td = timedelta(0)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def load_srt(filepath: str) -> list:
    """Reads and strictly validates an SRT file."""
    subtitles =[]
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        blocks = f.read().strip().split('\n\n')
        
    for i, block in enumerate(blocks, 1):
        lines =[line.strip() for line in block.split('\n') if line.strip()]
        if not lines:
            continue
            
        # Validation: Ensure it looks like an SRT block
        if len(lines) < 2:
            logger.error(f"Corrupt SRT Block at index {i} in {filepath}: {block}")
            raise ValueError("SRT file is critically malformed. Halting extraction.")
            
        match = TIME_PATTERN.search(lines[1])
        if match:
            text = " ".join(lines[2:]).strip()
            subtitles.append({
                "start": parse_time(match.group(1)),
                "end": parse_time(match.group(2)),
                "text": text
            })
        else:
            logger.error(f"Malformed timestamp at block {i} in {filepath}: {lines[1]}")
            raise ValueError("SRT timestamp is critically malformed. Halting extraction.")
            
    return subtitles

def shift_srt_timestamps(srt_dir: str, play_id: str, year: str, offset_seconds: float):
    """Shifts the base SRT file for a given year and outputs a -fixed version."""
    input_file = os.path.join(srt_dir, f"{play_id}-{year}.srt")
    output_file = os.path.join(srt_dir, f"{play_id}-{year}-fixed.srt")
    
    if not os.path.exists(input_file):
        logger.error(f"Cannot shift. File not found: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            match = TIME_PATTERN.search(line)
            if match:
                start_time = parse_time(match.group(1)) + timedelta(seconds=offset_seconds)
                end_time = parse_time(match.group(2)) + timedelta(seconds=offset_seconds)
                outfile.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            else:
                outfile.write(line)
    logger.info(f"Successfully shifted by {offset_seconds}s. Saved to {output_file}")

def conform_srt_filenames(srt_dir: str, play_id: str):
    """Extracts years from messy filenames and standardizes them."""
    if not os.path.exists(srt_dir): return
    
    year_pattern = re.compile(r"(19\d{2}|20\d{2})")
    
    for filename in os.listdir(srt_dir):
        if not filename.endswith(".srt"): continue
        if "-fixed" in filename or "-validated" in filename: continue
        if re.match(rf"^{play_id}-\d{{4}}\.srt$", filename): continue
        
        year_match = year_pattern.search(filename)
        if year_match:
            year = year_match.group(1)
            new_name = f"{play_id}-{year}.srt"
            
            old_path = os.path.join(srt_dir, filename)
            new_path = os.path.join(srt_dir, new_name)
            
            # Avoid overwriting if it somehow already exists
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                logger.info(f"Conformed SRT: {filename} -> {new_name}")