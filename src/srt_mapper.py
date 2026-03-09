"""
srt_mapper.py
Hybrid LSH Density Clustering & Bag-of-Words (BoW) Engine for SRT alignment.
"""
import re
import logging
from typing import List, Dict, Any
from datasketch import MinHash, MinHashLSH

logger = logging.getLogger(__name__)

# ==========================================
# 🛠️ ALIGNMENT CONFIGURATION
# ==========================================
CONFIG = {
    # LSH Macro Search (Finding the "Truth" Cluster)
    "num_permutations": 128,
    "lsh_threshold": 0.15,       # Fuzzy enough to catch script deviations
    "shingle_size": 3,           # N-gram size (3 words per chunk)
    "srt_window_subs": 4,        # Group 4 subtitles together for LSH index
    "srt_window_stride": 1,      
    "script_window_words": 20,   # Chunk script into 20-word segments for querying
    "script_window_stride": 10,  
    "cluster_gap_seconds": 120,  # Matches > 2 mins apart belong to different scenes
    
    # BoW Micro Search (Honing the Edges)
    "boundary_search_words": 50  # Number of words to use as Start/End anchors for precise trimming
}
# ==========================================

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\[.*?\]|\(.*?\)', '', text) 
    text = re.sub(r'[^a-z0-9\s]', '', text)     
    return " ".join(text.split())

def get_shingles(text: str, n: int = CONFIG["shingle_size"]) -> set:
    words = text.split()
    if len(words) < n: return {text}
    return set(" ".join(words[i:i+n]) for i in range(len(words) - n + 1))

def create_minhash(shingles: set) -> MinHash:
    m = MinHash(num_perm=CONFIG["num_permutations"])
    for s in shingles: m.update(s.encode('utf8'))
    return m

def has_overlap(anchor_shingles: set, sub_shingles: set) -> bool:
    """Checks if a subtitle shares at least one n-gram with the anchor text."""
    if not sub_shingles or not anchor_shingles: return False
    return len(anchor_shingles.intersection(sub_shingles)) >= 1

