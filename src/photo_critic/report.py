"""Report generation module for creating JSON and Markdown outputs."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_critique(result: dict[str, Any]) -> dict[str, Any] | None:
    """Parse critique from API result.

    Args:
        result: Batch result dictionary from API

    Returns:
        Parsed critique dictionary, or None if parsing failed
    """
    try:
        # Extract text content from response
        if result["result"]["type"] == "succeeded":
            message = result["result"]["message"]
            content = message["content"]

            # Find text content
            text_content = None
            for block in content:
                if block["type"] == "text":
                    text_content = block["text"]
                    break

            if not text_content:
                logger.warning(f"No text content in result: {result['custom_id']}")
                return None

            # Try to parse JSON from text
            # Handle case where response might have markdown code blocks
            text_content = text_content.strip()
            if text_content.startswith("```json"):
                text_content = text_content[7:]
            if text_content.startswith("```"):
                text_content = text_content[3:]
            if text_content.endswith("```"):
                text_content = text_content[:-3]

            critique = json.loads(text_content.strip())
            return critique

        else:
            logger.warning(
                f"Result not succeeded: {result['custom_id']} - "
                f"{result['result']['type']}"
            )
            return None

    except Exception as e:
        logger.error(f"Failed to parse critique for {result['custom_id']}: {e}")
        return None


def merge_results(
    batch_results: list[dict[str, Any]], image_metadata: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge batch results with image metadata.

    Args:
        batch_results: Results from batch API
        image_metadata: Metadata from prepare_batch()

    Returns:
        List of merged result dictionaries
    """
    # Create lookup by custom_id
    metadata_by_id = {item["custom_id"]: item for item in image_metadata}

    merged = []

    for result in batch_results:
        custom_id = result["custom_id"]

        # Get metadata
        metadata = metadata_by_id.get(custom_id, {})

        # Parse critique
        critique = parse_critique(result)

        if critique is None:
            logger.warning(f"Skipping result with no critique: {custom_id}")
            continue

        # Merge
        merged_item = {
            "custom_id": custom_id,
            "filename": metadata.get("filename", "unknown"),
            "path": metadata.get("path", "unknown"),
            "original_dimensions": metadata.get("original_dimensions", (0, 0)),
            **critique,
        }

        merged.append(merged_item)

    logger.info(f"Merged {len(merged)} results")
    return merged


def filter_by_score(
    results: list[dict[str, Any]], min_score: float
) -> list[dict[str, Any]]:
    """Filter results by minimum overall score.

    Args:
        results: List of merged result dictionaries
        min_score: Minimum overall_score to include

    Returns:
        Filtered list of results
    """
    filtered = [r for r in results if r.get("overall_score", 0) >= min_score]
    logger.info(
        f"Filtered to {len(filtered)} results with score >= {min_score} "
        f"(from {len(results)})"
    )
    return filtered


