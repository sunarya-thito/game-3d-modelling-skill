#!/usr/bin/env python3
"""Assemble numbered PNG frames into a palette-optimized looping GIF."""

from pathlib import Path
import argparse
import shutil
import subprocess
import tempfile


def encode_with_ffmpeg(paths, output, duration_ms):
    executable = shutil.which("ffmpeg")
    if executable is None:
        return False
    frame_rate = 1000.0 / duration_ms
    with tempfile.TemporaryDirectory(prefix="showcase-gif-") as temporary:
        temporary = Path(temporary)
        for index, source in enumerate(paths):
            shutil.copyfile(source, temporary / f"{index:08d}.png")
        source_pattern = str(temporary / "%08d.png")
        palette = temporary / "palette.png"
        common = [executable, "-y", "-hide_banner", "-loglevel", "error"]
        subprocess.run(
            common
            + [
                "-framerate",
                f"{frame_rate:.9f}",
                "-i",
                source_pattern,
                "-vf",
                "palettegen=max_colors=256:stats_mode=full",
                str(palette),
            ],
            check=True,
        )
        subprocess.run(
            common
            + [
                "-framerate",
                f"{frame_rate:.9f}",
                "-i",
                source_pattern,
                "-i",
                str(palette),
                "-lavfi",
                "paletteuse=dither=sierra2_4a:diff_mode=rectangle",
                "-loop",
                "0",
                str(output),
            ],
            check=True,
        )
    return True


def encode_with_pillow(paths, output, duration_ms):
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit(
            "Neither ffmpeg nor Pillow is available. Install one encoder first."
        ) from exc
    images = [Image.open(path).convert("RGB") for path in paths]
    sample_width = max(64, images[0].width // 4)
    sample_height = max(64, images[0].height // 4)
    columns = 4
    rows = (len(images) + columns - 1) // columns
    contact = Image.new("RGB", (sample_width * columns, sample_height * rows))
    for index, frame in enumerate(images):
        sample = frame.resize((sample_width, sample_height), Image.Resampling.LANCZOS)
        contact.paste(sample, ((index % columns) * sample_width, (index // columns) * sample_height))
    palette = contact.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    converted = [
        frame.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)
        for frame in images
    ]
    converted[0].save(
        output,
        save_all=True,
        append_images=converted[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration-ms", type=int, default=70)
    parser.add_argument("--pattern", default="*.png")
    parser.add_argument(
        "--encoder",
        choices=("auto", "ffmpeg", "pillow"),
        default="auto",
        help="ffmpeg gives the cleanest gradients; auto falls back to Pillow",
    )
    args = parser.parse_args()
    if args.duration_ms <= 0:
        raise SystemExit("--duration-ms must be positive")
    paths = sorted(args.frames.glob(args.pattern))
    if not paths:
        raise SystemExit(f"no frames matching {args.pattern!r} in {args.frames}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    used_ffmpeg = args.encoder != "pillow" and encode_with_ffmpeg(
        paths, args.output, args.duration_ms
    )
    if args.encoder == "ffmpeg" and not used_ffmpeg:
        raise SystemExit("ffmpeg was requested but is not available on PATH")
    if not used_ffmpeg:
        encode_with_pillow(paths, args.output, args.duration_ms)
    encoder = "ffmpeg" if used_ffmpeg else "Pillow"
    print(f"wrote {args.output} from {len(paths)} frames with {encoder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
