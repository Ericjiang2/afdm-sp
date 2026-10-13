import json
import pathlib


HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "method_comparison_summary.json"
OUT_PATH = HERE / "TABLE_method_comparison.tex"


def latex_escape(text):
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
    )


with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

lines = [
    "\\begin{table*}[t]",
    "\\centering",
    "\\caption{Method evolution from failed residual correction to the final frozen direct-bit corrector.}",
    "\\label{tab:method_evolution}",
    "\\begin{tabular}{p{2.6cm}p{2.8cm}p{3.2cm}p{6.4cm}}",
    "\\toprule",
    "Method & Family & Test protocol & Headline outcome \\\\",
    "\\midrule"
]

for row in data["methods"]:
    lines.append(
        f'{latex_escape(row["method"])} & {latex_escape(row["family"])} & {latex_escape(row["test_protocol"])} & {latex_escape(row["headline_result"])} \\\\'
    )

lines.extend(
    [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
        ""
    ]
)

OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f"Saved: {OUT_PATH}")
