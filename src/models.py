"""
models.py
Defines the Object-Oriented schema for plays and analytics characters.
"""
import json
from typing import List, Union, Dict, Any
from collections import defaultdict

class Character:
    def __init__(self, name: str):
        self.name = name.strip().upper()
        self.is_speaker = False
        self.stats = {"total_words": 0, "total_turns": 0, "avg_words_per_turn": 0.0}
        self.mentions_out = defaultdict(int) 
        self.mentions_in = defaultdict(int)

    @classmethod
    def from_csv_row(cls, row: dict):
        """Reconstructs a Character object from a loaded CSV dictionary row."""
        c = cls(row["Name"])
        c.is_speaker = (row["Is_Speaker"] == "True")
        c.stats["total_turns"] = int(row["Total_Turns"])
        c.stats["total_words"] = int(row["Total_Words"])
        c.stats["avg_words_per_turn"] = float(row["Avg_Words_Per_Turn"])
        
        # Deserialize the many-to-many relationship dictionaries
        c.mentions_out = defaultdict(int, json.loads(row["Mentions_Out_Dict"]))
        c.mentions_in = defaultdict(int, json.loads(row["Mentions_In_Dict"]))
        return c


class StageDirection:
    def __init__(self, text: str):
        self.text = text.strip()
        self.act_idx = 0
        self.scene_idx_in_act = 0
        self.scene_idx_in_play = 0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "stage_direction", 
            "text": self.text,
            "act_idx": self.act_idx,
            "scene_idx_in_act": self.scene_idx_in_act,
            "scene_idx_in_play": self.scene_idx_in_play
        }

    @classmethod
    def from_dict(cls, data: dict):
        sd = cls(data["text"])
        sd.act_idx = data.get("act_idx", 0)
        sd.scene_idx_in_act = data.get("scene_idx_in_act", 0)
        sd.scene_idx_in_play = data.get("scene_idx_in_play", 0)
        return sd


class Turn:
    def __init__(self, speaker: str):
        self.speaker = speaker.strip().upper()
        self.lines: List[str] =[]
        
        # Enriched Metadata Fields
        self.act_idx = 0
        self.scene_idx_in_act = 0
        self.scene_idx_in_play = 0
        self.turn_idx_in_scene = 0
        self.turn_idx_in_act = 0
        self.turn_idx_in_play = 0
        self.progress_in_scene = 0.0
        self.progress_in_act = 0.0
        self.progress_in_play = 0.0
        
    def add_line(self, line: str):
        self.lines.append(line.strip())
        
    def word_count(self) -> int:
        return sum(len(line.split()) for line in self.lines)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "turn",
            "speaker": self.speaker,
            "lines": self.lines,
            "word_count": self.word_count(),
            "act_idx": self.act_idx,
            "scene_idx_in_act": self.scene_idx_in_act,
            "scene_idx_in_play": self.scene_idx_in_play,
            "turn_idx_in_scene": self.turn_idx_in_scene,
            "turn_idx_in_act": self.turn_idx_in_act,
            "turn_idx_in_play": self.turn_idx_in_play,
            "progress_in_scene": self.progress_in_scene,
            "progress_in_act": self.progress_in_act,
            "progress_in_play": self.progress_in_play
        }

    @classmethod
    def from_dict(cls, data: dict):
        t = cls(data["speaker"])
        t.lines = data["lines"]
        for key in["act_idx", "scene_idx_in_act", "scene_idx_in_play", 
                    "turn_idx_in_scene", "turn_idx_in_act", "turn_idx_in_play",
                    "progress_in_scene", "progress_in_act", "progress_in_play"]:
            setattr(t, key, data.get(key, 0))
        return t

class Scene:
    def __init__(self, title: str):
        self.title = title.strip()
        self.elements: List[Union[Turn, StageDirection]] =[]
        self.act_idx = 0
        self.scene_idx_in_act = 0
        self.scene_idx_in_play = 0
        self.total_turns = 0
        
    def add_element(self, element: Union[Turn, StageDirection]):
        self.elements.append(element)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "act_idx": self.act_idx,
            "scene_idx_in_act": self.scene_idx_in_act,
            "scene_idx_in_play": self.scene_idx_in_play,
            "total_turns": self.total_turns,
            "elements": [e.to_dict() for e in self.elements]
        }

    @classmethod
    def from_dict(cls, data: dict):
        s = cls(data["title"])
        s.act_idx = data.get("act_idx", 0)
        s.scene_idx_in_act = data.get("scene_idx_in_act", 0)
        s.scene_idx_in_play = data.get("scene_idx_in_play", 0)
        s.total_turns = data.get("total_turns", 0)
        
        for e in data["elements"]:
            if e["type"] == "stage_direction":
                s.add_element(StageDirection.from_dict(e))
            elif e["type"] == "turn":
                s.add_element(Turn.from_dict(e))
        return s

