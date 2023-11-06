import os, jsonc

game = input("Enter game name: ")
if f"{game}.jsonc" not in os.listdir("."):
    print("Game not found, try entering it again")
    exit()

with open(f"{game}.jsonc", encoding="utf-8") as f:
    gens = jsonc.load(f)

report = {}

for genName, gen in gens.items():
    report[genName]: dict = {}
    if "languages" not in gen: continue
    for lang in gen["languages"]:
        report[genName][lang] = []
        for goal in gen["goals"]:
            if "translations" not in goal.keys() or lang not in goal["translations"]:
                report[genName][lang].append(goal["name"])

with open(f"_report_{game}.json", "w", encoding="utf-8") as f:
    jsonc.dump(report, f, indent=4)