class SRTMapper:
    def __init__(self, play_schema: Dict[str, Any], srt_data: List[Dict]):
        self.play_schema = play_schema
        self.srt_data = srt_data
        self.lsh = MinHashLSH(threshold=CONFIG["lsh_threshold"], num_perm=CONFIG["num_permutations"])
        self.windows = {}
        
        self.total_film_seconds = self.srt_data[-1]["end"].total_seconds() if self.srt_data else 1.0
        self._build_lsh_index()

    def _build_lsh_index(self):
        """Builds the coarse LSH index from the SRT file."""
        w_size, stride = CONFIG["srt_window_subs"], CONFIG["srt_window_stride"]
        for i in range(0, len(self.srt_data) - w_size + 1, stride):
            window_subs = self.srt_data[i:i+w_size]
            combined_text = clean_text(" ".join(sub["text"] for sub in window_subs))
            if not combined_text: continue
            
            shingles = get_shingles(combined_text)
            m = create_minhash(shingles)
            win_id = f"win_{i}"
            
            self.windows[win_id] = {
                "start_sec": window_subs[0]["start"].total_seconds(),
                "end_sec": window_subs[-1]["end"].total_seconds(),
                "start_idx": i,
                "end_idx": i + w_size - 1,
                "shingles": shingles
            }
            self.lsh.insert(win_id, m)

    def _cluster_matches(self, matches: List[Dict]) -> Dict:
        """Finds the densest chronological cluster to isolate the scene's core timeline."""
        if not matches: return None
        
        matches.sort(key=lambda x: x["time"])
        clusters = []
        current_cluster = [matches[0]]
        
        for m in matches[1:]:
            if m["time"] - current_cluster[-1]["time"] <= CONFIG["cluster_gap_seconds"]:
                current_cluster.append(m)
            else:
                clusters.append(current_cluster)
                current_cluster = [m]
        clusters.append(current_cluster)
        
        best_cluster = max(clusters, key=lambda c: len(c))
        
        return {
            "start_idx": min(m["start_idx"] for m in best_cluster),
            "end_idx": max(m["end_idx"] for m in best_cluster)
        }

    def format_scene_id(self, act_idx, scene_idx, title):
        if "PROLOGUE" in title.upper():
            return f"A{act_idx} Prologue"
        return f"A{act_idx}S{scene_idx}"

    def extract_timeline(self) -> Dict[str, str]:
        results = {}
        last_scene_end_sec = 0.0 # Mathematical chronological constraint constraint
        
        for act in self.play_schema.get("acts",[]):
            for scene in act.get("scenes",[]):
                scene_id = self.format_scene_id(scene.get("act_idx"), scene.get("scene_idx_in_act"), scene["title"])
                
                lines =[line for e in scene.get("elements", []) if e["type"] == "turn" for line in e["lines"]]
                scene_text = clean_text(" ".join(lines))
                words = scene_text.split()
                if not words: continue
                
                # ==================================================
                # PHASE 1: MACRO SEARCH (Find the Core with LSH)
                # ==================================================
                w_size, stride = CONFIG["script_window_words"], CONFIG["script_window_stride"]
                scene_matches =[]

                for i in range(0, len(words), stride):
                    chunk = " ".join(words[i:i+w_size])
                    if not chunk: continue
                    
                    chunk_shingles = get_shingles(chunk)
                    result_ids = self.lsh.query(create_minhash(chunk_shingles))
                    
                    for win_id in result_ids:
                        win = self.windows[win_id]
                        scene_matches.append({
                            "time": win["start_sec"],
                            "start_idx": win["start_idx"],
                            "end_idx": win["end_idx"]
                        })

                cluster = self._cluster_matches(scene_matches)

                def format_hms(sec):
                    m, s = divmod(int(sec), 60)
                    h, m = divmod(m, 60)
                    return f"{h:02d}:{m:02d}:{s:02d}"

                if not cluster:
                    results[f"{scene_id} Start"] = "N/A"
                    results[f"{scene_id} End"] = "N/A"
                    continue

                # ==================================================
                # PHASE 2: MICRO SEARCH (Trim Edges with Bag-of-Words)
                # ==================================================
                start_idx = cluster["start_idx"]
                end_idx = min(cluster["end_idx"] + CONFIG["srt_window_subs"], len(self.srt_data) - 1)
                
                # Set fallback boundaries to the general cluster edges
                true_start_sec = self.srt_data[start_idx]["start"].total_seconds()
                true_end_sec = self.srt_data[end_idx]["end"].total_seconds()

                # Build Start & End Anchors
                start_anchor = get_shingles(" ".join(words[:CONFIG["boundary_search_words"]]))
                end_anchor = get_shingles(" ".join(words[-CONFIG["boundary_search_words"]:]))

                # Forward Scan for Exact Start
                for i in range(start_idx, end_idx + 1):
                    sub_shingles = get_shingles(clean_text(self.srt_data[i]["text"]))
                    if has_overlap(start_anchor, sub_shingles):
                        true_start_sec = self.srt_data[i]["start"].total_seconds()
                        break

                # Backward Scan for Exact End
                for i in range(end_idx, start_idx - 1, -1):
                    sub_shingles = get_shingles(clean_text(self.srt_data[i]["text"]))
                    if has_overlap(end_anchor, sub_shingles):
                        true_end_sec = self.srt_data[i]["end"].total_seconds()
                        break

                # ==================================================
                # PHASE 3: SEQUENCE ENFORCEMENT (No Overlaps!)
                # ==================================================
                if true_start_sec < last_scene_end_sec:
                    true_start_sec = last_scene_end_sec
                
                if true_end_sec < true_start_sec:
                    true_end_sec = true_start_sec

                # Update the chronological lock for the next scene
                last_scene_end_sec = true_end_sec

                results[f"{scene_id} Start"] = format_hms(true_start_sec)
                results[f"{scene_id} End"] = format_hms(true_end_sec)
                    
        return results