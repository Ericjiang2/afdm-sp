"""Summarize fresh original qualification; never infer receiver superiority."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path)
    args = parser.parse_args()
    base = args.qualification
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for directory in sorted((base / "commands").iterdir()):
        if not directory.is_dir():
            continue
        exit_code = int((directory / "exit_code.txt").read_text())
        if exit_code != 0:
            raise ValueError(f"Qualification failed: {directory.name}: {exit_code}")
        metrics = {}
        for line in (directory / "time.txt").read_text().splitlines():
            if "Maximum resident set size (kbytes):" in line:
                metrics["process_peak_rss_kib"] = int(line.rsplit(":", 1)[1])
            if "Elapsed (wall clock) time" in line:
                parts = line.split("): ", 1)[1].split(":")
                seconds = 0.0
                for part in parts:
                    seconds = seconds * 60 + float(part)
                metrics["process_wall_seconds"] = seconds
        if len(metrics) != 2:
            raise ValueError(f"Incomplete process metrics: {directory}")
        rows.append(dict(command=directory.name, exit_code=exit_code, **metrics))
    if len(rows) != 9:
        raise ValueError("Expected eight original checks and saved-decision recount")
    with (out / "qualification_commands.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    source = args.benchmark or base / "fresh_outputs" / "kernel_benchmark.json"
    fixtures = json.loads(source.read_text())
    kernel_rows = []
    for fixture in fixtures:
        for implementation in ("fast", "full", "cached_dense"):
            values = fixture["seconds"][implementation]
            if len(values) != 7 or any(value <= 0 for value in values):
                raise ValueError("Expected seven positive interleaved timings")
            kernel_rows.append(dict(
                N=fixture["N"], P=fixture["P"], implementation=implementation,
                repetitions=len(values), median_ms=1000 * fixture["median"][implementation],
                maximum_output_discrepancy=max(fixture["errors"]),
            ))
    with (out / "same_output_kernel.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(kernel_rows[0]))
        writer.writeheader()
        writer.writerows(kernel_rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(8.2, 4.1), layout="constrained")
    positions = np.arange(len(fixtures))
    labels = ("Matrix-free", "Fresh dense + outputs", "Cached dense outputs")
    colors = ("#0072B2", "#D55E00", "#009E73")
    for j, implementation in enumerate(("fast", "full", "cached_dense")):
        offset = (j - 1) * .24
        medians = [1000 * f["median"][implementation] for f in fixtures]
        ax.bar(positions + offset, medians, width=.22, color=colors[j], label=labels[j])
        for i, fixture in enumerate(fixtures):
            values = 1000 * np.asarray(fixture["seconds"][implementation])
            ax.scatter(np.full(len(values), positions[i] + offset), values,
                       marker="_", color="black", s=35, linewidths=.7)
    ax.set_yscale("log")
    ax.set_ylabel("Same-output kernel time (ms, logarithmic scale)")
    ax.set_xticks(positions, [f"N={f['N']}, P={f['P']}" for f in fixtures])
    ax.legend(frameon=False, loc="upper left")
    ax.set_ylim(.08, 200)
    for suffix in ("pdf", "svg", "png"):
        fig.savefig(out / f"same_output_kernel.{suffix}", dpi=180)
    plt.close(fig)
    caption = (
        "Fresh deinlab original-source qualification. Bars: medians; black marks: "
        "seven interleaved repetitions on each fixed fixture. All implementations "
        "compute matching energies, masks, coefficients, weak row variance and full "
        "mean. Cached dense outputs are faster on these fixtures; matrix-free avoids "
        "fresh dense construction. This is a moment-kernel benchmark, not complete "
        "receiver latency, communication performance, or population uncertainty.\n"
    )
    (out / "same_output_kernel_caption.md").write_text(caption)
    inputs = [source, *sorted((base / "commands").glob("*/*.txt"))]
    manifest = dict(
        scope="original qualification only; zero new driver development/confirmation frames",
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs={str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        commands=rows,
        limitations="Process RSS includes interpreter/setup and all cases in a test; not per-arm online memory.",
    )
    (out / "report_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"commands_passed": len(rows), "fixtures": len(fixtures),
                      "maximum_kernel_error": max(r["maximum_output_discrepancy"] for r in kernel_rows)}))


if __name__ == "__main__":
    main()
