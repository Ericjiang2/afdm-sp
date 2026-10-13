import json
import pathlib


HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "claim_scope_matrix.json"
OUT_PATH = HERE / "TABLE_claim_scope.tex"


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
    "\\caption{Claim and scope matrix used to keep the paper aligned with the validated evidence.}",
    "\\label{tab:claim_scope}",
    "\\begin{tabular}{p{4.2cm}p{5.3cm}p{4.5cm}}",
    "\\toprule",
    "Claim & Key evidence & Scope or limitation \\\\",
    "\\midrule"
]

for row in data["rows"]:
    lines.append(
        f'{latex_escape(row["claim"])} & {latex_escape(row["evidence"])} & {latex_escape(row["scope"])} \\\\'
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
