import csv

input_file = "petitchef_recipes.csv"  # o teu ficheiro original
output_file = "recipes.csv"  # ficheiro limpo

with open(input_file, "r", encoding="utf-8", newline="") as fin, \
     open(output_file, "w", encoding="utf-8", newline="") as fout:

    reader = csv.DictReader(fin)

    fieldnames = reader.fieldnames

    # escreve CSV novo com ; e sem aspas
    writer = csv.DictWriter(
        fout,
        fieldnames=fieldnames,
        delimiter=';',          # <<< agora usa ponto e vírgula
        quoting=csv.QUOTE_NONE, # <<< não mete aspas
        escapechar='\\'         # caso algum campo tenha ; no futuro
    )

    writer.writeheader()

    for row in reader:
        # limpar aspas NOS CAMPOS titulo e passos
        for col in ("titulo", "passos"):
            if row.get(col) is not None:
                row[col] = row[col].replace('"', "").replace("'", "")

        writer.writerow(row)

print("Feito! Ficheiro gerado:", output_file)
