# How to Set Up GTD Coach

## Installation Options

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/gtd-coach.git
cd gtd-coach

# Build and run
./scripts/deployment/docker-run.sh build
./scripts/deployment/docker-run.sh
```

### Option 2: Local Python

```bash
# Clone repository
git clone https://github.com/yourusername/gtd-coach.git
cd gtd-coach

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the coach
python -m gtd_coach
```

## LM Studio Setup

1. Download [LM Studio](https://lmstudio.ai/)
2. Install Llama 3.1 8B model (Q4_K_M quantization recommended)
3. Start the server on port 1234
4. Verify at http://localhost:1234/v1/models

## Environment Configuration

```bash
# Copy example configuration
cp config/.env.example .env

# Edit with your settings
nano .env
```

Essential variables:
```bash
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=meta-llama-3.1-8b-instruct
```

## Verify Installation

```bash
# Test timer
./scripts/timer.sh 1 "Test complete!"

# Test LLM connection
python3 scripts/test_llm_client.py

# Run a demo review
python3 demo-review.py
```

## Troubleshooting

### LM Studio Connection Failed
- Ensure LM Studio is running
- Check model is loaded
- Verify URL in .env matches LM Studio settings

### Audio Alerts Not Working
- macOS: Grant terminal audio permissions
- Linux: Install `sox` package
- Windows: Audio alerts currently unsupported

### Docker Issues
- Ensure Docker Desktop is running
- Check available memory (need 4GB minimum)
- Try rebuilding: `docker compose build --no-cache`