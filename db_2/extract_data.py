import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import unicodedata

BASE = "https://pt.petitchef.com"

CATEGORIAS = {
    "Entrada": "entrada",
    "Prato Principal": "prato-principal",
    "Sobremesa": "sobremesa",
}

TARGETS = {
    "Entrada": 1200,
    "Prato Principal": 1200,
    "Sobremesa": 1200,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (projeto-scraping-petitchef)"
}

CRITERIOS_POSSIVEIS = [
    "Sem glúten",
    "Vegan",
    "Vegetariano",
    "Sem lactose",
    "Sem açúcar",
    "Sem ovo",
]


def normalizar(s: str) -> str:
    """Remove acentos e passa a minúsculas para comparação robusta."""
    if not isinstance(s, str):
        s = str(s)
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def get_recipe_links_limited(slug, max_needed, max_pages=20):
    links = []
    page = 1

    while len(links) < max_needed and page <= max_pages:
        if page == 1:
            url = f"{BASE}/receitas/{slug}"
        else:
            url = f"{BASE}/receitas/{slug}-page-{page}"

        print(f"[LISTA] {url}")
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print("Falhou página:", resp.status_code)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.select("h2 a"):
            href = a.get("href", "")
            if "/receitas/" in href and "fid-" in href:
                if href.startswith("/"):
                    href = BASE + href
                if href not in links:
                    links.append(href)
                    if len(links) >= max_needed:
                        break

        page += 1
        time.sleep(1)

    return links


def extract_text_after_heading(soup, heading_text):
    h = soup.find(lambda tag: tag.name in ("h2", "h3") and heading_text in tag.get_text())
    if not h:
        return None
    el = h.find_next()
    while el and el.name is None:
        el = el.find_next()
    return el


def parse_recipe(url, categoria):
    print(f"[RECEITA] {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"  -> Erro de rede, a ignorar esta receita: {e}")
        return None

    if resp.status_code != 200:
        print("  -> Falhou receita:", resp.status_code)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # título
    title_tag = soup.find("h1")
    titulo = title_tag.get_text(strip=True) if title_tag else ""

    # Ignorar receita se o título contiver "?"
    if "?" in titulo:
        print("  -> Ignorada: título contém '?'")
        return None

    dificuldade = None
    tempo_total = None
    calorias = None

    # calorias (só aceitaremos receitas que tenham Kcal)
    for text in soup.stripped_strings:
        m = re.search(r"(\d+)\s*Kcal", text, re.IGNORECASE)
        if m:
            calorias = f"{m.group(1)} Kcal"
            break

    if calorias is None:
        print("  -> Ignorada: não tem Kcal")
        return None

    # info perto do título (dificuldade, tempo)
    if title_tag:
        texts = []
        for t in title_tag.find_all_next(string=True, limit=40):
            s = t.strip()
            if s:
                texts.append(s)

        for t in texts:
            if any(pal in t for pal in ("Fácil", "Médio", "Difícil")):
                dificuldade = t
                break

        for t in texts:
            if re.search(r"\b\d+\s*(h|min)", t):
                tempo_total = t
                break

    # rating
    rating = None
    for text in soup.stripped_strings:
        m = re.search(r"(\d+(?:[.,]\d+)?)/5", text)
        if m and "votos" in text:
            rating = m.group(1).replace(",", ".")
            break

    # ingredientes
    ingredientes = []
    ing_block = extract_text_after_heading(soup, "Ingredientes")
    if ing_block:
        if ing_block.name in ("ul", "ol"):
            for li in ing_block.find_all("li"):
                ingredientes.append(li.get_text(" ", strip=True))
        else:
            for el in ing_block.find_all_next():
                if el.name in ("h2", "h3"):
                    break
                if el.name in ("li", "p"):
                    ingredientes.append(el.get_text(" ", strip=True))

    if not ingredientes:
        print("  -> Ignorada: não tem ingredientes")
        return None

    # juntar ingredientes num único campo
    ingredientes_str = " | ".join(ingredientes)

    # ⚠️ se tiver ponto e vírgula nos ingredientes, ignorar esta receita
    if ";" in ingredientes_str:
        print("  -> Ignorada: ingredientes contêm ';'")
        return None

    # preparação
    passos = []
    prep_block = extract_text_after_heading(soup, "Preparação")
    if prep_block:
        if prep_block.name in ("ul", "ol"):
            for li in prep_block.find_all("li"):
                passos.append(li.get_text(" ", strip=True))
        else:
            for el in prep_block.find_all_next():
                if el.name in ("h2", "h3"):
                    break
                if el.name in ("li", "p"):
                    passos.append(el.get_text(" ", strip=True))

    passos_str = " | ".join(passos)

    if ";" in passos_str:
        print("  -> Ignorada: passos contêm ';'")
        return None

    # critérios
    criterios_encontrados = []
    crit_norm_list = [(crit, normalizar(crit)) for crit in CRITERIOS_POSSIVEIS]

    for text in soup.stripped_strings:
        t_norm = normalizar(text.strip())
        if not t_norm:
            continue
        for crit_original, crit_norm in crit_norm_list:
            if crit_norm in t_norm and crit_original not in criterios_encontrados:
                criterios_encontrados.append(crit_original)

    return {
        "titulo": titulo,
        "categoria": categoria,
        "dificuldade": dificuldade,
        "tempo_total": tempo_total,
        "calorias": calorias,
        "rating": rating,
        "ingredientes": ingredientes_str,
        "passos": passos_str,
        "criterios": " | ".join(criterios_encontrados),
    }



def main():
    todas = []

    for categoria_nome, slug in CATEGORIAS.items():
        alvo = TARGETS[categoria_nome]
        links = get_recipe_links_limited(slug, max_needed=alvo)
        print(f"{categoria_nome}: {len(links)} links apanhados (alvo={alvo})")

        for url in links:
            dados = parse_recipe(url, categoria_nome)
            if dados:
                todas.append(dados)
            time.sleep(1)

    campos = [
        "titulo",
        "categoria",
        "dificuldade",
        "tempo_total",
        "calorias",
        "rating",
        "ingredientes",
        "passos",
        "criterios",
    ]

    with open("petitchef_recipes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in todas:
            writer.writerow(r)

    print("Feito: petitchef_recipes.csv")


if __name__ == "__main__":
    main()
