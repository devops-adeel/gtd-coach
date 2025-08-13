# Performance Baselines - GTD Coach LangGraph Agent

## Overview

This document defines the expected performance characteristics of the GTD Coach LangGraph agent. These baselines are used to detect performance regressions and ensure the system meets ADHD user requirements for responsiveness.

## Key Performance Indicators (KPIs)

### 1. Context Management Performance

| Metric | Baseline | Acceptable Range | Critical Threshold | Notes |
|--------|----------|------------------|-------------------|-------|
| Token Counting | 50ms | 30-70ms | >100ms | Using count_tokens_approximately |
| Message Trimming (4K) | 80ms | 50-120ms | >150ms | trim_messages with "last" strategy |
| Phase Summarization | 200ms | 150-300ms | >500ms | Summarizing phase on transition |
| Context Overflow Recovery | 150ms | 100-200ms | >300ms | Emergency trimming when >4K |

### 2. LM Studio Integration

| Metric | Baseline | Acceptable Range | Critical Threshold | Notes |
|--------|----------|------------------|-------------------|-------|
| Health Check | 500ms | 200ms-1s | >2s | GET /v1/models endpoint |
| Connection Retry | 2s | 1-3s per attempt | >5s | Exponential backoff (3 attempts) |
| Chat Completion (avg) | 2.5s | 1-4s | >5s | 32K context, local inference |
| Streaming First Token | 800ms | 500ms-1.2s | >2s | Time to first streamed token |
| Total Response Time | 3s | 2-5s | >8s | Complete response generation |

### 3. Phase Execution Times

| Phase | Target Duration | Acceptable Range | User Experience Impact |
|-------|----------------|------------------|----------------------|
| STARTUP | 2 min | 1.5-2.5 min | Welcome and readiness check |
| MIND_SWEEP | 10 min | 9-11 min | Critical for ADHD capture |
| PROJECT_REVIEW | 12 min | 11-13 min | 45 sec per project target |
| PRIORITIZATION | 5 min | 4-6 min | ABC assignment |
| WRAP_UP | 3 min | 2-4 min | Save and celebrate |
| **Total Review** | 30 min | 28-32 min | ADHD-optimized duration |

### 4. Tool Execution Performance

| Tool Category | Baseline | Acceptable Range | Critical Threshold |
|--------------|----------|------------------|-------------------|
| Time Check | 50ms | 20-80ms | >150ms |
| Capture Tools | 200ms | 100-400ms | >1s |
| Memory Search | 800ms | 500ms-1.5s | >3s |
| Memory Save | 400ms | 200-800ms | >2s |
| Pattern Detection | 300ms | 200-500ms | >1s |
| Intervention Check | 150ms | 100-250ms | >500ms |

### 5. Checkpointing & Persistence

| Operation | Baseline | Acceptable Range | Critical Threshold |
|-----------|----------|------------------|-------------------|
| SQLite Checkpoint Save | 150ms | 100-250ms | >500ms |
| Checkpoint Load | 100ms | 50-200ms | >400ms |
| Session Recovery | 500ms | 300-800ms | >2s |
| State Serialization | 80ms | 50-150ms | >300ms |

### 6. Token Usage Metrics

| Metric | Target | Acceptable Range | Warning Threshold |
|--------|--------|------------------|-------------------|
| Tokens per Phase | 3K | 2K-4K | >5K |
| Context Overflows/Session | 1 | 0-2 | >3 |
| Total Session Tokens | 15K | 10K-20K | >25K |
| Token Efficiency | 80% | 70-90% | <60% |

*Token Efficiency = (Useful tokens / Total tokens) × 100*

## Performance by System Configuration

### Minimum Requirements
- **CPU**: 4 cores @ 2.5GHz
- **RAM**: 8GB (4GB for LM Studio)
- **Model**: Llama 3.1 8B Q4_K_M
- **Expected Performance**: Baseline values

### Recommended Configuration
- **CPU**: 8 cores @ 3.0GHz or M1/M2 Mac
- **RAM**: 16GB
- **Model**: Llama 3.1 8B Q4_K_M
- **Expected Performance**: 20-30% faster than baseline

### Optimal Configuration
- **GPU**: NVIDIA RTX 3060 or better
- **RAM**: 32GB
- **Model**: Llama 3.1 8B Q5_K_M or higher
- **Expected Performance**: 50-70% faster than baseline

## Monitoring & Alerting Thresholds

### Real-time Monitoring
```python
# Context metrics tracked per phase
context_metrics = {
    'total_tokens': 0,
    'phase_tokens': {},
    'overflow_count': 0
}
```

### Alert Conditions

