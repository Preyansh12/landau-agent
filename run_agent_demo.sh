#!/usr/bin/env bash
# Live agent runs for the submission. Writes results/<tag>_transcript.md and results/<tag>_tool_log.json.
# Anthropic:  export ANTHROPIC_API_KEY=...
# Gemini:     export LANDAU_AGENT_PROVIDER=gemini GEMINI_API_KEY=... LANDAU_AGENT_MODEL=<gemini model id>
set -e
python -m landau_agent.agent "Is SrTiO3 ferroelectric? Start from the cubic Pm-3m parent and use the tools to decide." --tag agent_SrTiO3
python -m landau_agent.agent "Why is Ca3Ti2O7 ferroelectric? Start from the I4/mmm parent." --tag agent_Ca3Ti2O7
