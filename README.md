# Virtual DAG Orchestrator - One-Shot Game Generation

This project benchmarks AI models on their ability to generate complete, playable Python games in a single shot using a DAG orchestrator workflow.

## Overview

The prompt system ("GOD MODE ONE-SHOT GAME DEV") instructs an AI to:
1. Refine game intent into a spec
2. Create a dependency-aware DAG for game generation
3. Execute each node (planning, spec, architecture, generation, review, integration)
4. Output a final single-file Python game that's actually playable

## Project Structure

```
.
├── 2d/                      # 2D space shooter games
│   ├── 2d_chatgpt5.4.py
│   ├── 2d_claude_sonnet_4.6.py
│   ├── 2d_gemini.py
│   ├── 2d_grok.py
│   ├── 2d_minimax2.7.py
│   ├── 2d_nemotron-3-super-120b-a12b.py
│   └── 2d_qwen3.5-397b-a17b.py
├── 3d/                      # 3D flight simulator games
│   ├── 3d_chatgpt_extended.py
│   ├── 3d_chatgpt_free.py
│   ├── 3d_claude_sonnet_4.6.py
│   ├── 3d_gemini.py
│   ├── 3d_gemma-4-31b-it.py
│   ├── 3d_grok.py
│   ├── 3d_minimax-m2.7.py
│   ├── 3d_nemotron-3-super-120b-a12b.py
│   └── 3d_qwen3.5-397b-a17b.py
├── 2d_prompt.md             # Prompt used for 2D space shooter
├── 3d_prompt.md             # Prompt used for 3D flight sim
├── LICENSE                  # MIT License
└── README.md                # This file
```

## Running the Games

### Prerequisites

- Python 3.10+
- pygame (or pygame-ce)

### Quick Start

```bash
# Install pygame if needed
pip install pygame-ce pygame

# Run any game
python 2d/2d_claude_sonnet_4.6.py
python 3d/3d_claude_sonnet_4.6.py
```

Each game is self-contained in a single Python file with auto-install logic for pygame if not present.

### Controls

Each game may have different controls. On-screen instructions are provided in-game.

## Prompt Versions

- **2d_prompt.md**: Generates a 2D top-down space shooter
- **3d_prompt.md**: Generates a 3D flight simulator

Both prompts are nearly identical except for the game type specification.

## Models Tested

- ChatGPT 5.4
- Claude Sonnet 4.6
- Gemini
- Grok
- MiniMax 2.7
- Nemotron-3-Super-120B-A12B
- Qwen 3.5 397B A17B
- Gemma 4 31B IT

## Purpose

This benchmark tests whether AI models can:
1. Follow a complex multi-step orchestration workflow
2. Produce complete, runnable code (not pseudocode or placeholders)
3. Generate games with proper game loops, collisions, win/lose states, and polish
4. Work within constraints (single file, procedural graphics, no external assets)