"""
build_corrector_ber_snr_json.py

Build the paper display JSON for the frozen-corrector BER-vs-SNR figure from a
refresh/evidence summary JSON, so the plotting data does not need to be edited
by hand.
"""

from __future__ import annotations

import argparse
import json
import pathlib


def _parse_args() -> argparse.Namespace:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build figures/data/corrector_ber_snr.json from a summary JSON.")
    parser.add_argument("--summary-json", type=str, required=True)
    parser.add_argument(
        "--out-json",
        type=str,
        default=str(here / "data" / "corrector_ber_snr.json"),
    )
    return parser.parse_args()


def _read_combined_regime(payload: dict, regime_name: str) -> dict:
    regime = payload["regimes"][regime_name]
    if "combined" in regime:
        return regime["combined"]
    return regime


def _to_display_regime(summary_row: dict) -> dict:
    items = sorted((int(snr), row) for snr, row in summary_row["per_snr"].items())
    return {
        "snr_db": [snr for snr, _ in items],
        "CurrentJoint": [row["baseline_ber_mean"] for _, row in items],
        "FrozenCorrector": [row["corrected_ber_mean"] for _, row in items],
    }


def main() -> None:
    args = _parse_args()
    summary_path = pathlib.Path(args.summary_json)
    out_path = pathlib.Path(args.out_json)

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    nominal = _read_combined_regime(payload, "nominal")
    ppaths15 = _read_combined_regime(payload, "failure_ppaths15")

    display = {
        "nominal": _to_display_regime(nominal),
        "failure_ppaths15": _to_display_regime(ppaths15),
        "note": "BER gain = BER(CurrentJoint) - BER(FrozenCorrector). Positive = improvement.",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(display, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
