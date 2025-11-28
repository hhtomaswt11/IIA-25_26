

# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa-pro/concepts/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []
import pandas as pd
import os
import unicodedata
import re
import google.generativeai as genai
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


RECIPES_FILE = os.path.join(os.path.dirname(__file__), "..", "data_source", "recipes.csv")


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    HAS_GEMINI = True
else:
    HAS_GEMINI = False
    print("⚠️ AVISO: Chave Gemini não configurada. A geração automática não funcionará.")


def _normalize_str(s: str) -> str:
    """Remove acentos e coloca em minúsculas para comparação segura."""
    s = (s or "").lower().strip()
    return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')

def _parse_time_to_minutes(s: str):
    """Converte '1 h 30 m', '45 min', etc. para minutos (int)."""
    s = (s or "").lower().strip()
    if not s:
        return None
    s = s.replace('.', ' ').replace(',', ' ').replace('\u00a0', ' ')
    
    h_match = re.search(r"(\d+)\s*(?:h|hora|horas)", s)
    m_match = re.search(r"(\d+)\s*(?:min|m|minuto|minutos)", s)
    
    if not h_match:
        h_match = re.search(r"(\d+)h(?![a-z])", s) # ex: 1h
        
    if h_match:
        hours = int(h_match.group(1))
        mins = int(m_match.group(1)) if m_match else 0
        return hours * 60 + mins
    
    if m_match:
        return int(m_match.group(1))
        
    n = re.search(r"(\d+)", s)
    return int(n.group(1)) if n else None

def _parse_calories(s: str):
    """Extrai valor numérico das calorias."""
    s = (s or "").lower()
    n = re.search(r"(\d+)", s)
    return int(n.group(1)) if n else None

def _load_recipes(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep=';', encoding='utf-8', dtype=str)
        df = df.fillna("")

        df.columns = [c.strip() for c in df.columns]

        df['categoria_norm'] = df.get('categoria', '').apply(_normalize_str)
        df['dificuldade_norm'] = df.get('dificuldade', '').apply(_normalize_str)
        df['criterios_norm'] = df.get('criterios', '').apply(_normalize_str)
        df['ingredientes_search'] = df.get('ingredientes', '').apply(_normalize_str)

        # Colunas numéricas
        df['rating_num'] = pd.to_numeric(df.get('rating', ''), errors='coerce').fillna(0)
        df['tempo_minutes'] = df.get('tempo_total', '').astype(str).apply(_parse_time_to_minutes)
        df['calorias_num'] = df.get('calorias', '').astype(str).apply(_parse_calories)

        # print(f"--- Dataset Carregado: {len(df)} receitas ---")
        return df
    except FileNotFoundError:
        print(f"!!! ERRO: Ficheiro não encontrado: {path}")
        return pd.DataFrame()

RECIPE_DATASET = _load_recipes(RECIPES_FILE)


def generate_recipe_with_gemini(category, difficulty, time_desc, restrictions, avoid, caloric_desc):
    """
    Chama o Google Gemini para criar uma receita.
    Recebe 'time_desc' e 'caloric_desc' já traduzidos para linguagem natural.
    """
    if not HAS_GEMINI:
        return None

    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""
    Atua como um chef de cozinha profissional.
    O utilizador pediu uma receita que não existe na minha base de dados.
    Cria uma receita AGORA que cumpra estritamente estes requisitos:

    - Tipo de Prato: {category if category else "Qualquer"}
    - Dificuldade: {difficulty if difficulty else "Qualquer"}
    - Tempo de Preparação: {time_desc if time_desc else "Qualquer"}
    - Calorias: {caloric_desc if caloric_desc else "Sem restrição específica"}
    - Restrições Alimentares: {restrictions if restrictions else "Nenhuma"}
    - Ingredientes a evitar: {avoid if avoid else "Nenhum"}

    A resposta deve ser em Português de Portugal.
    Usa este formato simples:
    
    TITULO: [Nome Criativo]
    INFO: [Tempo exato] | [Dificuldade] | [Calorias estimadas]
    
    INGREDIENTES:
    - [Item 1]
    - [Item 2]
    
    PREPARAÇÃO:
    1. [Passo 1]
    2. [Passo 2]
    
    (Nota: Receita gerada por IA baseada nos teus gostos)
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro Gemini: {e}")
        return None


# class ActionSearchRecipesByIngredients(Action):
#     def name(self) -> Text:
#         return "action_search_recipes_by_ingredients"

#     def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],
#     ) -> List[Dict[Text, Any]]:

#         # Obter ingredientes dos slots
#         base_ing = tracker.get_slot("available_ingredients") or ""
#         extra_ing = tracker.get_slot("additional_ingredients") or ""

