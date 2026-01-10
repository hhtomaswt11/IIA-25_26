import csv

input_file = "recipes_old.csv"
output_file = "recipes.csv"

with open(input_file, "r", encoding="utf-8") as f_in, \
     open(output_file, "w", encoding="utf-8", newline="") as f_out:

    reader = csv.reader(f_in, delimiter=";")
    writer = csv.writer(f_out, delimiter=";")

    # Ler cabeçalho original
    header = next(reader)

    # Escrever novo cabeçalho com 'id' no início
    writer.writerow(["id"] + header)

    # Escrever linhas com ID crescente
    for idx, row in enumerate(reader, start=1):
        writer.writerow([idx] + row)

print("CSV criado com sucesso:", output_file)
