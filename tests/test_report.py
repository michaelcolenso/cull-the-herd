"""Tests for report module."""

import json
from pathlib import Path

import pytest

from photo_critic.report import (
    calculate_statistics,
    filter_by_score,
    generate_json_report,
    generate_markdown_report,
    generate_report,
    merge_results,
    parse_critique,
)


def make_succeeded_result(custom_id: str, critique: dict) -> dict:
    """Create a mock succeeded API result."""
    return {
        "custom_id": custom_id,
        "result": {
            "type": "succeeded",
            "message": {"content": [{"type": "text", "text": json.dumps(critique)}]},
        },
    }


def make_sample_critique(
    overall: float = 7.5,
    composition: float = 8.0,
    lighting: float = 7.0,
    subject: float = 7.5,
    technical: float = 7.5,
) -> dict:
    """Create a sample critique dictionary."""
    return {
        "overall_score": overall,
        "composition_score": composition,
        "composition_notes": "Good use of rule of thirds",
        "lighting_score": lighting,
        "lighting_notes": "Natural lighting works well",
        "subject_score": subject,
        "subject_notes": "Clear subject matter",
        "technical_score": technical,
        "technical_notes": "Sharp focus throughout",
        "summary": "A well-composed photograph with good technical execution.",
        "strengths": ["Strong composition", "Good lighting"],
        "improvements": ["Could benefit from more contrast"],
    }


class TestParseCritique:
    """Tests for parse_critique function."""

    def test_parse_succeeded_result(self) -> None:
        """Test parsing a succeeded result."""
        critique = make_sample_critique()
        result = make_succeeded_result("test_id", critique)
        parsed = parse_critique(result)

        assert parsed is not None
        assert parsed["overall_score"] == 7.5
        assert parsed["composition_score"] == 8.0

    def test_parse_with_markdown_code_blocks(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        critique = make_sample_critique()
        result = {
            "custom_id": "test_id",
            "result": {
                "type": "succeeded",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"```json\n{json.dumps(critique)}\n```",
                        }
                    ]
                },
            },
        }
        parsed = parse_critique(result)
        assert parsed is not None
        assert parsed["overall_score"] == 7.5

    def test_parse_failed_result(self) -> None:
        """Test that failed results return None."""
        result = {
            "custom_id": "test_id",
            "result": {"type": "errored", "error": {"message": "API error"}},
        }
        parsed = parse_critique(result)
        assert parsed is None

    def test_parse_invalid_json(self) -> None:
        """Test that invalid JSON returns None."""
        result = {
            "custom_id": "test_id",
            "result": {
                "type": "succeeded",
                "message": {"content": [{"type": "text", "text": "not valid json"}]},
            },
        }
        parsed = parse_critique(result)
        assert parsed is None

    def test_parse_no_text_content(self) -> None:
        """Test result with no text content returns None."""
        result = {
            "custom_id": "test_id",
            "result": {
                "type": "succeeded",
                "message": {"content": [{"type": "image", "data": "..."}]},
            },
        }
        parsed = parse_critique(result)
        assert parsed is None


class TestMergeResults:
    """Tests for merge_results function."""

    def test_merge_single_result(self) -> None:
        """Test merging a single result with metadata."""
        critique = make_sample_critique()
        batch_results = [make_succeeded_result("img_0001", critique)]
        metadata = [
            {
                "custom_id": "img_0001",
                "filename": "photo.jpg",
                "path": "/path/to/photo.jpg",
                "original_dimensions": (1920, 1080),
            }
        ]

        merged = merge_results(batch_results, metadata)

        assert len(merged) == 1
        assert merged[0]["filename"] == "photo.jpg"
        assert merged[0]["overall_score"] == 7.5
        assert merged[0]["original_dimensions"] == (1920, 1080)

    def test_merge_skips_failed_results(self) -> None:
        """Test that failed results are skipped."""
        critique = make_sample_critique()
        batch_results = [
            make_succeeded_result("img_0001", critique),
            {"custom_id": "img_0002", "result": {"type": "errored"}},
        ]
        metadata = [
            {"custom_id": "img_0001", "filename": "photo1.jpg", "path": "/p1"},
            {"custom_id": "img_0002", "filename": "photo2.jpg", "path": "/p2"},
        ]

        merged = merge_results(batch_results, metadata)
        assert len(merged) == 1
        assert merged[0]["filename"] == "photo1.jpg"

    def test_merge_missing_metadata(self) -> None:
        """Test merging when metadata is missing."""
        critique = make_sample_critique()
        batch_results = [make_succeeded_result("img_0001", critique)]
        metadata: list = []  # No matching metadata

        merged = merge_results(batch_results, metadata)
        assert len(merged) == 1
        assert merged[0]["filename"] == "unknown"


