# LLM-as-a-Judge Implementation for GTD Coach

## ✅ Phase 1 Complete: Post-Session Evaluation

### What We Built
A non-blocking, fire-and-forget evaluation system that assesses GTD Coach interactions after each session without impacting user experience.

### Key Components

1. **Post-Session Evaluator** (`gtd_coach/evaluation/post_session.py`)
   - Evaluates sessions asynchronously after completion
   - Uses both local (Llama 3.1) and cloud (OpenAI) models
   - Implements graceful fallback when cloud APIs unavailable
   - Saves results to `~/gtd-coach/data/evaluations/`

2. **Evaluation Criteria** (`gtd_coach/evaluation/criteria.py`)
   - **Task Extraction Accuracy**: Evaluates if all user-mentioned tasks are captured
   - **Memory Relevance**: Assesses if retrieved memories are useful and utilized
   - **Coaching Quality**: Judges ADHD-appropriateness of coaching responses

3. **Configuration** (`config/evaluation/judge_config.yaml`)
   - Flexible model selection (local vs cloud)
   - Adjustable thresholds for each metric
   - Cost control settings
   - Progressive enhancement modes

4. **Integration** (Modified `gtd_coach/coach.py`)
   - Tracks all interactions during session
   - Triggers evaluation after wrap-up phase
   - Zero impact on session flow

### How It Works

1. **During Session**: Coach tracks all user inputs and responses
2. **After Wrap-up**: Session data is passed to evaluator
3. **Background Processing**: Evaluation runs asynchronously
4. **Results Storage**: Scores saved locally and optionally to Langfuse

### Testing

Run the test suite:
```bash
python3 test_evaluation.py
```

Results are saved to:
```
~/gtd-coach/data/evaluations/eval_<session_id>.json
```

### Current Limitations

1. **Observation Only**: No interventions yet (Phase 1 design)
2. **Post-Session**: Evaluations happen after session ends
3. **Local Fallback**: Uses local model when cloud unavailable

### Next Phases (Not Yet Implemented)

- **Phase 2**: Pattern learning from evaluation data
- **Phase 3**: Phase-boundary interventions
- **Phase 4**: Real-time adaptive behavior

### Configuration Options

Enable/disable evaluation:
```bash
export EVAL_ENABLED=false  # Disable completely
```

Sampling rate (reduce costs):
```bash
export EVAL_SAMPLING_RATE=0.5  # Evaluate 50% of interactions
```

### Evaluation Metrics

Each interaction is scored on:
- **Task Extraction**: 0.0-1.0 (threshold: 0.7)
- **Memory Relevance**: 0.0-1.0 (threshold: 0.5)
- **Coaching Quality**: 0.0-1.0 (threshold: 0.6)

### Cost Estimate

With current configuration:
- Local model only: $0.00 per session
- With OpenAI GPT-4o-mini: ~$0.015 per session
- With GPT-4o for quality: ~$0.025 per session

### Privacy & Security

- All evaluations respect existing privacy settings
- No additional data leaves the system
- Local-first approach with cloud as enhancement

## Summary

The LLM-as-a-Judge system is now integrated and operational in observation mode. It provides valuable insights into coaching quality without disrupting the ADHD-friendly flow that makes GTD Coach effective. Future phases will progressively add interventions based on learned patterns.