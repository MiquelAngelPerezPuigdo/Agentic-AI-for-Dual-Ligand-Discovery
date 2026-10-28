# HTE: one 48-reaction screen

**Start with [the staff procedure](run/README.md).** It explains what to weigh, where to load it and what to do at each App pause.

| Task | File |
|---|---|
| Follow the experiment | **[Staff procedure](run/README.md)** |
| Weigh the chemicals | **[Weighing sheet](run/WEIGHING.md)** |
| Run the OT-2 | **[run_screen.py](run/run_screen.py)** |
| Print the instructions | [Two-page bench sheet](run/bench-sheet.pdf) |
| Calculate yields | [LC analysis instructions](run/ANALYSIS.md) |

Load once and start one program: stocks → dosing → reaction and analytical standards → quenching → LC sampling. Staff handle caps, covers and shaker moves at the prompts. The same labware and tip racks stay loaded.

Everything for the bench is in **`run/`**. Its `images/` and `tables/` subfolders support the linked instructions. No API key is needed.

<details>
<summary>Software and scientific records</summary>

[Build and test instructions](support/README.md) · [How the pairs were selected](support/research/METHOD.md) · [Selection evidence](support/campaigns/hackathon2026/)

Code, inputs, tests and historical material are grouped in `support/`. The root `pyproject.toml` and `uv.lock` install the analysis software using the commands in the LC instructions.

</details>