class TestFilterByScore:
    """Tests for filter_by_score function."""

    def test_filter_returns_above_threshold(self) -> None:
        """Test filtering keeps results above threshold."""
        results = [
            {"overall_score": 8.0, "filename": "high.jpg"},
            {"overall_score": 5.0, "filename": "low.jpg"},
            {"overall_score": 7.0, "filename": "mid.jpg"},
        ]

        filtered = filter_by_score(results, min_score=6.5)
        assert len(filtered) == 2
        filenames = [r["filename"] for r in filtered]
        assert "high.jpg" in filenames
        assert "mid.jpg" in filenames
        assert "low.jpg" not in filenames

    def test_filter_with_zero_threshold(self) -> None:
        """Test that zero threshold returns all results."""
        results = [
            {"overall_score": 8.0},
            {"overall_score": 2.0},
        ]
        filtered = filter_by_score(results, min_score=0.0)
        assert len(filtered) == 2

    def test_filter_handles_missing_score(self) -> None:
        """Test filtering handles missing overall_score."""
        results = [
            {"overall_score": 8.0},
            {"filename": "no_score.jpg"},  # Missing score
        ]
        filtered = filter_by_score(results, min_score=5.0)
        assert len(filtered) == 1


class TestCalculateStatistics:
    """Tests for calculate_statistics function."""

    def test_calculate_empty_results(self) -> None:
        """Test statistics for empty results."""
        stats = calculate_statistics([])
        assert stats["total_images"] == 0
        assert stats["mean_overall_score"] == 0.0

    def test_calculate_mean_scores(self) -> None:
        """Test mean score calculation."""
        results = [
            {
                "overall_score": 8.0,
                "composition_score": 7.0,
                "lighting_score": 8.0,
                "subject_score": 9.0,
                "technical_score": 8.0,
            },
            {
                "overall_score": 6.0,
                "composition_score": 5.0,
                "lighting_score": 6.0,
                "subject_score": 7.0,
                "technical_score": 6.0,
            },
        ]

        stats = calculate_statistics(results)

        assert stats["total_images"] == 2
        assert stats["mean_overall_score"] == 7.0
        assert stats["mean_composition_score"] == 6.0
        assert stats["mean_lighting_score"] == 7.0

    def test_calculate_score_distribution(self) -> None:
        """Test score distribution calculation."""
        results = [
            {
                "overall_score": 9.5,
                "composition_score": 9,
                "lighting_score": 9,
                "subject_score": 9,
                "technical_score": 9,
            },  # excellent
            {
                "overall_score": 8.5,
                "composition_score": 8,
                "lighting_score": 8,
                "subject_score": 8,
                "technical_score": 8,
            },  # great
            {
                "overall_score": 7.5,
                "composition_score": 7,
                "lighting_score": 7,
                "subject_score": 7,
                "technical_score": 7,
            },  # good
            {
                "overall_score": 4.0,
                "composition_score": 4,
                "lighting_score": 4,
                "subject_score": 4,
                "technical_score": 4,
            },  # poor
        ]

        stats = calculate_statistics(results)

        assert stats["score_distribution"]["excellent (9-10)"] == 1
        assert stats["score_distribution"]["great (8-9)"] == 1
        assert stats["score_distribution"]["good (7-8)"] == 1
        assert stats["score_distribution"]["poor (0-5)"] == 1


