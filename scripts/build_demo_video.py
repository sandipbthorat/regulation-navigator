"""Create the narrated, captioned Week 2 walkthrough video."""

from __future__ import annotations

import argparse
import re
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080
BACKGROUND = "#0B1320"
INK = "#E5E7EB"
MUTED = "#A7B0BF"
ACCENT = "#35C6B2"
PANEL = "#111C2C"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


@dataclass(frozen=True)
class Scene:
    slug: str
    heading: str
    caption: str
    narration: str
    screenshot: str | None = None


SCENES = [
    Scene(
        "01-title",
        "Medical Device Software Regulatory Navigator",
        "Week 2 RAG project · LangChain + LangGraph · August 2026",
        "Medical Device Software Regulatory Navigator is a RAG application for regulatory, "
        "quality, and software professionals who need an early, source-grounded screen of one "
        "software function. It covers United States FDA software policy, European MDR Rule 11, "
        "IMDRF software as a medical device, IEC 62304, and ISO 14971. Every result is preliminary "
        "and keeps legal and conformity decisions with qualified reviewers.",
    ),
    Scene(
        "02-input",
        "Start with one software function",
        "21 curated evidence cards · typed facts · unknowns stay visible",
        "The Streamlit surface begins with a single-function description and typed facts. The "
        "bundled knowledge corpus has 21 curated English evidence cards linked to official FDA, "
        "United States statutory, European, IMDRF, IEC, and ISO pages. Authorized PDFs, Markdown, "
        "and text can be added through the ingestion command. Missing facts stay unknown instead "
        "of being silently guessed.",
        "app-input.png",
    ),
    Scene(
        "03-configured",
        "Live robotic-platform example",
        "Explicit product facts drive deterministic LangGraph decision nodes",
        "For the walkthrough, the software runs on a surgical robotic platform, analyzes sensor "
        "information, and alerts a surgeon. I identify it as medical-purpose software that is part "
        "of hardware, uses a clinician, analyzes a signal, and could contribute to death or serious "
        "injury. LangGraph routes the case through scope, clinical decision support, United States, "
        "IMDRF, IEC, European, retrieval, citation, freshness, and release-gate nodes.",
        "app-configured.png",
    ),
    Scene(
        "04-result",
        "Preliminary, source-grounded classification",
        "Atomic claims · inline source IDs · visible human-review boundary",
        "The live result classifies the function as software in a medical device and a likely FDA "
        "device software function. It is not software as a medical device under IMDRF N10 because "
        "it is part of hardware. The preliminary IEC 62304 screen is Class C, and European "
        "classification requires the implementing-rule and driven-device analysis. Each displayed "
        "conclusion is an atomic claim with inline source identifiers, and the disclaimer remains "
        "visible.",
        "app-result-focused.png",
    ),
    Scene(
        "05-sources",
        "Hybrid retrieval and applicable sources",
        "BM25 + Chroma RRF · exact identifier boosts · top-k 8",
        "Retrieval combines BM25 and local Chroma embeddings with reciprocal-rank fusion and exact "
        "identifier boosts. Default top k is eight. Metadata-constrained supplements ensure every "
        "decision-critical source family is present, while raw retrieval quality is evaluated "
        "separately. The source table distinguishes statutes, binding regulations, final guidance, "
        "draft guidance, international frameworks, and licensed standards.",
        "app-sources.png",
    ),
    Scene(
        "06-quality",
        "Evidence quality is visible",
        "100% claim grounding · current corpus · measured live latency",
        "The quality tab makes the evidence contract visible. This run has ten validated citations, "
        "one hundred percent applicability-source coverage, one hundred percent claim-level "
        "faithfulness, and a current source review under the thirty-day freshness service level. "
        "The app refuses unsupported requests or stale evidence, and warns that standards work "
        "requires licensed sources.",
        "app-quality.png",
    ),
    Scene(
        "07-evidence",
        "Inspect the evidence behind a claim",
        "Stable IDs · lifecycle status · concise evidence · official link",
        "Each evidence card shows a stable citation identifier, document, section, authority, "
        "status, date, concise supporting text, and an official link. The IEC card deliberately "
        "provides only scope-level evidence and directs the user to a licensed copy, preventing the "
        "system from reconstructing copyrighted standard text.",
        "app-evidence-expanded.png",
    ),
    Scene(
        "08-close",
        "Measured, reproducible, and ready to submit",
        "20 classification cases · 15 retrieval/refusal cases · complete artifact package",
        "The checked-in evaluation includes 20 classification cases and 15 retrieval and refusal "
        "cases. The current development run measured one hundred percent claim-level "
        "faithfulness, one hundred percent Recall at five, zero point nine five one normalized "
        "discounted cumulative gain at five, and zero point zero zero five second p ninety-five "
        "assessment latency. Codex helped scaffold the project, inspect the handout, refine the "
        "LangGraph workflow, run tests, and generate submission artifacts. The package includes the "
        "app, corpus, tests, evaluation report, project document, and this walkthrough.",
    ),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD_FONT if bold else FONT, size)


