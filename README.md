# Shakespeare Analytics

A Python-based pipeline for parsing, structuring, and analyzing raw text files of Shakespearean plays. 

This project reads raw plaintext plays and converts them into a deeply nested Object-Oriented schema (Play -> Act -> Scene -> Turn). Once structured, it runs Transformer-based Named Entity Recognition (NER) via spaCy to map out character networks, calculating who speaks the most, how wordy they are, and who talks about whom.

## Current Features
* **Custom Text Parser**: Uses heuristics to safely extract character turns, stage directions, and narrative choruses, while discarding formatting noise.
* **Metadata Injection**: Calculates fractional progress through a scene/act/play for every spoken line.
* **NLP Character Extraction**: Identifies mentioned characters dynamically, filtering out historical text hallucinations (e.g., "dost", "hath", "ho").
* **Relational Mapping**: Generates a many-to-many relationship dictionary of character mentions.
* **Data Caching**: Bypasses heavy NLP processing on subsequent runs by saving and loading states directly from CSV.

## Future Roadmap
We plan to expand this pipeline to support:
* **Multi-Play Comparisons**: Analyzing word counts and character dynamics across multiple works.
* **Data Visualization**: Generating node-graphs of character relationships and timeline plots of scene densities.
* **Media Syncing**: Parsing film subtitle files (SRT) to map the text schema to exact movie timestamps.

## Setup & Installation

1. Create a conda environment and install dependencies:
   ```bash
   conda create -n shakespeare_env python=3.10 -y
   conda activate shakespeare_env
   pip install -r requirements.txt
   ```
2. Download the spaCy Transformer model:
   ```bash
   python -m spacy download en_core_web_trf
   ```
3. Place your raw play text (e.g., `Romeo_and_Juliet-Shakespeare-raw.txt`) into `data/raw/`.

## Usage
Run the main orchestrator to parse the text, run the NLP, and generate the reports:
```bash
python main.py
```

**Flags:**
* `-r` or `--rebuild`: Forces a complete re-parse of the raw text and a fresh NLP pass.
* `-t` or `--top[INT]`: Adjusts the number of top characters displayed in the terminal report (default is 5).

Example: `python main.py -r -t 10`
