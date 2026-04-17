# Virtual DAG Orchestrator - One-Shot Game Generation

This repo benchmarks whether a single model response can produce a complete, playable Python game by simulating an orchestrated multi-step build pipeline inside one prompt.

The core idea is simple: instead of asking a model to "just write the game", the prompt makes it behave like a full orchestrator. It first refines intent, writes a spec, constructs a dependency-aware DAG, critiques that DAG, writes node prompts, virtually executes those nodes in memory, reviews the integrated build, and only then emits the final single-file game.

The inspiration for this approach came from [Bijan Bowen](https://www.youtube.com/@Bijanbowen).

## What "Virtual Orchestrator" Means

A true orchestrator would make many separate model calls:

1. One call writes intent.
2. Another writes the spec.
3. Others generate subsystems in parallel.
4. Review nodes inspect intermediate artifacts.
5. An integration step merges outputs.
6. Final QA and hardening happen after that.

This repo does not do that with actual external orchestration infrastructure. Instead, the prompt asks one sufficiently capable model to simulate that whole workflow internally in a single response.

That is why this is a virtual DAG orchestrator:

- The DAG is real as a planning artifact.
- The node prompts are real and self-contained.
- The execution log is virtual rather than backed by separate API calls.
- The model is effectively role-playing planner, generator, reviewer, integrator, and QA in one large context window.

## Why This Often Works Better Than A Plain Prompt

The virtual orchestrator forces the model to spend tokens on:

- intent clarification
- concrete success criteria
- dependency planning
- subsystem decomposition
- adversarial review
- integration checks
- final hardening

That extra structure usually improves one-shot quality. In practice, it increases the odds that the final game is actually runnable, coherent, and polished instead of collapsing into partial code, loose ideas, or missing systems.

The tradeoff is straightforward: it uses more tokens. You are paying context and output budget for planning and self-critique in exchange for a better chance of getting a stronger first-pass result.

## How Close This Gets To A True Orchestrator

For strong large-context frontier models, this virtual approach probably gets around 95-97% of what a true orchestrator would deliver for this specific one-shot use case.

Why not 100%?

- A real orchestrator can run genuinely separate node executions.
- It can branch, retry, and re-run only failed steps.
- It can use specialized models per node.
- It can validate intermediate artifacts programmatically.
- It can preserve cleaner separation between planning, generation, review, and integration.

So the true orchestrator is still better in principle. The gap becomes more important when you use smaller models, because smaller models are much less reliable at holding this entire simulated pipeline in memory at once. A real orchestrator helps those smaller models more because it externalizes memory, decomposition, and retries instead of demanding that everything stay coherent inside one huge answer.

## Prompt Templates

There are two top-level prompt files:

- [2d_prompt.md](/Users/granite/virtual_dag_orchestrator_oneshot_games/2d_prompt.md)
- [3d_prompt.md](/Users/granite/virtual_dag_orchestrator_oneshot_games/3d_prompt.md)

They are nearly identical by design. The orchestration method is the same in both. The main difference is the target game brief:

- `2d_prompt.md` targets a 2D space shooter
- `3d_prompt.md` targets a 3D flight sim

Everything else stays mostly constant so the benchmark is testing model capability, not wildly different prompt engineering strategies.

## Prompt Pipeline

Each prompt instructs the model to produce output in this rough order:

1. `intent.md`
2. `spec.md`
3. a full orchestrator-ready DAG
4. a hostile DAG review with fixes
5. self-contained prompts for every DAG node
6. a virtual DAG execution log
7. final integration notes
8. a brutal adversarial review of the integrated game
9. the final runnable single-file Python game
10. short run instructions
11. a final quality verdict

This sequencing matters. It pushes the model to decide what it is building before it writes code, and to inspect likely failure points before it commits to the final output.

## Project Structure

```text
.
├── 2d/                      # Generated 2D games from different models
├── 3d/                      # Generated 3D games from different models
├── 2d_prompt.md             # Virtual orchestrator prompt for 2D space shooters
├── 3d_prompt.md             # Virtual orchestrator prompt for 3D flight sims
├── LICENSE
└── README.md
```

## Running The Games

### Prerequisites

- Python 3.10+
- `pygame-ce` or `pygame`

### Quick Start

```bash
pip install pygame-ce pygame

python 2d/2d_claude_sonnet_4.6.py
python 3d/3d_gemini.py
```

Most generated files are self-contained single-file games. Many also include minimal auto-install bootstrap logic for `pygame-ce` or `pygame`.

### Controls

Controls vary by generated game. Most builds include on-screen instructions or obvious keyboard defaults.

## What This Repo Is Testing

This benchmark is mainly testing whether a model can:

1. follow a deep structured generation workflow
2. keep multiple intermediate artifacts coherent in one context
3. produce complete runnable code instead of placeholders
4. generate gameplay, feedback, progression, and HUD in one shot
5. survive adversarial self-review without losing the final implementation

It is not a perfect substitute for a real orchestrator system. It is a practical approximation that deliberately spends more tokens to buy higher one-shot reliability and output quality.

## Results Pattern

The generated games have a very strong shared signature. Across models, the most successful one-shotted outputs converge on the same high-reward arcade formula:

- heavy neon palettes with cyan, magenta, purple, and bright white accents
- aggressive particles for explosions, trails, engine glow, and impact feedback
- screen shake on damage and big events
- glow effects built from alpha surfaces, additive layering, or bright overlapping primitives
- responsive movement, dash, or boost-heavy control schemes

This is one of the clearest findings in the repo: neon plus particles plus shake plus fast controls is an extremely effective cheat code for making a simple game feel much more expensive than it really is. Models seem to converge on it because it produces a high level of perceived polish for relatively low implementation complexity.

## Standout Outputs

Some files stand out for different reasons:

- [2d/2d_claude_sonnet_4.6.py](/Users/granite/virtual_dag_orchestrator_oneshot_games/2d/2d_claude_sonnet_4.6.py): strongest overall 2D result. It has the best mix of production value, enemy variety, pickups, visual polish, and code readability.
- [2d/2d_chatgpt5.4.py](/Users/granite/virtual_dag_orchestrator_oneshot_games/2d/2d_chatgpt5.4.py): most feature-rich 2D build. It pushes progression, weapon evolution, HUD depth, and enemy behavior density harder than most of the set.
- [3d/3d_grok.py](/Users/granite/virtual_dag_orchestrator_oneshot_games/3d/3d_grok.py): most ambitious 3D implementation. It gets closest to feeling like a real 3D game by leaning into actual 3D math, rotations, and camera behavior.
- [3d/3d_chatgpt_extended.py](/Users/granite/virtual_dag_orchestrator_oneshot_games/3d/3d_chatgpt_extended.py): most complex single-file build. It is extremely long and dense, and it tries to act like a full mini-game rather than a narrow prototype.
- [2d/2d_gemini.py](/Users/granite/virtual_dag_orchestrator_oneshot_games/2d/2d_gemini.py): simplest elegant result. It is cleaner and easier to read than many of the larger outputs while still being fun to play.

## What The Models Seem To Optimize For

The outputs suggest different default strengths:

- Claude tends to be strongest at polish, readability, and moment-to-moment game feel.
- Grok tends to be the most technically ambitious, especially when the task rewards explicit spatial or 3D reasoning.
- ChatGPT tends to add more systems, more upgrades, and more feature density.
- Gemini tends to produce cleaner, simpler, and more readable implementations.

These are not universal laws, but they are visible patterns in this repo.

## Main Lesson From The Games

The best one-shotted games do not just add more code or more enemy count. The strongest outputs give enemies distinct personalities, add progression or pickup systems, and create enough juice that the game feels good immediately.

That matters because these prompts are trying to achieve a polished vertical slice in one pass, not an engine or framework. The repo suggests that a one-shot game becomes convincing when it has:

- clear movement and combat readability
- immediate audiovisual feedback
- obvious escalation
- at least light progression or upgrade structure
- enemies that behave differently enough to create texture

In other words, the universal lesson here is not just that LLMs can write arcade games in one shot. It is that they can get surprisingly close to "feels good" if the prompt steers them toward high-leverage polish patterns.

## Models In The Repo

The repo includes outputs from models such as:

- ChatGPT 5.4
- Claude Sonnet 4.6
- Gemini
- Grok
- MiniMax 2.7
- Nemotron-3-Super-120B-A12B
- Qwen 3.5 397B A17B
- Gemma 4 31B IT

## Practical Takeaway

If you have a strong model with a large context window, a virtual orchestrator prompt is often enough to get most of the upside of orchestration without building orchestration infrastructure.

If you want maximum reliability, retries, tool use, intermediate validation, or stronger performance from smaller models, a true orchestrator is still the better system design.
