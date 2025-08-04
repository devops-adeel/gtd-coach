# Graphiti Memory Integration for GTD Coach

## Overview

This integration adds agentic memory capabilities to the GTD Coach using Zep's Graphiti. It tracks:
- Recurring patterns in mind sweep items
- Personal productivity insights  
- ADHD behavioral patterns (task switching and focus indicators)

## Architecture

### Components Created

1. **`graphiti_integration.py`** - Memory management interface
   - Async episode queuing and batching
   - Phase transition tracking
   - Behavior pattern recording
   - Session summary generation

2. **`adhd_patterns.py`** - ADHD pattern detection
   - Mindsweep coherence analysis
   - Task switching detection
   - Focus quality scoring
   - Linguistic marker analysis

3. **`generate_summary.py`** - Weekly insights generator
   - Queries last 7 days of data
   - Analyzes patterns and trends
   - Generates markdown reports
   - Provides ADHD-specific insights

4. **GTD Coach Enhancements**
   - Non-blocking memory capture
   - Real-time pattern detection
   - Automatic session summaries

## How It Works

### During Review Sessions

1. **Real-time Capture**: As you interact with the coach, all conversations are asynchronously captured
2. **Pattern Detection**: During mind sweep, the system detects:
   - Topic switches between items
   - Coherence scores
   - Fragmentation indicators
3. **Phase Tracking**: Each phase transition is recorded with timing data
4. **Batch Processing**: Data is flushed to disk after each phase to avoid performance impact

### Data Storage (Temporary)

Currently stores data as JSON files in `~/gtd-coach/data/`:
- `graphiti_batch_*.json` - Episode batches for Graphiti
- `mindsweep_*.json` - Mind sweep items
- `priorities_*.json` - Prioritized actions

When MCP integration is complete, these will be sent directly to Graphiti.

### Weekly Summaries

Run `python3 ~/gtd-coach/generate_summary.py` to generate insights including:
- Productivity metrics (completion rate, session duration)
- Mind sweep analysis (topics, themes, item counts)
- ADHD pattern analysis (task switching, coherence)
- Personalized recommendations

## Usage

### Running a Review with Memory

```bash
# Start your review as normal
~/gtd-coach/start-coach.sh

# The integration runs automatically in the background
```

### Generating Weekly Summary

```bash
# After completing reviews for the week
python3 ~/gtd-coach/generate_summary.py

# Summary is saved to ~/gtd-coach/summaries/
```

### Testing the Integration

```bash
# Run integration tests
python3 ~/gtd-coach/test_graphiti_integration.py
```

## Next Steps for Full MCP Integration

1. **Replace File Storage**: Update `GraphitiMemory.flush_episodes()` to use MCP tools:
   ```python
   await mcp_add_episode(
       name=f"{episode['type']}_{timestamp}",
       episode_body=json.dumps(episode),
       source="json",
       group_id=self.session_group_id
   )
   ```

2. **Enable Retrieval**: Update `GraphitiRetriever` methods to use MCP search:
   ```python
   results = await mcp_search_nodes(
       query="mind sweep patterns",
       entity_type="Behavior",
       center_node_uuid=user_uuid
   )
   ```

3. **Real-time Insights**: Add coach awareness of past patterns:
   - Query Graphiti before each phase
   - Provide personalized guidance based on history
   - Suggest improvements based on trends

## ADHD Pattern Detection Details

### Coherence Analysis
- **High coherence (>0.7)**: Items stay on topic, well-organized thoughts
- **Low coherence (<0.5)**: Fragmented thinking, multiple topic switches

### Task Switching
- Detects when consecutive items change topics
- Tracks frequency and abruptness of switches
- Identifies common switching patterns

### Focus Indicators
- Response time consistency
- Task completion rates
- Time efficiency per phase
- Clarification request frequency

## Privacy and Data

- All data stays local on your machine
- Session IDs are timestamped for easy management
- No personal data is sent to external services
- When using MCP/Graphiti, data remains in your configured Neo4j instance