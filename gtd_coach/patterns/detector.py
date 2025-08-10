#!/usr/bin/env python3
"""
Lightweight pattern detection for recurring GTD items
Provides zero-friction memory retrieval for ADHD support
"""

import json
import glob
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class PatternDetector:
    """Lightweight pattern detection for recurring GTD items"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path.home() / "gtd-coach" / "data"
    
    def find_recurring_patterns(self, weeks_back: int = 4) -> List[Dict[str, Any]]:
        """Find items that appear across multiple mindsweep sessions"""
        all_items = []
        
        # Load recent mindsweep files
        mindsweep_files = sorted(glob.glob(str(self.data_dir / "mindsweep_*.json")))[-weeks_back:]
        
        for file_path in mindsweep_files:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    items = data.get('items', [])
                    all_items.extend([(item.lower(), file_path) for item in items])
            except (json.JSONDecodeError, FileNotFoundError):
                continue
        
        # Find recurring themes using key phrase extraction
        patterns = {}
        for item, source in all_items:
            # Extract meaningful 2-word phrases (bigrams)
            words = [w for w in item.split() if len(w) > 2]
            
            # Create bigrams from significant words
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                
                # Skip common filler bigrams
                if any(filler in bigram for filler in ['the', 'and', 'for', 'with', 'about']):
                    continue
                
                if bigram not in patterns:
                    patterns[bigram] = {'count': 0, 'examples': [], 'sources': set()}
                patterns[bigram]['count'] += 1
                patterns[bigram]['examples'].append(item)
                patterns[bigram]['sources'].add(source)
            
            # Also track single words that appear frequently
            # (dynamically identify important words based on frequency)
            for word in words:
                # Skip very common words
                if word in ['this', 'that', 'from', 'with', 'about', 'have', 'will']:
                    continue
                # Track if it's a potentially important word (verb or noun-like)
                if len(word) >= 4:  # Focus on meaningful words
                    single_key = f"_{word}"  # Prefix to distinguish from bigrams
                    if single_key not in patterns:
                        patterns[single_key] = {'count': 0, 'examples': [], 'sources': set()}
                    patterns[single_key]['count'] += 1
                    patterns[single_key]['examples'].append(item)
                    patterns[single_key]['sources'].add(source)
        
        # Return patterns that appear 2+ times from different sessions
        recurring = []
        for key, data in patterns.items():
            if data['count'] >= 2 and len(data['sources']) >= 2:
                # Use the most descriptive example
                best_example = min(data['examples'], key=len) if data['examples'] else ""
                # Clean up the pattern for display (remove underscore prefix for single words)
                display_pattern = key[1:].title() if key.startswith('_') else key.title()
                recurring.append({
                    'pattern': display_pattern,
                    'count': data['count'],
                    'example': best_example,
                    'weeks_seen': len(data['sources'])
                })
        
        return sorted(recurring, key=lambda x: x['count'], reverse=True)[:3]
    
    def save_context(self, context: Dict[str, Any]) -> None:
        """Save pre-computed context for next session"""
        context_file = self.data_dir / "next_session_context.json"
        with open(context_file, 'w') as f:
            json.dump(context, f, indent=2)
    
    def load_context(self) -> Dict[str, Any]:
        """Load pre-computed context (instant, no waiting)"""
        context_file = self.data_dir / "next_session_context.json"
        if context_file.exists():
            try:
                with open(context_file) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {}
    
    def get_simple_insights(self, mindsweep_items: List[str]) -> Dict[str, Any]:
        """Generate simple insights from current session"""
        insights = {
            'item_count': len(mindsweep_items),
            'timestamp': datetime.now().isoformat()
        }
        
        # Find common themes in current session
        if mindsweep_items:
            words = []
            for item in mindsweep_items:
                words.extend([w.lower() for w in item.split() if len(w) > 3])
            
            if words:
                word_counts = Counter(words)
                # Get top 3 most common words (excluding common words)
                common_words = {'with', 'from', 'this', 'that', 'have', 'will', 'been', 'about'}
                top_words = [w for w, c in word_counts.most_common(10) 
                           if w not in common_words][:3]
                insights['themes'] = top_words
        
        return insights