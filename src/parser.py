"""
parser.py
State-machine based parser with deep heuristics for text extraction.
"""
import logging
from src.models import Play, Act, Scene, Turn, StageDirection

logger = logging.getLogger(__name__)

def is_act_header(line: str) -> bool:
    return line.startswith("ACT ")

def is_scene_header(line: str) -> bool:
    return line.startswith("SCENE ") or line.startswith("PROLOGUE")

def is_indented(line: str) -> bool:
    return line.startswith(" ") or line.startswith("\t")

def is_character_name(line: str) -> bool:
    if not line.strip() or is_indented(line):
        return False
    if is_act_header(line) or is_scene_header(line):
        return False
    return True

def is_stage_direction(line: str, is_scene_start: bool) -> bool:
    text = line.strip()
    if text.startswith("[") and text.endswith("]"):
        return True
    sd_keywords =["Enter", "Exit", "Exeunt", "Retires", "Dies", "Strikes", "Musicians"]
    if any(text.startswith(kw) for kw in sd_keywords):
        return True
    return False


class PlayParser:
    def __init__(self, title: str):
        self.play = Play(title)
        self.current_act = None
        self.current_scene = None
        self.current_turn = None
        
        self.started = False
        self.lines_parsed = 0
        self.anomalies = 0

    def parse_file(self, filepath: str) -> Play:
        logger.info(f"Beginning raw text parse of {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                self._parse_line(line, line_num)
                
        # Back Prop
        self.play.enrich_metadata()
        
        self._validate_closure()
        return self.play

    def _parse_line(self, line: str, line_num: int):
        clean_line = line.rstrip('\n\r')
        
        if not self.started:
            if is_act_header(clean_line):
                self.started = True
            else:
                return  
                
        self.lines_parsed += 1
        if not clean_line.strip():
            return  
            
        if is_act_header(clean_line):
            self._handle_act(clean_line)
        elif is_scene_header(clean_line):
            self._handle_scene(clean_line)
        elif is_character_name(clean_line):
            self._handle_character(clean_line)
        elif is_indented(clean_line):
            self._handle_indented_content(clean_line, line_num)
        else:
            self.anomalies += 1
            logger.warning(f"Line {line_num} Anomaly: Unrecognized structure -> '{clean_line}'")

    def _handle_act(self, line: str):
        self.current_turn = None
        self.current_scene = None
        self.current_act = Act(line.strip())
        self.play.add_act(self.current_act)

    def _handle_scene(self, line: str):
        self.current_turn = None
        self.current_scene = Scene(line.strip())
        if self.current_act:
            self.current_act.add_scene(self.current_scene)

    def _handle_character(self, line: str):
        self.current_turn = Turn(line)
        if self.current_scene:
            self.current_scene.add_element(self.current_turn)

    def _handle_indented_content(self, line: str, line_num: int):
        if not self.current_scene:
            return

        is_scene_start = (self.current_turn is None)
        
        if is_stage_direction(line, is_scene_start):
            sd = StageDirection(line)
            self.current_scene.add_element(sd)
        else:
            if self.current_turn is None:
                self.anomalies += 1
                logger.warning(f"Line {line_num} Anomaly: Unassigned dialogue. Defaulting to 'CHORUS'.")
                self.current_turn = Turn("CHORUS")
                self.current_scene.add_element(self.current_turn)
                
            self.current_turn.add_line(line)

    def _validate_closure(self):
        logger.info("=== Parsing Completed ===")
        if self.anomalies > 0:
            logger.warning(f"Finished with {self.anomalies} structural anomalies patched.")
        else:
            logger.info("Perfect parse! 0 structural anomalies detected.")