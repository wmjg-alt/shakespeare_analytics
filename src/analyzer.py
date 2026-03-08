"""
analyzer.py
Engine for NER extraction, statistical calculations, and Dual-Reporting.
Includes programmatic Entity Aliasing, Plural filtering, and Gimmick constraints.
"""
import csv
import json
import logging
import spacy
from typing import Dict

from src.models import Play, Turn, Character

logger = logging.getLogger(__name__)

class PlayAnalyzer:
    def __init__(self, play: Play = None, gimmick_chars: list = None):
        self.play = play
        self.characters: Dict[str, Character] = {}
        self.nlp = None
        # Normalize gimmicks to uppercase set for fast checking
        self.gimmick_chars = set([g.upper() for g in (gimmick_chars or [])])

    def _init_spacy(self):
        """Lazy loader for SpaCy to save memory/time if we are just loading a CSV."""
        if not self.nlp:
            logger.info("Loading spaCy Transformer model (en_core_web_trf)...")
            try:
                self.nlp = spacy.load("en_core_web_trf", disable=["tagger", "parser", "attribute_ruler", "lemmatizer"])
            except OSError:
                logger.error("Spacy model missing! Run: python -m spacy download en_core_web_trf")
                raise

            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            patterns =[]

            if self.play:
                speaker_names = set()
                for act in self.play.acts:
                    for scene in act.scenes:
                        for element in scene.elements:
                            if isinstance(element, Turn):
                                speaker_names.add(element.speaker)
                
                for name in speaker_names:
                    pattern_nodes =[{"LOWER": word.lower()} for word in name.split()]
                    patterns.append({"label": "PERSON", "pattern": pattern_nodes})

            patterns.append({
                "label": "PERSON",
                "pattern":[
                    {"LOWER": {"IN":["thane", "prince", "king", "queen", "duke", "earl", "lord", "lady"]}},
                    {"LOWER": "of"},
                    {"IS_TITLE": True}
                ]
            })

            ruler.add_patterns(patterns)

    def _get_character(self, name: str) -> Character:
        name = name.upper()
        if name not in self.characters:
            self.characters[name] = Character(name)
        return self.characters[name]

    def analyze(self):
        """Iterates through the play, runs NLP, and populates character stats."""
        if not self.play:
            raise ValueError("Play object is required to run deep NLP analysis.")
            
        self._init_spacy()
        logger.info("Running Named Entity Recognition on dialogue... This may take a moment.")
        
        for act in self.play.acts:
            for scene in act.scenes:
                for element in scene.elements:
                    if isinstance(element, Turn):
                        speaker = self._get_character(element.speaker)
                        speaker.is_speaker = True
                        speaker.stats["total_turns"] += 1
                        speaker.stats["total_words"] += element.word_count()
                        
                        doc = self.nlp(" ".join(element.lines))
                        for ent in doc.ents:
                            if ent.label_ == "PERSON":
                                mentioned_name = ent.text.strip().upper()
                                # Ignore self-mentions AND incoming mentions to gimmick characters
                                if mentioned_name != speaker.name and mentioned_name not in self.gimmick_chars:
                                    speaker.mentions_out[mentioned_name] += 1
                                    mentioned_char = self._get_character(mentioned_name)
                                    mentioned_char.mentions_in[speaker.name] += 1
                                    
        for char in self.characters.values():
            if char.stats["total_turns"] > 0:
                char.stats["avg_words_per_turn"] = char.stats["total_words"] / char.stats["total_turns"]

        self._filter_hallucinations()

    def _filter_hallucinations(self):
        """Cleans up the character registry based on strict heuristics."""
        bad_names = {"HO", "ERE", "AY", "NAY", "DOST", "HATH", "DOTH", "DIAN", 
                     "LIES", "WHERETO", "O", "AH", "ALAS", "MARRY",
                     "SIRRAH", "ANON", "HIE", "FIE", "ALACK", "TUT", "HAIL", "ALL"}
        
        valid_chars = {}
        speakers_set = {name for name, char in self.characters.items() if char.is_speaker}

        for name, char in self.characters.items():
            if name in bad_names and not char.is_speaker:
                continue
                
            is_plural_of_speaker = False
            if not char.is_speaker:
                if name.endswith("S") and name[:-1] in speakers_set:
                    is_plural_of_speaker = True
                elif name.endswith("ES") and name[:-2] in speakers_set:
                    is_plural_of_speaker = True
                    
            if is_plural_of_speaker:
                continue
                
            if char.is_speaker or len(char.mentions_in) >= 2:
                valid_chars[name] = char
                
        self.characters = valid_chars
        for char in self.characters.values():
            char.mentions_out = {k: v for k, v in char.mentions_out.items() if k in valid_chars}
            char.mentions_in = {k: v for k, v in char.mentions_in.items() if k in valid_chars}

    def load_from_csv(self, filepath: str):
        """Instantiates the character registry directly from a saved CSV."""
        logger.info(f"Loading Character network from {filepath} (Skipping NLP pass)...")
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                char = Character.from_csv_row(row)
                self.characters[char.name] = char

    def export_csv(self, filepath: str):
        """Exports the character registry and full relational dictionaries to CSV."""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Is_Speaker", "Total_Turns", "Total_Words", 
                             "Avg_Words_Per_Turn", "Mentions_Out_Dict", "Mentions_In_Dict"])
            
            for char in sorted(self.characters.values(), key=lambda x: x.stats["total_words"], reverse=True):
                writer.writerow([
                    char.name, char.is_speaker, char.stats["total_turns"], char.stats["total_words"],
                    round(char.stats["avg_words_per_turn"], 2),
                    json.dumps(char.mentions_out), json.dumps(char.mentions_in)
                ])
        logger.info(f"Successfully exported full character statistics to {filepath}")

    def generate_report(self, report_filepath: str, play_title: str = "Play", top_n: int = 5):
        """Generates a text report, prints to console, and writes cleanly to a file."""
        all_chars = list(self.characters.values())
        speakers =[c for c in all_chars if c.is_speaker]
        
        most_words = sorted(speakers, key=lambda x: x.stats["total_words"], reverse=True)[:top_n]
        most_turns = sorted(speakers, key=lambda x: x.stats["total_turns"], reverse=True)[:top_n]
        wordiest = sorted([c for c in speakers if c.stats["total_turns"] >= 2],
                          key=lambda x: x.stats["avg_words_per_turn"], reverse=True)[:top_n]
        top_gossip = sorted(speakers, key=lambda x: sum(x.mentions_out.values()), reverse=True)[:top_n]
        most_talked_about = sorted(all_chars, key=lambda x: sum(x.mentions_in.values()), reverse=True)[:top_n]

        # Aggregate report lines into a list
        lines =[]
        lines.append("=" * 60)
        lines.append(f"      NLP ANALYTICS: {play_title.upper()} (TOP {top_n})")
        lines.append("=" * 60)
        lines.append(f"Total Valid Entities:      {len(self.characters)}")
        lines.append(f"Actual Speaking Roles:     {len(speakers)}")
        lines.append(f"Mentioned-Only Characters: {len(self.characters) - len(speakers)}")
        
        lines.append(f"\n--- Most Words Spoken ---")
        for i, char in enumerate(most_words, 1):
            lines.append(f"{i:>2}. {char.name:<20} {char.stats['total_words']:>5} words")

        lines.append(f"\n--- Most Turns Taken ---")
        for i, char in enumerate(most_turns, 1):
            lines.append(f"{i:>2}. {char.name:<20} {char.stats['total_turns']:>5} turns")

        lines.append(f"\n--- Wordiest Characters (Avg Words/Turn) ---")
        for i, char in enumerate(wordiest, 1):
            lines.append(f"{i:>2}. {char.name:<20} {char.stats['avg_words_per_turn']:>5.1f} avg words")

        lines.append(f"\n--- Top Gossip (Mentions others the most) ---")
        for i, char in enumerate(top_gossip, 1):
            total_out = sum(char.mentions_out.values())
            fav_target = max(char.mentions_out, key=char.mentions_out.get) if char.mentions_out else "None"
            n_mentions_fav = char.mentions_out[fav_target]
            lines.append(f"{i:>2}. {char.name:<20} {total_out:>4} mentions (Most: {fav_target} - {n_mentions_fav})")

        lines.append(f"\n--- Most Talked About (Mentioned by others the most) ---")
        for i, char in enumerate(most_talked_about, 1):
            total_in = sum(char.mentions_in.values())
            biggest_fan = max(char.mentions_in, key=char.mentions_in.get) if char.mentions_in else "None"
            n_mentions_fan = char.mentions_in[biggest_fan]
            lines.append(f"{i:>2}. {char.name:<20} {total_in:>4} mentions (Biggest Fan: {biggest_fan} - {n_mentions_fan})")
        lines.append("="*60 + "\n")

        report_text = "\n".join(lines)
        
        # 1. Print to Console
        print(f"\n{report_text}\n")
        
        # 2. Write to File ('w' overwrites, ensuring no accidental appending to old stats)
        with open(report_filepath, 'w', encoding='utf-8') as f:
            f.write(report_text)
        logger.info(f"Analytics report written cleanly to {report_filepath}")