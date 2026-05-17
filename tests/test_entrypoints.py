from __future__ import annotations

import subprocess
import sys


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False, timeout=30)


def test_run_classifier_script_mock_folder():
    result = run_cmd([sys.executable, "run_classifier.py", "--mode", "mock", "--folder", "data/images"])
    assert result.returncode == 0
    assert result.stdout.count('"source": "mock"') == 5
    assert '"entity_type": "non_threat_animal"' in result.stdout


def test_run_headless_script_no_replay():
    result = run_cmd([sys.executable, "run_headless.py", "--no-replay"])
    assert result.returncode == 0
    assert "ARIES headless run complete:" in result.stdout
    assert "Summary JSON:" in result.stdout


def test_run_self_check_script():
    result = run_cmd([sys.executable, "run_self_check.py"])
    assert result.returncode == 0
    assert "ARIES self-check passed" in result.stdout


def test_run_demo_missing_pygame_message_is_actionable():
    code = "import builtins; real=builtins.__import__\n" \
        "def fake(name,*a,**k):\n" \
        "    if name == 'pygame': raise ImportError('blocked')\n" \
        "    return real(name,*a,**k)\n" \
        "builtins.__import__=fake\n" \
        "import run_demo\n" \
        "run_demo.main()\n"
    result = run_cmd([sys.executable, "-c", code])
    assert result.returncode != 0
    assert "run_headless.py --no-replay" in result.stderr
