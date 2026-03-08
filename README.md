# Shakespeare Analytics

A Python-based pipeline for parsing, structuring, analyzing, and visualizing raw text files of Shakespearean plays. 

This project reads raw plaintext plays and converts them into a deeply nested Object-Oriented schema (Play -> Act -> Scene -> Turn). Once structured, it runs Transformer-based Named Entity Recognition (NER) via spaCy to map out character networks, calculating who speaks the most, how wordy they are, and who talks about whom.

## Current Features
* **Interactive HTML Dashboard**: A stunning, dark-mode web dashboard (built with Tailwind CSS and Apache ECharts) to visualize character metrics and an interactive force-directed social network graph.
* **Custom Text Parser**: Uses heuristics and contextual line-buffering to safely extract character turns, stage directions, and narrative choruses, while discarding formatting noise.
* **Metadata Injection**: Calculates fractional progress through a scene/act/play for every spoken line.
* **Smart NLP Character Extraction**: Programmatically reads the play's cast to build a dynamic `EntityRuler` *before* the NLP runs, preventing characters like "Lady Capulet" and "Capulet" from bleeding together. 
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
   * **Important Naming Convention:** Ensure your files are named using the format `<Play_Name>-Shakespeare-raw.txt` (e.g., `Romeo_and_Juliet-Shakespeare-raw.txt`).

## Usage

### Generating the Data
Run the main orchestrator to parse the text, run the NLP, and generate the reports:
```bash
# Run Macbeth from scratch, displaying the Top 10 stats
python main.py -p Macbeth -r -t 10

# Load cached statistics for Romeo and Juliet instantly
python main.py -p Romeo_and_Juliet 
```

**Flags:**
* `-p` or `--play`: The formatted name of the play to process (Default: `Romeo_and_Juliet`). 
* `-r` or `--rebuild`: Forces a complete re-parse of the raw text and a fresh NLP pass.
* `-t` or `--top [INT]`: Adjusts the number of top characters displayed in the terminal report (Default: 5).
* `-g` or `--gimmicks`: A space-separated list of "gimmick" or collective characters (Default: `ALL CHORUS`). They track their own spoken stats but ignore incoming mentions to prevent graph clutter.


## Analytical Conceits & Assumptions
To parse historical texts programmatically and extract meaningful analytics, a few design conceits were made:
* **Gimmick / Collective Roles**: "ALL" and "CHORUS" are treated as distinct speaking members of the cast. To prevent the social network graph from clustering wildly around the word "all", these characters are blacklisted from *incoming* mentions. They only appear in the final dataset if they actually speak in that specific play.
* **Titles as Unified Names**: Rather than letting the NLP model split "Thane of Cawdor" into separate entities ("Thane" and "Cawdor"), programmatic rules map royal/noble titles (Thane, Prince, King, Duke, etc.) + "of" + [Place] into single identities. 
* **Plural Auto-Filtering**: If the text mentions "MONTAGUES" or "WITCHES", our script checks if "MONTAGUE" or "WITCH" is in the actual speaking cast. If they are, it drops the pluralized family/group mention entirely to prevent duplicated nodes.

## Data Source & Acknowledgments
The raw plaintext files used in this project are sourced from **[The Complete Works of William Shakespeare](http://shakespeare.mit.edu/)** (hosted by MIT IS&T and operated by *The Tech*). 
* Created by Jeremy Hylton in 1993; source for the text was the Complete Moby™ Shakespeare, public domain. And, of course: Shakespeare.

## License
Distributed under the MIT License. See `LICENSE` for more information.
