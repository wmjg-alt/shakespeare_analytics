# Shakespeare Analytics

A Python-based pipeline for parsing, analyzing, and visually graphing raw text files of Shakespearean plays, alongside an engine for extracting chronological alignment data from film adaptations (SRT syncing).

## Features & Architecture

### 1. Text Parsing & NLP Character Analytics
* **Custom Heuristic Parser**: Safely extracts structural schemas (Play -> Act -> Scene -> Turn) from plaintext plays, injecting completion percentages into every spoken line.
* **Pre-NER Dynamic Aliasing**: Reads the exact speaking cast and dynamically injects them into a SpaCy `EntityRuler` before the NLP runs. This prevents names like "Lady Capulet" and "Capulet" from fragmenting.
* **Relational Node Mapping**: Generates a many-to-many JSON-formatted interaction dictionary to track which characters mention others the most.

### 2. Film SRT Alignment (Timestamp Extraction)
Instead of brute-force string matching, this project utilizes **Locality-Sensitive Hashing (LSH)** and **Density Clustering** to cross-reference script text against movie subtitles:
* **The Algorithm**: The play script is chunked into overlapping 20-word n-grams. The SRT file is grouped into sliding 4-subtitle windows. Both are MinHashed and queried against an LSH index.
* **Density Clustering**: Because films skip lines or rearrange dialogue, the LSH index returns hundreds of fuzzy matches. A density-clustering algorithm groups matches by timestamp proximity. The dense cluster identifies the true location of the scene.
* **Flat Output**: Compiles all film timelines into a single `PlayID-Timelines.csv` (e.g., 1936, 1968, 1996) for easy multi-film comparison.

### 3. Interactive Web Dashboard
A zero-dependency, local-hosted `index.html` dashboard built with Tailwind CSS and Apache ECharts. It dynamically reads these processed CSVs to render Bar Charts and an interactive **Force-Directed Character Network Graph**.

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
3. **Data Structure**: Ensure your files follow this play-centric layout:
   ```text
   data/
     └── Romeo_and_Juliet/
         ├── Romeo_and_Juliet-Shakespeare-raw.txt
         └── srt/
             ├── Romeo_and_Juliet-1968.srt
   ```

## Usage & Quickstart

Use the built-in CLI help function to see all options: `python main.py -h`

**Run the Entire Pipeline (Parse + Extract):**
This is the easiest way to process a new play from scratch.
```bash
python main.py all -p Romeo_and_Juliet -r -t 5
```

**Run Only the Text Parser / NLP Character Analyzer:**
```bash
python main.py parse -p Macbeth -r
```

**Extract Timestamps from SRTs:**
(Note: Automatically prefers `-fixed.srt` or `-validated.srt` files if they exist to prevent destructive overwriting).
```bash
python main.py extract -p Romeo_and_Juliet
```

**Fix Out-of-Sync SRT files:**
If a subtitle file is off by a few seconds, shift it. This safely generates a `-fixed.srt` file.
```bash
python main.py util -p Romeo_and_Juliet --shift 1968 -2.8
```

## Analytical Conceits & Assumptions
To parse historical texts programmatically and align them across modern mediums, several design choices made:

* **Hybrid LSH + BoW Synchronization**: Aligning a 400-year-old script to a modern film is inherently fuzzy due to deleted lines and rearranged scenes. The extractor uses a coarse-to-fine hybrid algorithm:
    1. **Macro Search (LSH Density Clustering):** Queries overlapping 20-word script chunks against an LSH MinHash index of the subtitle file. Density clustering isolates the chronological "core" of the scene, bypassing false positives.
    2. **Micro Search (BoW Edge Honing):** Scans the subtitles strictly within the core cluster using a Bag-of-Words shingle overlap against the exact first and last 50 words of the script scene, snapping the Start/End timestamps tightly to the dialogue edges.
    3. **Chronological Constraint:** A strict mathematical forward-pass constraint (`Scene N Start >= Scene N-1 End`) guarantees overlapping "Schrödinger's scenes" are impossible.
* **Gimmick / Collective Roles**: "ALL" and "CHORUS" are treated as distinct speaking entities to preserve their text blocks. However, to prevent the social network graph from clustering wildly around the literal word "all", they are programmatically blacklisted from *incoming* mentions.
* **Titles as Unified Names**: Rather than letting the NLP model split "Thane of Cawdor" into separate entities, programmatic rules map noble titles (Thane, Prince, King, Duke) + "of" + [Place] into unified identities. 
* **Plural Auto-Filtering**: If the text mentions "MONTAGUES", the script checks if a singular "MONTAGUE" is in the actual speaking cast. If so, it drops the pluralized family mention entirely to prevent duplicated nodes.

## Data Source & Acknowledgments
Raw plaintext files sourced from **[The Complete Works of William Shakespeare](http://shakespeare.mit.edu/)** 
   
   (Created by Jeremy Hylton in 1993, based on the Complete Moby™ Shakespeare). 

## License
Distributed under the MIT License. See `LICENSE`.