#         if RECIPE_DATASET.empty:
#             dispatcher.utter_message(text="Erro: Base de dados indisponível.")
#             return []

#         # Combinar todos os ingredientes
#         all_ingredients = f"{base_ing}, {extra_ing}".strip(", ")

#         if not all_ingredients:
#             dispatcher.utter_message(text="Não percebi que ingredientes tens. Podes repetir?")
#             return []

#         # Separar ingredientes (aceita vírgulas, "e", pipes, ponto e vírgula)
#         raw_tokens = re.split(r'[,;|]|\s+e\s+', all_ingredients)
#         raw_tokens = [t.strip() for t in raw_tokens if t.strip()]
        
#         # Normalizar: remover acentos, minúsculas, eliminar palavras muito curtas
#         tokens = []
#         for t in raw_tokens:
#             normalized = _normalize_str(t)
#             # Ignorar tokens muito pequenos (ex: "de", "a", "o")
#             if len(normalized) > 2:
#                 tokens.append(normalized)

#         if not tokens:
#             dispatcher.utter_message(text="Não encontrei ingredientes válidos na tua mensagem.")
#             return []

#         print(f"🔍 Ingredientes RAW: {raw_tokens}")
#         print(f"🔍 Ingredientes NORMALIZADOS: {tokens}")

#         df = RECIPE_DATASET.copy()

#         # Contar quantos ingredientes do utilizador aparecem em cada receita
#         def count_matches(ing_str: str) -> int:
#             """
#             Conta quantos ingredientes (tokens) do utilizador aparecem 
#             na string de ingredientes da receita (já normalizada).
#             """
#             if not ing_str:
#                 return 0
            
#             count = 0
#             for token in tokens:
#                 # Procura palavra completa ou como parte de palavra composta
#                 # Ex: "batata" encontra em "batatas", "batata doce", etc.
#                 if token in ing_str:
#                     count += 1
#             return count

#         df["match_count"] = df["ingredientes_search"].apply(count_matches)

#         # FILTRAR: só receitas com PELO MENOS 1 ingrediente do utilizador
#         df = df[df["match_count"] > 0]

#         print(f"🔍 Receitas encontradas: {len(df)} de {len(RECIPE_DATASET)}")

#         if df.empty:
#             # Nenhuma receita encontrada
#             msg = f"Não encontrei receitas com {', '.join(raw_tokens)}."
            
#             if HAS_GEMINI:
#                 dispatcher.utter_message(
#                     text=f"{msg} Mas vou pedir ao Chef AI para criar uma receita exclusiva com esses ingredientes! 👨‍🍳✨"
#                 )
                
#                 # Gerar receita com Gemini
#                 recipe_ai = generate_recipe_with_gemini(
#                     category="Qualquer",
#                     difficulty="Qualquer",
#                     time_desc="Qualquer",
#                     restrictions="Nenhuma",
#                     avoid="",
#                     caloric_desc=f"Usando os ingredientes: {all_ingredients}"
#                 )
                
#                 if recipe_ai:
#                     dispatcher.utter_message(text=recipe_ai)
#                 else:
#                     dispatcher.utter_message(text="Erro ao gerar receita automática.")
#             else:
#                 dispatcher.utter_message(text=f"{msg} Tenta com outros ingredientes ou ativa o Gemini.")
            
#             return [SlotSet("search_results", [])]

#         # Ordenar: mais matches primeiro, depois melhor rating
#         df = df.sort_values(by=["match_count", "rating_num"], ascending=[False, False])

#         # Top 8 receitas
#         top = df.head(8)
#         num_total = len(df)

#         lines = []
#         for i, (idx, row) in enumerate(top.iterrows(), start=1):
#             titulo = row.get("titulo", "")
#             dif = row.get("dificuldade", "")
#             tempo = row.get("tempo_total", "")
#             cal = row.get("calorias", "")
#             matches = int(row.get("match_count", 0))
            
#             # Mostrar quantos ingredientes do utilizador a receita usa
#             ingredient_plural = "ingrediente" if matches == 1 else "ingredientes"
#             lines.append(
#                 f"{i}. **{titulo}** ({dif}, {tempo}, {cal}) - Usa {matches} {ingredient_plural}"
#             )

#         text_out = "\n".join(lines)
        
#         # Mensagem final
#         recipe_plural = "receita" if num_total == 1 else "receitas"
#         dispatcher.utter_message(
#             text=f"Ótima combinação! 🥘 Encontrei {num_total} {recipe_plural} com esses ingredientes:\n\n{text_out}\n\nQueres ver alguma em particular?"
#         )

