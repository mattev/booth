"""Golden scenarios for the eval harness — representative event-batches the daemon
would hand to the commentary engine. Each `events` list uses the same {kind, desc} shape
that daemon._summarize produces. `desc` (scenario-level) is shown to the judge for grading.
"""

SCENARIOS = [
    {
        "name": "session_start",
        "desc": "A brand-new Claude Code session opens (should stay silent — no welcome filler).",
        "expect_silent": True,
        "events": [{"kind": "session_start", "desc": "session started"}],
    },
    {
        "name": "health_endpoint_win",
        "desc": "User asks for a feature + test; Claude does it and tests pass first try.",
        "big_moment": True,
        "events": [
            {"kind": "prompt", "desc": "user asked: add a /health endpoint and a test for it"},
            {"kind": "post_tool", "desc": "post_tool Read server.py"},
            {"kind": "post_tool", "desc": "post_tool Edit server.py (added /health route)"},
            {"kind": "post_tool", "desc": "post_tool Write test_health.py"},
            {"kind": "post_tool", "desc": "post_tool Bash pytest -> 3 passed in 0.4s"},
        ],
    },
    {
        "name": "failing_tests",
        "desc": "User runs the suite; tests fail.",
        "events": [
            {"kind": "prompt", "desc": "user asked: run the test suite"},
            {"kind": "post_tool", "desc": "post_tool Bash pytest -> 2 failed, 5 passed"},
        ],
    },
    {
        "name": "error_then_fix",
        "desc": "A build errors, Claude patches it, build goes green.",
        "events": [
            {"kind": "post_tool", "desc": "post_tool Bash npm run build -> error TS2345 in types.ts"},
            {"kind": "post_tool", "desc": "post_tool Edit types.ts"},
            {"kind": "post_tool", "desc": "post_tool Bash npm run build -> success"},
        ],
    },
    {
        "name": "long_refactor",
        "desc": "A sweeping rename across many files.",
        "events": [
            {"kind": "prompt", "desc": "user asked: rename UserService to AccountService everywhere"},
            {"kind": "post_tool", "desc": "post_tool Edit auth/user_service.py"},
            {"kind": "post_tool", "desc": "post_tool Edit auth/__init__.py"},
            {"kind": "post_tool", "desc": "post_tool Edit api/routes.py"},
            {"kind": "post_tool", "desc": "post_tool Edit tests/test_user.py"},
            {"kind": "post_tool", "desc": "post_tool Edit billing/account.py"},
            {"kind": "post_tool", "desc": "post_tool Edit docs/architecture.md"},
        ],
    },
    {
        "name": "noisy_reads",
        "desc": "Claude reads a pile of files to understand a flow — lots of low-drama events.",
        "events": [
            {"kind": "prompt", "desc": "user asked: how does the auth flow work?"},
            {"kind": "post_tool", "desc": "post_tool Read auth/login.py"},
            {"kind": "post_tool", "desc": "post_tool Read auth/session.py"},
            {"kind": "post_tool", "desc": "post_tool Read auth/tokens.py"},
            {"kind": "post_tool", "desc": "post_tool Read middleware/auth.py"},
            {"kind": "post_tool", "desc": "post_tool Read config/security.py"},
            {"kind": "post_tool", "desc": "post_tool Read tests/test_auth.py"},
        ],
    },
    {
        "name": "git_push",
        "desc": "User pushes their work to GitHub successfully.",
        "events": [
            {"kind": "prompt", "desc": "user asked: commit and push my changes"},
            {"kind": "post_tool", "desc": "post_tool Bash git commit -m 'fix auth bug'"},
            {"kind": "post_tool", "desc": "post_tool Bash git push -> main updated"},
        ],
    },
    {
        "name": "search_exploration",
        "desc": "User asks a 'where is X' question; Claude greps and reads.",
        "events": [
            {"kind": "prompt", "desc": "user asked: where is rate limiting handled?"},
            {"kind": "post_tool", "desc": "post_tool Grep 'rate.?limit' -> 4 matches"},
            {"kind": "post_tool", "desc": "post_tool Read middleware/throttle.py"},
        ],
    },
    {
        "name": "stop_after_win",
        "desc": "Claude finishes its turn after a successful change.",
        "events": [{"kind": "stop", "desc": "turn finished, all green"}],
    },
    {
        "name": "quiet_batch",
        "desc": "Nothing happened this tick — should stay silent (edge case).",
        "expect_silent": True,
        "events": [],
    },
]
