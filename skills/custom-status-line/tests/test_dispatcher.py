import json
import os
import stat
import pytest
from statusline.dispatcher import run_pipeline, load_pipeline_config, run_external_script


MOCK_CLAUDE = {
    "model": {"display_name": "Test Model", "id": "test-model"},
    "context_window": {"remaining_percentage": 85, "context_window_size": 200000,
                       "total_input_tokens": 1000, "total_output_tokens": 500,
                       "current_usage": {"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}},
    "cost": {"total_duration_ms": 60000, "total_api_duration_ms": 5000,
             "total_lines_added": 10, "total_lines_removed": 5, "total_cost_usd": 0.5},
    "cwd": "/tmp/test",
    "session_id": "test-session-123",
    "session_name": "",
    "rate_limits": {
        "five_hour": {"used_percentage": 5.0, "resets_at": 0},
        "seven_day": {"used_percentage": 28.5, "resets_at": 0},
    },
    "version": "1.0",
    "workspace": {"project_dir": "/tmp/test"},
    "transcript_path": "",
}


class TestLoadPipelineConfig:
    def test_creates_default_if_missing(self, tmp_path):
        config_path = tmp_path / "pipeline.json"
        config = load_pipeline_config(str(config_path))
        assert len(config["pipeline"]) >= 2
        assert config_path.exists()

    def test_reads_existing(self, tmp_path):
        config_path = tmp_path / "pipeline.json"
        config_path.write_text(json.dumps({
            "pipeline": [{"name": "test", "module": "base_info"}]
        }))
        config = load_pipeline_config(str(config_path))
        assert len(config["pipeline"]) == 1
        assert config["pipeline"][0]["name"] == "test"


class TestRunExternalScript:
    def test_runs_script_and_parses_output(self, tmp_path):
        script = tmp_path / "test.sh"
        script.write_text('#!/bin/bash\necho \'{"lines": ["hello"]}\'\n')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        result = run_external_script(str(script), {"claude": {}, "lines": []})
        assert result == ["hello"]

    def test_returns_none_on_bad_script(self, tmp_path):
        script = tmp_path / "bad.sh"
        script.write_text("#!/bin/bash\nexit 1\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        result = run_external_script(str(script), {"claude": {}, "lines": []})
        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        script = tmp_path / "bad.sh"
        script.write_text("#!/bin/bash\necho 'not json'\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        result = run_external_script(str(script), {"claude": {}, "lines": []})
        assert result is None


class TestRunPipeline:
    def test_module_entry_calls_function(self):
        def mock_run(claude_data, lines):
            return lines + ["added by mock"]

        modules = {"mock_mod": mock_run}
        pipeline = [{"name": "mock", "module": "mock_mod"}]
        result = run_pipeline(MOCK_CLAUDE, pipeline, modules)
        assert "added by mock" in result

    def test_skips_missing_module(self):
        pipeline = [{"name": "missing", "module": "nonexistent"}]
        result = run_pipeline(MOCK_CLAUDE, pipeline, {})
        assert result == []

    def test_script_entry_runs_external(self, tmp_path):
        script = tmp_path / "ext.sh"
        script.write_text('#!/bin/bash\necho \'{"lines": ["from script"]}\'\n')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        pipeline = [{"name": "ext", "script": str(script)}]
        result = run_pipeline(MOCK_CLAUDE, pipeline, {})
        assert result == ["from script"]
