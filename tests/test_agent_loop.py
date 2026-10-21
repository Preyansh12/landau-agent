"""Offline check of the agent loop and transcript writing with a scripted fake model."""
import os
import sys
import types
from types import SimpleNamespace as NS


class _FakeMessages:
    def __init__(self):
        self.turn = 0

    def create(self, **kw):
        self.turn += 1
        if self.turn == 1:      # model asks for a tool that fails cleanly (no parent yet)
            return NS(stop_reason="tool_use", content=[
                NS(type="text", text="Setting the supercell first."),
                NS(type="tool_use", id="t1", name="set_supercell", input={"matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]]})])
        return NS(stop_reason="end_turn", content=[NS(type="text", text="The tool reported an error; I need a parent first.")])


def test_agent_loop_writes_transcript(tmp_path, monkeypatch):
    fake = types.ModuleType("anthropic")
    fake.Anthropic = lambda: NS(messages=_FakeMessages())
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.chdir(tmp_path)
    os.makedirs("results")
    from landau_agent import agent
    out = agent.run("test question", verbose=False, tag="fake")
    assert "error" in out.lower()
    text = open("results/fake_transcript.md").read()
    assert "set_supercell" in text and "Tool result" in text and "error" in text


def test_openai_compatible_backend(tmp_path, monkeypatch):
    """Same loop through the chat-completions (Gemini-compatible) backend, with a fake client."""
    turns = {"n": 0}

    def create(**kw):
        turns["n"] += 1
        assert kw["messages"][0]["role"] == "system" and kw["tools"][0]["type"] == "function"
        if turns["n"] == 1:
            call = NS(id="c1", function=NS(name="set_supercell", arguments='{"matrix": [[2,0,0],[0,2,0],[0,0,2]]}'))
            return NS(choices=[NS(message=NS(content="Checking.", tool_calls=[call]))])
        assert kw["messages"][-1]["role"] == "tool" and "error" in kw["messages"][-1]["content"]
        return NS(choices=[NS(message=NS(content="Tool error: no parent loaded.", tool_calls=None))])

    fake = types.ModuleType("openai")
    fake.OpenAI = lambda **kw: NS(chat=NS(completions=NS(create=create)))
    monkeypatch.setitem(sys.modules, "openai", fake)
    monkeypatch.chdir(tmp_path)
    os.makedirs("results")
    from landau_agent import agent
    monkeypatch.setattr(agent, "PROVIDER", "gemini")
    monkeypatch.setattr(agent, "MODEL", "fake-model")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    out = agent.run("q", verbose=False, tag="fakeoa")
    assert "error" in out.lower()
    assert "set_supercell" in open("results/fakeoa_transcript.md").read()