1. **Performance Degradation Alert**
   - Any metric exceeds critical threshold
   - 3 consecutive operations exceed acceptable range
   - Total review time exceeds 35 minutes

2. **Context Management Alert**
   - More than 3 context overflows per session
   - Token usage exceeds 25K for session
   - Phase summarization fails

3. **Connection Issues Alert**
   - LM Studio health check fails 3 times
   - Connection retry exhausted (3 attempts)
   - Response timeout (>30s)

## Testing Performance

### Benchmark Suite
```bash
# Run performance benchmarks
pytest tests/agent/test_performance_benchmarks.py -v

# Generate performance report
pytest tests/agent/test_performance_benchmarks.py \
    --benchmark-only \
    --benchmark-json=performance_report.json

# Compare with baseline
pytest tests/agent/test_performance_benchmarks.py \
    --benchmark-compare=data/baseline_metrics.json
```

### Performance Test Categories

1. **Micro-benchmarks**
   - Token counting speed
   - Message trimming efficiency
   - State serialization

2. **Component Benchmarks**
   - Tool execution latency
   - LM Studio response time
   - Checkpoint operations

3. **End-to-End Benchmarks**
   - Complete phase execution
   - Full 30-minute review
   - Interrupt and resume cycle

## Optimization Strategies

### Current Optimizations

1. **Aggressive Token Management**
   - 4K token limit (12.5% of 32K context)
   - Reduces computational cost (quadratic scaling)
   - Improves response latency

2. **Phase-based Summarization**
   - Reduces message history between phases
   - Maintains context while reducing tokens
   - Prevents context overflow

3. **Mock-first Testing**
   - Ensures consistent performance baselines
   - Enables reliable CI/CD pipelines
   - Reduces test execution time

### Future Optimization Opportunities

1. **Connection Pooling**
   - Reuse LM Studio connections
   - Reduce connection overhead
   - Implement connection pool (size: 2-3)

2. **Caching Layer**
   - Cache frequent LLM responses
   - Implement TTL-based cache (5 min)
   - Cache hit target: 20-30%

3. **Parallel Tool Execution**
   - Execute independent tools concurrently
   - Use asyncio for I/O-bound operations
   - Potential 30-40% latency reduction

4. **Dynamic Token Limits**
   - Adjust token limit based on phase
   - STARTUP: 2K tokens
   - MIND_SWEEP: 4K tokens
   - PROJECT_REVIEW: 6K tokens

## Performance Regression Detection

### Automated Checks
```python
def test_performance_regression(benchmark, baseline_metrics):
    """Detect performance regressions"""
    current = benchmark(operation_under_test)
    baseline = baseline_metrics[operation_name]
    
    # Allow 20% degradation before failing
    assert current.mean < baseline * 1.2
    
    # Warn if 10% degradation
    if current.mean > baseline * 1.1:
        warnings.warn(f"Performance degraded by {degradation}%")
```

### Manual Review Triggers
- PR increases latency >10%
- New dependency affects performance
- Context management changes
- LLM client modifications

## Historical Performance Trends

### Version History
| Version | Date | Context Trim | LM Response | Total Review | Notes |
|---------|------|--------------|-------------|--------------|-------|
| v1.0.0 | 2024-01 | 150ms | 4s | 35 min | Initial migration |
| v1.1.0 | 2024-02 | 100ms | 3s | 32 min | Optimized trimming |
| v1.2.0 | 2024-03 | 80ms | 2.5s | 30 min | Current baseline |

### Performance Improvements
- **v1.1.0**: 33% reduction in context trimming latency
- **v1.2.0**: 17% reduction in LM Studio response time
- **v1.2.0**: 14% reduction in total review duration

## Reporting Performance Issues

When reporting performance issues, include:

1. **System Configuration**
   - CPU/GPU specs
   - Available RAM
   - LM Studio version
   - Model variant (Q4_K_M, Q5_K_M, etc.)

2. **Performance Metrics**
   - Actual vs expected times
   - Context overflow count
   - Token usage statistics

3. **Reproduction Steps**
   - Specific phase or tool affected
   - Consistent or intermittent issue
   - Error messages or timeouts

4. **Logs**
   - Agent logs with timing info
   - LM Studio server logs
   - System resource usage

## Conclusion

These performance baselines ensure the GTD Coach remains responsive and effective for ADHD users. Regular monitoring and optimization maintain the 30-minute review target while providing a smooth, interruption-free experience.

The conservative 4K token limit and aggressive trimming strategy are intentional design choices that prioritize:
- Consistent performance
- Predictable latency
- Cost-effective operation
- Reliable context management

Any changes to these baselines should be carefully evaluated for their impact on the ADHD user experience.