#         return [SlotSet("search_results", top.to_dict("records"))]



class ActionSearchRecipesByIngredients(Action):
    def name(self) -> Text:
        return "action_search_recipes_by_ingredients"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Obter ingredientes dos slots
        base_ing = tracker.get_slot("available_ingredients") or ""
        extra_ing = tracker.get_slot("additional_ingredients") or ""

        if RECIPE_DATASET.empty:
            dispatcher.utter_message(text="Erro: Base de dados indisponível.")
            return []

        # Combinar todos os ingredientes
        all_ingredients = f"{base_ing}, {extra_ing}".strip(", ")

        if not all_ingredients:
            dispatcher.utter_message(text="Não percebi que ingredientes tens. Podes repetir?")
            return []

        # Separar ingredientes (aceita vírgulas, "e", pipes, ponto e vírgula)
        raw_tokens = re.split(r'[,;|]|\s+e\s+', all_ingredients)
        raw_tokens = [t.strip() for t in raw_tokens if t.strip()]
        
        # Normalizar: remover acentos, minúsculas, eliminar palavras muito curtas
        tokens = []
        for t in raw_tokens:
            normalized = _normalize_str(t)
            # Ignorar tokens muito pequenos (ex: "de", "a", "o")
            if len(normalized) > 2:
                tokens.append(normalized)

        if not tokens:
            dispatcher.utter_message(text="Não encontrei ingredientes válidos na tua mensagem.")
            return []

        
        # DEBUG (NAO APAGAR)
        # print(f"🔍 Ingredientes RAW: {raw_tokens}")
        # print(f"🔍 Ingredientes NORMALIZADOS: {tokens}")
        # print(f"🔍 Total de ingredientes obrigatórios: {len(tokens)}")

        df = RECIPE_DATASET.copy()
        num_required = len(tokens)  # <--- NÚMERO DE INGREDIENTES OBRIGATÓRIOS

        # Contar quantos ingredientes do utilizador aparecem em cada receita
        def count_matches(ing_str: str) -> int:
            """
            Conta quantos ingredientes (tokens) do utilizador aparecem 
            na string de ingredientes da receita (já normalizada).
            """
            if not ing_str:
                return 0
            
            count = 0
            for token in tokens:
                if token in ing_str:
                    count += 1
            return count

        df["match_count"] = df["ingredientes_search"].apply(count_matches)

        df = df[df["match_count"] == num_required] 
        
      # DEBUG 
      #  print(f"🔍 Receitas com TODOS os ingredientes: {len(df)} de {len(RECIPE_DATASET)}")

        if df.empty:
            # Nenhuma receita encontrada COM TODOS os ingredientes
            msg = f"Não encontrei receitas que usem **todos** estes ingredientes: {', '.join(raw_tokens)}."
            
            if HAS_GEMINI:
                dispatcher.utter_message(
                    text=f"{msg} Mas vou pedir ao Chef AI para criar uma receita exclusiva com esses ingredientes! 👨‍🍳✨"
                )
                
                # Gerar receita com Gemini
                recipe_ai = generate_recipe_with_gemini(
                    category="Qualquer",
                    difficulty="Qualquer",
                    time_desc="Qualquer",
                    restrictions="Nenhuma",
                    avoid="",
                    caloric_desc=f"Usando os ingredientes: {all_ingredients}"
                )
                
                if recipe_ai:
                    dispatcher.utter_message(text=recipe_ai)
                else:
                    dispatcher.utter_message(text="Erro ao gerar receita automática.")
            else:
                dispatcher.utter_message(text=f"{msg} Tenta com menos ingredientes ou ingredientes diferentes.")
            
            return [SlotSet("search_results", [])]

        # Ordenar por melhor rating (já têm todos os ingredientes)
        df = df.sort_values(by="rating_num", ascending=False)

        # Top 8 receitas
        top = df.head(8)
        num_total = len(df)

        lines = []
        for i, (idx, row) in enumerate(top.iterrows(), start=1):
            titulo = row.get("titulo", "")
            dif = row.get("dificuldade", "")
            tempo = row.get("tempo_total", "")
            cal = row.get("calorias", "")
            
            lines.append(
                f"{i}. **{titulo}** ({dif}, {tempo}, {cal})"
            )

        text_out = "\n".join(lines)
        
        # Mensagem final
        recipe_plural = "receita" if num_total == 1 else "receitas"
        dispatcher.utter_message(
            text=f"Perfeito! 🥘 Encontrei {num_total} {recipe_plural} que usam **todos** esses ingredientes:\n\n{text_out}" # \n\nQueres ver alguma em particular?"
        )

        return [SlotSet("search_results", top.to_dict("records"))]