def calculate_statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate statistics from results.

    Args:
        results: List of merged result dictionaries

    Returns:
        Statistics dictionary
    """
    if not results:
        return {
            "total_images": 0,
            "mean_overall_score": 0.0,
            "mean_composition_score": 0.0,
            "mean_lighting_score": 0.0,
            "mean_subject_score": 0.0,
            "mean_technical_score": 0.0,
            "score_distribution": {},
        }

    overall_scores = [r["overall_score"] for r in results]
    composition_scores = [r["composition_score"] for r in results]
    lighting_scores = [r["lighting_score"] for r in results]
    subject_scores = [r["subject_score"] for r in results]
    technical_scores = [r["technical_score"] for r in results]

    # Calculate score distribution (tiers)
    distribution = {
        "excellent (9-10)": len([s for s in overall_scores if s >= 9]),
        "great (8-9)": len([s for s in overall_scores if 8 <= s < 9]),
        "good (7-8)": len([s for s in overall_scores if 7 <= s < 8]),
        "average (6-7)": len([s for s in overall_scores if 6 <= s < 7]),
        "below_average (5-6)": len([s for s in overall_scores if 5 <= s < 6]),
        "poor (0-5)": len([s for s in overall_scores if s < 5]),
    }

    return {
        "total_images": len(results),
        "mean_overall_score": round(sum(overall_scores) / len(overall_scores), 2),
        "mean_composition_score": round(
            sum(composition_scores) / len(composition_scores), 2
        ),
        "mean_lighting_score": round(sum(lighting_scores) / len(lighting_scores), 2),
        "mean_subject_score": round(sum(subject_scores) / len(subject_scores), 2),
        "mean_technical_score": round(
            sum(technical_scores) / len(technical_scores), 2
        ),
        "score_distribution": distribution,
    }


def generate_json_report(
    results: list[dict[str, Any]], output_path: Path
) -> None:
    """Generate JSON report.

    Args:
        results: List of merged result dictionaries
        output_path: Path to output JSON file
    """
    # Sort by overall_score descending
    sorted_results = sorted(
        results, key=lambda x: x.get("overall_score", 0), reverse=True
    )

    # Calculate statistics
    stats = calculate_statistics(sorted_results)

    # Build report
    report = {
        "generated_at": datetime.now().isoformat(),
        "statistics": stats,
        "results": sorted_results,
    }

    # Write to file
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"JSON report written to: {output_path}")


def generate_markdown_report(
    results: list[dict[str, Any]], output_path: Path
) -> None:
    """Generate Markdown report.

    Args:
        results: List of merged result dictionaries
        output_path: Path to output Markdown file
    """
    # Sort by overall_score descending
    sorted_results = sorted(
        results, key=lambda x: x.get("overall_score", 0), reverse=True
    )

    # Calculate statistics
    stats = calculate_statistics(sorted_results)

    # Build markdown
    lines = [
        "# Photo Critic Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Statistics",
        "",
        f"- **Total Images:** {stats['total_images']}",
        f"- **Mean Overall Score:** {stats['mean_overall_score']}/10",
        f"- **Mean Composition Score:** {stats['mean_composition_score']}/10",
        f"- **Mean Lighting Score:** {stats['mean_lighting_score']}/10",
        f"- **Mean Subject Score:** {stats['mean_subject_score']}/10",
        f"- **Mean Technical Score:** {stats['mean_technical_score']}/10",
        "",
        "### Score Distribution",
        "",
    ]

    for tier, count in stats["score_distribution"].items():
        lines.append(f"- **{tier}:** {count}")

    lines.extend(["", "---", "", "## Detailed Results", ""])

    # Group by tier
    tiers = [
        ("Excellent (9-10)", 9, 10),
        ("Great (8-9)", 8, 9),
        ("Good (7-8)", 7, 8),
        ("Average (6-7)", 6, 7),
        ("Below Average (5-6)", 5, 6),
        ("Poor (0-5)", 0, 5),
    ]

    for tier_name, min_score, max_score in tiers:
        tier_results = [
            r
            for r in sorted_results
            if min_score <= r.get("overall_score", 0) < max_score
            or (max_score == 10 and r.get("overall_score", 0) == 10)
        ]

        if not tier_results:
            continue

        lines.extend(["", f"### {tier_name}", ""])

        for result in tier_results:
            lines.extend(
                [
                    f"#### {result['filename']} - **{result['overall_score']}/10**",
                    "",
                    f"**Path:** `{result['path']}`",
                    "",
                    f"**Summary:** {result['summary']}",
                    "",
                    "**Scores:**",
                    f"- Composition: {result['composition_score']}/10 - {result['composition_notes']}",
                    f"- Lighting: {result['lighting_score']}/10 - {result['lighting_notes']}",
                    f"- Subject: {result['subject_score']}/10 - {result['subject_notes']}",
                    f"- Technical: {result['technical_score']}/10 - {result['technical_notes']}",
                    "",
                    "**Strengths:**",
                ]
            )

            for strength in result.get("strengths", []):
                lines.append(f"- {strength}")

            lines.extend(["", "**Improvements:**"])

            for improvement in result.get("improvements", []):
                lines.append(f"- {improvement}")

            lines.append("")

    # Write to file
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    logger.info(f"Markdown report written to: {output_path}")


def generate_report(
    batch_results: list[dict[str, Any]],
    image_metadata: list[dict[str, Any]],
    output_path: Path,
    format: str = "json",
    min_score: float = 0.0,
) -> None:
    """Generate final report.

    Args:
        batch_results: Results from batch API
        image_metadata: Metadata from prepare_batch()
        output_path: Path to output file
        format: Output format ('json', 'markdown', or 'both')
        min_score: Minimum overall_score to include

    Raises:
        ValueError: If format is invalid
    """
    if format not in {"json", "markdown", "both"}:
        raise ValueError(f"Invalid format: {format}")

    # Merge results
    results = merge_results(batch_results, image_metadata)

    # Filter by score
    if min_score > 0:
        results = filter_by_score(results, min_score)

    if not results:
        logger.warning("No results to write")
        return

    # Generate reports
    if format in {"json", "both"}:
        json_path = output_path.with_suffix(".json")
        generate_json_report(results, json_path)

    if format in {"markdown", "both"}:
        md_path = output_path.with_suffix(".md")
        generate_markdown_report(results, md_path)

    logger.info("Report generation complete")