def wrapped_lines(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def base_canvas() -> Image.Image:
    return Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)


def draw_brand(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((96, 72, 119, 95), radius=5, fill=ACCENT)
    draw.text((136, 66), "REGULATION NAVIGATOR", font=font(24, True), fill=ACCENT)
    draw.text((1640, 68), "WEEK 2 · 2026", font=font(20), fill=MUTED)


def create_title_frame(scene: Scene, output: Path, closing: bool = False) -> None:
    canvas = base_canvas()
    draw = ImageDraw.Draw(canvas)
    draw_brand(draw)
    y = 285 if not closing else 245
    draw.text((160, y), wrapped_lines(scene.heading, 34), font=font(66, True), fill=INK, spacing=12)
    draw.rounded_rectangle((160, y + 205, 1660, y + 210), radius=2, fill=ACCENT)
    draw.text(
        (160, y + 250), wrapped_lines(scene.caption, 70), font=font(34), fill=MUTED, spacing=10
    )
    if closing:
        metrics = [
            ("100%", "claim faithfulness"),
            ("100%", "Recall@5"),
            ("0.951", "nDCG@5"),
            ("0.005s", "p95 latency"),
        ]
        x = 160
        for value, label in metrics:
            draw.rounded_rectangle((x, 690, x + 360, 865), radius=18, fill=PANEL)
            draw.text((x + 28, 720), value, font=font(42, True), fill=ACCENT)
            draw.text((x + 28, 790), label, font=font(24), fill=MUTED)
            x += 390
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=95)


def create_screenshot_frame(scene: Scene, source: Path, output: Path) -> None:
    screenshot = Image.open(source).convert("RGB")
    screenshot = screenshot.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    canvas = screenshot.copy()
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, WIDTH, 126), fill=(11, 19, 32, 238))
    draw.rectangle((0, 842, WIDTH, HEIGHT), fill=(11, 19, 32, 244))
    draw.rounded_rectangle((72, 48, 95, 71), radius=5, fill=ACCENT)
    draw.text((112, 38), scene.heading, font=font(34, True), fill=INK)
    draw.text((112, 895), wrapped_lines(scene.caption, 78), font=font(34), fill=INK, spacing=10)
    draw.text(
        (112, 1008),
        "PRELIMINARY EDUCATIONAL SCREENING · NOT LEGAL ADVICE",
        font=font(20),
        fill=MUTED,
    )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=95)


def synthesize_audio(scene: Scene, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        audit = subprocess.run(
            ["/usr/bin/afinfo", str(output)], capture_output=True, text=True, check=False
        )
        match = re.search(r"estimated duration:\s+([0-9.]+)", audit.stdout)
        if match and float(match.group(1)) > 0:
            return
        output.unlink()
    subprocess.run(
        ["/usr/bin/say", "-r", "180", "-o", str(output), scene.narration],
        check=True,
        timeout=90,
    )


def build_video(frames_dir: Path, output: Path, build_dir: Path) -> None:
    build_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    audio_clips = []
    for index, scene in enumerate(SCENES):
        image_path = build_dir / f"{scene.slug}.jpg"
        audio_path = build_dir / f"{scene.slug}.aiff"
        if scene.screenshot:
            create_screenshot_frame(scene, frames_dir / scene.screenshot, image_path)
        else:
            create_title_frame(scene, image_path, closing=index == len(SCENES) - 1)
        synthesize_audio(scene, audio_path)
        audio = AudioFileClip(str(audio_path))
        audio_clips.append(audio)
        clip = ImageClip(str(image_path)).with_duration(audio.duration + 0.45).with_audio(audio)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")
    if final.duration > 300:
        raise RuntimeError(f"Video is {final.duration:.1f}s; it must not exceed 300 seconds")
    output.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(output),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="4500k",
        threads=4,
        logger="bar",
    )
    final.close()
    for clip in clips:
        clip.close()
    for audio in audio_clips:
        audio.close()
    print(f"Created {output} ({final.duration:.1f} seconds)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=Path, default=Path("output/video/frames"))
    parser.add_argument(
        "--output", type=Path, default=Path("output/video/Regulation_Navigator_Demo.mp4")
    )
    parser.add_argument("--build-dir", type=Path, default=Path("tmp/video_build"))
    args = parser.parse_args()
    build_video(args.frames, args.output, args.build_dir)


if __name__ == "__main__":
    main()
