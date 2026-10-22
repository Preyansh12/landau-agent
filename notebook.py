import marimo

__generated_with = "0.0.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import subprocess, json, os, sys
    mo.md("# LandauAgent: results notebook\nScorecard regenerated from the result files, and one live run through the same tools the agent uses.")
    return json, mo, os, subprocess, sys


@app.cell
def _(mo, os, subprocess, sys):
    table = subprocess.run([sys.executable, "make_benchmark_table.py"], capture_output=True, text=True,
                           encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}).stdout
    mo.md("## Scorecard (generated, not typed)\n\n" + table)
    return (table,)


@app.cell
def _(mo):
    mo.vstack([mo.md("## Ca₃Ti₂O₇ phase ladder"), mo.image(src="results/phase_ladder_Ca3Ti2O7.png", width=700)])
    return


@app.cell
def _(mo):
    material = mo.ui.dropdown(["SrTiO3", "CaTiO3", "BaTiO3", "PbTiO3", "LaAlO3"], value="SrTiO3", label="Cubic perovskite")
    run = mo.ui.run_button(label="Find instabilities with MACE")
    mo.hstack([material, run])
    return material, run


@app.cell
def _(material, mo, run):
    mo.stop(not run.value, mo.md("*Press the button to compute MACE force constants and the irrep curvatures (a few minutes on a laptop; cached afterwards).*"))
    from landau_agent.tools import Session
    s = Session()
    s.fc_cache = f"results/{material.value}_force_constants.npy"
    s.load_parent(material.value)
    s.set_supercell([[2, 0, 0], [0, 2, 0], [0, 0, 2]])
    modes = s.find_instabilities()["modes"]
    rows = [m for m in modes if m["unstable"]]
    mo.md("### Unstable irreps at the MACE-relaxed lattice\n\n| irrep | standard label | curvature (eV/Å²) | polar |\n|---|---|---|---|\n"
          + "\n".join(f"| {m['name']} | {m.get('standard_label') or '—'} | {m['curvature_eV_A2']} | {m['polar']} |" for m in rows))
    return


if __name__ == "__main__":
    app.run()
