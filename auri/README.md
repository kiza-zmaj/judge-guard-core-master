# 🎙️ AURI — Claude-Powered Alexa Voice Assistant

> Transform any Alexa device into an ultra-intelligent assistant using Claude as the LLM brain, with neural voice, persistent memory, and Smart Home control.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│ Alexa Device │───▶│  Alexa Cloud  │───▶│  AWS Lambda   │───▶│  Claude API  │
│  (Echo/Show) │    │  (ASR + NLU)  │    │  (Python 3.11)│    │  (Anthropic) │
└─────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                       ┌───────────┐   ┌───────────┐   ┌───────────┐
                       │ DynamoDB   │   │  Polly     │   │    S3     │
                       │ (Memory)   │   │ (Neural    │   │ (Audio)   │
                       │            │   │  Voice)    │   │           │
                       └───────────┘   └───────────┘   └───────────┘
```

## Features

- 🧠 **Claude-powered intelligence** — Natural conversations in Brazilian Portuguese
- 💾 **Persistent memory** — Remembers your name, preferences, and conversation history
- 🔊 **Neural voice** — Vitória neural voice via Amazon Polly
- 📺 **Visual interface** — APL templates for Echo Show devices
- 🏠 **Smart Home** — Control lights, thermostats, and more
- ⚡ **Routines** — Predefined automations (bom dia, boa noite, trabalho, sair)

## Prerequisites

- [Amazon Developer account](https://developer.amazon.com/)
- [AWS account](https://aws.amazon.com/) (free tier works)
- [Anthropic API key](https://console.anthropic.com/)
- Node.js 18+ (for ASK CLI)
- Python 3.11+

## Quick Setup

### 1. Install CLIs

```bash
# ASK CLI (Alexa Skills Kit)
npm install -g ask-cli
ask configure

# AWS CLI
pip install awscli
aws configure
```

### 2. Run Setup

```bash
cd auri/
chmod +x scripts/*.sh
./scripts/setup.sh
```

This will:
- ✅ Check prerequisites
- ✅ Create DynamoDB table (`auri-users`)
- ✅ Store API key in Secrets Manager
- ✅ Install Python dependencies

### 3. Deploy

```bash
./scripts/deploy.sh
```

### 4. Test

```bash
# Simulator
./scripts/test.sh

# Interactive dialog
ask dialog --locale pt-BR
```

## Project Structure

```
auri/
├── ask-resources.json              # ASK CLI configuration
├── skill-package/
│   ├── skill.json                  # Skill manifest
│   ├── interactionModels/
│   │   └── custom/
│   │       └── pt-BR.json          # Interaction model (Portuguese)
│   └── assets/
│       └── apl/
│           ├── chat-interface.json  # Echo Show chat UI
│           └── launch-screen.json   # Welcome screen
├── lambda/
│   ├── lambda_function.py          # Main Lambda handler
│   ├── requirements.txt            # Python dependencies
│   ├── smart_home_handler.py       # Smart Home directives handler
│   └── utils/
│       ├── __init__.py
│       ├── claude_helper.py        # Claude API integration
│       ├── dynamodb_helper.py      # Persistence layer
│       └── polly_helper.py         # Neural TTS synthesis
├── infrastructure/
│   └── cfn-deployer/
│       └── skill-stack.yaml        # CloudFormation template
├── scripts/
│   ├── setup.sh                    # One-time setup
│   ├── deploy.sh                   # Build & deploy
│   └── test.sh                     # Run tests
└── tests/
    ├── conftest.py                 # Pytest fixtures
    ├── test_lambda.py              # Handler unit tests
    └── test_smart_home.py          # Smart Home tests
```

## Configuration

### Environment Variables (Lambda)

| Variable | Description | Default |
|----------|-------------|---------|
| `DYNAMODB_TABLE` | DynamoDB table name | `auri-users` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AURI_AUDIO_BUCKET` | S3 bucket for Polly audio | `auri-audio` |
| `ANTHROPIC_API_KEY` | Claude API key (prefer Secrets Manager) | — |

### Supported Intents

| Intent | Example | Description |
|--------|---------|-------------|
| ChatIntent | "me ajuda com o clima" | Ask any question (routed to Claude) |
| SmartHomeIntent | "liga a sala" | Control smart home devices |
| RoutineIntent | "ativa rotina bom dia" | Trigger predefined routines |
| SetNameIntent | "meu nome é João" | Set your name for personalization |
| HelpIntent | "ajuda" | Get help text |
| StopIntent | "para" | End the session |

### Polly Voices

| Voice | Language | Type | Recommended |
|-------|----------|------|-------------|
| Vitória | pt-BR | Neural | ✅ Default |
| Camila | pt-BR | Neural | Alternative |
| Ricardo | pt-BR | Standard | Male voice |
| Inês | pt-PT | Neural | Portugal |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Lambda timeout | Increase timeout (max 8s), reduce `MAX_RESPONSE_CHARS` |
| "Não entendi" | Check interaction model has enough sample utterances |
| No Claude response | Verify API key in Secrets Manager, check Lambda logs |
| APL not showing | Ensure device supports APL, check `_supports_apl()` |
| DynamoDB errors | Verify IAM role permissions, check table exists |

### View Logs

```bash
aws logs tail /aws/lambda/auri-skill --follow
```

## License

MIT
