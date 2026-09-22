import json

with open("sharpbet-v12-halftime-goals-audit.ipynb") as f:
    nb = json.load(f)

global_scope = {}
for i, cell in enumerate(nb["cells"]):
    if cell["cell_type"] == "code":
        print(f"\n--- EXECUTING CELL {i} ---")
        code = "".join(cell["source"])
        exec(code, global_scope)

print("\n🎉 DRY RUN COMPLETE! Checking gate_verdicts.json...")
with open("gate_verdicts.json") as f:
    print(f.read())
