"""M0 demo: feed a realistic Claude Code session through the booth and hear it called.

    python3 -m booth.demo            # generate + speak
    python3 -m booth.demo --silent   # generate + print only (no audio)

Proves the whole pipeline: events -> commentary (LLM or template fallback) -> say.
"""
import sys

from . import commentary, player

# A realistic little half-inning: a request, some tool work, a win.
SAMPLE = [
    {"kind": "session_start", "desc": "session started"},
    {"kind": "prompt", "desc": "user asked: add a /health endpoint and a test for it"},
    {"kind": "post_tool", "desc": "post_tool Read server.py"},
    {"kind": "post_tool", "desc": "post_tool Edit server.py (added /health route)"},
    {"kind": "post_tool", "desc": "post_tool Write test_health.py"},
    {"kind": "post_tool", "desc": "post_tool Bash pytest -> 3 passed in 0.4s"},
    {"kind": "stop", "desc": "turn finished, tests green"},
]


def main():
    silent = "--silent" in sys.argv
    lines = commentary.call(SAMPLE, chatty="lively", big_moment=True)
    if not lines:
        print("(booth had nothing to say)")
        return
    for line in lines:
        print(f"  {line['speaker'].upper():9} {line['text']}")
        if not silent:
            player.enqueue(line)


if __name__ == "__main__":
    main()
