import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
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


def obter_imagem_principal(soup):
    """
    Tenta obter a imagem principal da receita.
    Estratégia:
      1) <meta property="og:image" ...> (normalmente é a principal)
      2) <meta name="twitter:image" ...>
      3) fallback para <img> dentro de <figure> perto do h1
    """
    # 1) OpenGraph
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"].strip()

    # 2) Twitter card
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"].strip()

    # 3) fallback (mais frágil, mas ajuda se meta falhar)
    h1 = soup.find("h1")
    if h1:
        # procura um figure/img ali “próximo”
        for el in h1.find_all_next(["figure", "img"], limit=60):
            if el.name == "img":
                src = el.get("src") or el.get("data-src") or el.get("data-lazy-src")
                if src:
                    return src.strip()
            elif el.name == "figure":
                img = el.find("img")
                if img:
                    src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if src:
                        return src.strip()

    return None




def iter_texto_da_seccao(soup, heading_text: str):
    """
    Devolve um iterador de strings APENAS da secção que vem a seguir
    a um heading (h2/h3) com o texto 'heading_text', até ao próximo heading.
    """
    heading_text_norm = heading_text.strip().lower()

    h = soup.find(
        lambda tag: isinstance(tag, Tag)
        and tag.name in ("h2", "h3")
        and heading_text_norm in tag.get_text(" ", strip=True).strip().lower()
    )
    if not h:
        return iter(())  # secção não encontrada

    def _gen():
        # Percorre elementos após o heading, até ao próximo h2/h3
        for el in h.next_elements:
            if isinstance(el, Tag) and el.name in ("h2", "h3"):
                break
            # apanha apenas strings limpas
            if isinstance(el, str):
                s = el.strip()
                if s:
                    yield s

    return _gen()


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
    
        # imagem principal (obrigatória)
    imagem = obter_imagem_principal(soup)
    if not imagem:
        print("  -> Ignorada: não tem imagem")
        return None


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

    # critérios (APENAS na secção "Nutrição")
    criterios_encontrados = []
    crit_norm_list = [(crit, normalizar(crit)) for crit in CRITERIOS_POSSIVEIS]

    for text in iter_texto_da_seccao(soup, "Nutrição"):
        t_norm = normalizar(text)
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
        "imagem": imagem,

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
        "imagem", 
    ]

    with open("petitchef_recipes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in todas:
            writer.writerow(r)

    print("Feito: petitchef_recipes.csv")


if __name__ == "__main__":
    main()
