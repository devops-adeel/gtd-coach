# Phase 2: Pattern Learning from Evaluation Data

## ✅ Implementation Complete

### Overview
Phase 2 implements pattern learning from evaluation data with a focus on ADHD-specific behaviors. The system analyzes coaching sessions to detect patterns in time blindness, task switching, executive function, and fatigue, then generates actionable insights and adapts thresholds personalized to each user.

## Architecture

### Core Components

#### 1. **ADHD Pattern Analyzer** (`gtd_coach/patterns/evaluation_patterns.py`)
Detects ADHD-specific patterns from evaluation data:
- **Time Blindness Score**: Measures time awareness accuracy (0-1 scale)
- **Task Switching Frequency**: Counts topic changes and incomplete thoughts
- **Executive Function Assessment**: Evaluates organizational support effectiveness
- **Fatigue Detection**: Identifies energy drop-off patterns

#### 2. **Pattern Aggregator** (`gtd_coach/patterns/pattern_aggregator.py`)
Statistical analysis and aggregation:
- **Rolling Averages**: 7-session window for trend detection
- **Anomaly Detection**: 2 standard deviation threshold
- **Session Clustering**: Groups sessions into performance levels
- **Personal Baseline**: Calculates individual norms

#### 3. **Adaptive Metrics** (`gtd_coach/metrics/adaptive_metrics.py`)
Personalizes evaluation thresholds:
- **Dynamic Adjustment**: Gradual rate of 0.1 per session
- **Bounded Thresholds**: Respects min/max limits per metric
- **Degradation Detection**: Alerts when below personal baseline
- **Intervention Suggestions**: Context-specific recommendations

#### 4. **Evaluation Analytics** (`gtd_coach/analytics/evaluation_analytics.py`)
Insight generation and reporting:
- **Trend Calculation**: Linear regression for performance trends
- **Template-Based Insights**: ADHD-specific actionable advice
- **Weekly Summaries**: Comprehensive pattern reports
- **Markdown Export**: Formatted insights for review

## ADHD Pattern Detection

### Time Blindness Indicators
```python
{
  'score': 0.45,  # Below 0.5 indicates issue
  'indicators': [
    'Lack of time awareness in MIND_SWEEP',
    'Rush pattern detected in PRIORITIZATION'
  ],
  'severity': 'moderate'
}
```

### Task Switching Analysis
```python
{
  'switch_frequency': 3.5,  # Switches per session
  'incomplete_thoughts': 2,
  'affected_phases': ['MIND_SWEEP', 'PROJECT_REVIEW'],
  'severity': 'high'
}
```

### Executive Function Support
```python
{
  'overall_score': 0.65,
  'task_extraction_accuracy': 0.8,
  'memory_utilization': 0.5,
  'structure_support': 0.65,
  'needs_improvement': False
}
```

### Fatigue Patterns
```python
{
  'detected': True,
  'indicators': ['Declining performance across phases'],
  'phase_scores': [0.8, 0.75, 0.6, 0.5],  # Downward trend
  'severity': 'moderate'
}
```

## Statistical Methods

### Algorithms Used
- **Moving Average**: Simple 7-session window
- **Anomaly Detection**: Standard deviation method (2σ)
- **Trend Analysis**: Linear regression with scipy.stats
- **Clustering**: Simple K-means implementation (no sklearn)

### Performance Metrics
- Pattern detection: < 100ms latency
- Aggregation: Handles 30+ sessions efficiently
- Insight generation: Template-based, instant
- No impact on session performance (fire-and-forget)

## Adaptive Thresholds

### How It Works
1. **Baseline Calculation**: After 5 sessions, calculates personal mean ± std
2. **Gradual Adjustment**: Moves 10% toward target each session
3. **Bounded Updates**: Respects metric-specific min/max values
4. **Degradation Alerts**: Triggers when below personal baseline

### Example Threshold Evolution
```
Session 1-5: Default threshold = 0.7
Session 6: Personal mean = 0.75, adjusted to 0.71
Session 10: Converged to personal baseline = 0.73
Session 15: Stable at 0.73 ± 0.05
```

## Insight Generation

### Template-Based Insights
The system generates specific, actionable insights based on detected patterns:

#### Critical Issues (Red Alerts)
- "⚠️ **Critical Time Awareness Issue**: Your time estimation accuracy is very low. Consider using visual timers and setting alerts every 5 minutes."

#### Improvement Opportunities (Yellow Alerts)
- "📉 **Declining Time Awareness**: Your ability to track time is decreasing. Try the Pomodoro technique with 25-minute blocks."