class TestGenerateJsonReport:
    """Tests for generate_json_report function."""

    def test_generate_json_creates_file(self, tmp_path: Path) -> None:
        """Test that JSON report is created."""
        results = [
            {
                "overall_score": 8.0,
                "composition_score": 8.0,
                "lighting_score": 8.0,
                "subject_score": 8.0,
                "technical_score": 8.0,
                "filename": "test.jpg",
            }
        ]
        output_path = tmp_path / "report.json"

        generate_json_report(results, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            report = json.load(f)
        assert "generated_at" in report
        assert "statistics" in report
        assert "results" in report

    def test_generate_json_sorted_by_score(self, tmp_path: Path) -> None:
        """Test that results are sorted by score descending."""
        results = [
            {
                "overall_score": 5.0,
                "composition_score": 5,
                "lighting_score": 5,
                "subject_score": 5,
                "technical_score": 5,
                "filename": "low.jpg",
            },
            {
                "overall_score": 9.0,
                "composition_score": 9,
                "lighting_score": 9,
                "subject_score": 9,
                "technical_score": 9,
                "filename": "high.jpg",
            },
            {
                "overall_score": 7.0,
                "composition_score": 7,
                "lighting_score": 7,
                "subject_score": 7,
                "technical_score": 7,
                "filename": "mid.jpg",
            },
        ]
        output_path = tmp_path / "report.json"

        generate_json_report(results, output_path)

        with open(output_path) as f:
            report = json.load(f)
        assert report["results"][0]["filename"] == "high.jpg"
        assert report["results"][1]["filename"] == "mid.jpg"
        assert report["results"][2]["filename"] == "low.jpg"


class TestGenerateMarkdownReport:
    """Tests for generate_markdown_report function."""

    def test_generate_markdown_creates_file(self, tmp_path: Path) -> None:
        """Test that Markdown report is created."""
        results = [
            {
                "overall_score": 8.0,
                "composition_score": 8.0,
                "composition_notes": "Good",
                "lighting_score": 8.0,
                "lighting_notes": "Good",
                "subject_score": 8.0,
                "subject_notes": "Good",
                "technical_score": 8.0,
                "technical_notes": "Good",
                "filename": "test.jpg",
                "path": "/path/test.jpg",
                "summary": "Great photo",
                "strengths": ["Sharp"],
                "improvements": ["Crop tighter"],
            }
        ]
        output_path = tmp_path / "report.md"

        generate_markdown_report(results, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "# Photo Critic Report" in content
        assert "test.jpg" in content
        assert "Great photo" in content


class TestGenerateReport:
    """Tests for generate_report function."""

    def test_generate_report_json(self, tmp_path: Path) -> None:
        """Test generating JSON format report."""
        critique = make_sample_critique()
        batch_results = [make_succeeded_result("img_0001", critique)]
        metadata = [{"custom_id": "img_0001", "filename": "test.jpg", "path": "/test"}]
        output_path = tmp_path / "report"

        generate_report(batch_results, metadata, output_path, format="json")

        assert (tmp_path / "report.json").exists()
        assert not (tmp_path / "report.md").exists()

    def test_generate_report_markdown(self, tmp_path: Path) -> None:
        """Test generating Markdown format report."""
        critique = make_sample_critique()
        batch_results = [make_succeeded_result("img_0001", critique)]
        metadata = [{"custom_id": "img_0001", "filename": "test.jpg", "path": "/test"}]
        output_path = tmp_path / "report"

        generate_report(batch_results, metadata, output_path, format="markdown")

        assert not (tmp_path / "report.json").exists()
        assert (tmp_path / "report.md").exists()

    def test_generate_report_both(self, tmp_path: Path) -> None:
        """Test generating both formats."""
        critique = make_sample_critique()
        batch_results = [make_succeeded_result("img_0001", critique)]
        metadata = [{"custom_id": "img_0001", "filename": "test.jpg", "path": "/test"}]
        output_path = tmp_path / "report"

        generate_report(batch_results, metadata, output_path, format="both")

        assert (tmp_path / "report.json").exists()
        assert (tmp_path / "report.md").exists()

    def test_generate_report_with_min_score(self, tmp_path: Path) -> None:
        """Test that min_score filter is applied."""
        high_critique = make_sample_critique(overall=9.0)
        low_critique = make_sample_critique(overall=4.0)
        batch_results = [
            make_succeeded_result("img_0001", high_critique),
            make_succeeded_result("img_0002", low_critique),
        ]
        metadata = [
            {"custom_id": "img_0001", "filename": "high.jpg", "path": "/high"},
            {"custom_id": "img_0002", "filename": "low.jpg", "path": "/low"},
        ]
        output_path = tmp_path / "report"

        generate_report(
            batch_results, metadata, output_path, format="json", min_score=7.0
        )

        with open(tmp_path / "report.json") as f:
            report = json.load(f)
        assert len(report["results"]) == 1
        assert report["results"][0]["filename"] == "high.jpg"

    def test_generate_report_invalid_format(self, tmp_path: Path) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format"):
            generate_report([], [], tmp_path / "report", format="invalid")
