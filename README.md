# Shakespeare Analytics

A Python-based pipeline for parsing, structuring, and analyzing raw text files of Shakespearean plays. 

This project reads raw plaintext plays and converts them into a deeply nested Object-Oriented schema (Play -> Act -> Scene -> Turn). Once structured, it runs Transformer-based Named Entity Recognition (NER) via spaCy to map out character networks, calculating who speaks the most, how wordy they are, and who talks about whom.

## Current Features
* **Custom Text Parser**: Uses heuristics and contextual line-buffering to safely extract character turns, stage directions, and narrative choruses, while discarding formatting noise.
* **Metadata Injection**: Calculates fractional progress through a scene/act/play for every spoken line.
* **NLP Character Extraction**: Identifies mentioned characters dynamically, filtering out historical text hallucinations (e.g., "dost", "hath", "ho").
* **Relational Mapping**: Generates a many-to-many relationship dictionary of character mentions.
* **Data Caching**: Bypasses heavy NLP processing on subsequent runs by saving and loading states directly from CSV.
* **Multi-Play Support**: Dynamically handles multiple texts as long as they follow the standardized naming convention.

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
3. Place your raw play texts into `data/raw/`. 
   * **Important Naming Convention:** Ensure your files are named using the format `<Play_Name>-Shakespeare-raw.txt` (e.g., `Romeo_and_Juliet-Shakespeare-raw.txt` or `Macbeth-Shakespeare-raw.txt`).

## Usage
Run the main orchestrator to parse the text, run the NLP, and generate the reports:
```bash
python main.py -p Romeo_and_Juliet
```

**Flags:**
* `-p` or `--play`: The formatted name of the play to process (Default: `Romeo_and_Juliet`). Underscores will be automatically parsed into spaces for the reports.
* `-r` or `--rebuild`: Forces a complete re-parse of the raw text and a fresh NLP pass.
* `-t` or `--top [INT]`: Adjusts the number of top characters displayed in the terminal report (Default: 5).

**Examples:**
Run Macbeth from scratch, displaying the Top 10 stats:
```bash
python main.py -p Macbeth -r -t 10
```

Load cached statistics for Romeo and Juliet instantly:
```bash
python main.py -p Romeo_and_Juliet
```

## Data Source & Acknowledgments
The raw plaintext files used in this project are sourced from **[The Complete Works of William Shakespeare](http://shakespeare.mit.edu/)** (hosted by MIT IS&T and operated by *The Tech*). 
* Created by Jeremy Hylton in 1993, this was the Web's first edition of the Complete Works.
* The original electronic source for the text was the Complete Moby™ Shakespeare, which is in the public domain. 

## License
Distributed under the MIT License. See `LICENSE` for more information.