#### Positive Reinforcement (Green Alerts)
- "✅ **Time Management Improving**: Your time awareness is getting better! Current strategies are working."

## Configuration

### Pattern Learning Settings (`config/pattern_learning/pattern_config.yaml`)
```yaml
pattern_learning:
  enabled: true
  min_sessions: 5
  
  adhd_patterns:
    time_blindness:
      threshold: 0.5
    task_switching:
      threshold: 3.0
    executive_function:
      threshold: 0.6
    fatigue_detection:
      threshold: 0.5
```

## Testing

### Test Coverage
- ✅ ADHD pattern detection
- ✅ Pattern aggregation across sessions
- ✅ Statistical analysis methods
- ✅ Session clustering
- ✅ Adaptive threshold adjustment
- ✅ Insight generation
- ✅ Weekly summary creation
- ✅ Performance trend analysis
- ✅ Personal baseline calculation
- ✅ Full integration pipeline

### Running Tests
```bash
python3 test_pattern_learning.py
```

## Integration with Existing Systems

### With Phase 1 Evaluation
- Reads evaluation files from `data/evaluations/`
- Processes scores and reasoning from LLM judges
- No modification to evaluation system needed

### With Langfuse
- Optional integration for fetching aggregated scores
- Falls back to local data if unavailable

### With N-of-1 Experiments
- Patterns can trigger new experiments
- Adaptive thresholds inform success criteria

## Privacy & Performance

### Data Retention
- 30-day maximum retention
- Local-only pattern storage
- Aggregate statistics only
- No PII in patterns

### Performance Guarantees
- < 100ms pattern detection
- Async processing (fire-and-forget)
- Zero impact on session flow
- Cached insights for 60 minutes

## Example Weekly Summary

```markdown
# GTD Coach Weekly Insights

📅 Week of 2025-08-04

## Summary
- **Sessions Completed**: 5
- **Time Awareness Score**: 65%
- **Task Switching Frequency**: 2.8 switches/session
- **Executive Function Score**: 72%

## Key Insights

✅ **Executive Function Strong**: Your organizational skills are excellent!

📉 **Declining Time Awareness**: Your ability to track time is decreasing.

🔄 **Moderate Task Switching**: Some topic jumping detected.

## Recommendations

1. **Time Management Tool**: Install a Time Timer app
2. **Batch Similar Tasks**: Group all email items together
3. **Energy Management**: Schedule reviews for peak energy time

## Performance Trends
- Task Extraction: ➡️ stable
- Memory Relevance: 📉 declining
- Coaching Quality: 📈 improving
```

## Future Enhancements (Phase 3)

### Real-Time Interventions
- Pattern detection triggers immediate coaching adjustments
- Phase-boundary interventions based on degradation
- Adaptive prompts based on user state

### Enhanced Analytics
- LLM-powered insight generation
- Correlation with Timing app data
- Graphiti memory integration

## Timing App Validation (Phase 2.5)

### Overview
Enhanced pattern validation using Timing app data to understand the discrepancy between self-reported and actual time usage. This discrepancy is treated as valuable diagnostic information about executive function, not an error to correct.

### Implementation
- **Non-invasive Integration**: Added `enrich_with_timing_patterns()` method to existing `ADHDPatternAnalyzer`
- **Pattern Classification**: 
  - `high_awareness`: Good self-awareness (>70% project coverage)
  - `selective_awareness`: Remembers important work, forgets routine (40-70%)
  - `time_blindness`: Significant executive function challenge (<40%)
- **Invisible Work Ratio**: Calculates percentage of work time not mentioned in reviews
- **Fire-and-forget**: Async enrichment with 3-second timeout, no session disruption

### Insights Generated
- **Time Blindness Pattern**: Validates ADHD time blindness with compassionate framing
- **Selective Awareness**: Explains focus on memorable vs routine work
- **Invisible Work**: Acknowledges reactive/unplanned work as valid

### Testing
All Timing validation tests pass:
- Graceful degradation without Timing data
- Pattern detection accuracy
- Invisible work calculations
- Timeout handling
- Insight generation

## Summary

Phase 2 successfully implements a comprehensive pattern learning system that:
- Detects ADHD-specific behavioral patterns
- Validates patterns with objective Timing data (Phase 2.5)
- Adapts thresholds to individual baselines
- Generates actionable, template-based insights
- Maintains zero-friction user experience
- Provides foundation for Phase 3 interventions

The system is production-ready and will continuously improve coaching quality through data-driven personalization and validation.