class Act:
    def __init__(self, title: str):
        self.title = title.strip()
        self.scenes: List[Scene] =[]
        self.act_idx = 0
        self.total_scenes = 0
        self.total_turns = 0
        
    def add_scene(self, scene: Scene):
        self.scenes.append(scene)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "act_idx": self.act_idx,
            "total_scenes": self.total_scenes,
            "total_turns": self.total_turns,
            "scenes":[s.to_dict() for s in self.scenes]
        }

    @classmethod
    def from_dict(cls, data: dict):
        a = cls(data["title"])
        a.act_idx = data.get("act_idx", 0)
        a.total_scenes = data.get("total_scenes", 0)
        a.total_turns = data.get("total_turns", 0)
        for s_data in data["scenes"]:
            a.add_scene(Scene.from_dict(s_data))
        return a

class Play:
    def __init__(self, title: str):
        self.title = title.strip()
        self.acts: List[Act] =[]
        self.total_turns = 0
        
    def add_act(self, act: Act):
        self.acts.append(act)

    def enrich_metadata(self):
        """Back-propagates sequential IDs and calculates completion fractions."""
        global_scene_idx = 0
        global_turn_idx = 1
        
        # Pass 1: Assign IDs and get totals
        for a_idx, act in enumerate(self.acts, 1):
            act.act_idx = a_idx
            act.total_scenes = len(act.scenes)
            
            local_scene_idx = 1
            act_turns = 0
            
            for scene in act.scenes:
                scene.act_idx = a_idx
                is_prologue = "PROLOGUE" in scene.title.upper()
                
                # Assign 0 for Prologue, attach to the 'previous' global scene context
                if is_prologue:
                    scene.scene_idx_in_act = 0
                    scene.scene_idx_in_play = global_scene_idx 
                else:
                    scene.scene_idx_in_act = local_scene_idx
                    local_scene_idx += 1
                    global_scene_idx += 1
                    scene.scene_idx_in_play = global_scene_idx
                    
                scene_turns = sum(1 for e in scene.elements if isinstance(e, Turn))
                scene.total_turns = scene_turns
                
                local_turn_idx = 1
                for element in scene.elements:
                    # Stage directions just get basic locality tags
                    element.act_idx = a_idx
                    element.scene_idx_in_act = scene.scene_idx_in_act
                    element.scene_idx_in_play = scene.scene_idx_in_play
                    
                    if isinstance(element, Turn):
                        element.turn_idx_in_scene = local_turn_idx
                        element.turn_idx_in_act = act_turns + local_turn_idx
                        element.turn_idx_in_play = global_turn_idx
                        
                        element.progress_in_scene = round(local_turn_idx / scene_turns, 4) if scene_turns else 0.0
                        
                        local_turn_idx += 1
                        global_turn_idx += 1
                
                act_turns += scene_turns
            act.total_turns = act_turns
            
        self.total_turns = global_turn_idx - 1
        
        # Pass 2: Now that we know totals for Acts and the Play, calculate remaining fractions
        for act in self.acts:
            for scene in act.scenes:
                for element in scene.elements:
                    if isinstance(element, Turn):
                        element.progress_in_act = round(element.turn_idx_in_act / act.total_turns, 4) if act.total_turns else 0.0
                        element.progress_in_play = round(element.turn_idx_in_play / self.total_turns, 4) if self.total_turns else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "total_turns": self.total_turns,
            "acts":[a.to_dict() for a in self.acts]
        }

    @classmethod
    def from_dict(cls, data: dict):
        p = cls(data["title"])
        p.total_turns = data.get("total_turns", 0)
        for a_data in data["acts"]:
            p.add_act(Act.from_dict(a_data))
        return p