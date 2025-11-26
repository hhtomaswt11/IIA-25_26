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

        print(f"--- Dataset Carregado: {len(df)} receitas ---")
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


class ActionSearchRecipes(Action):
    def name(self) -> Text:
        return "action_search_recipes"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # 1. Obter Slots
        category = tracker.get_slot("recipe_category") or ""
        time = tracker.get_slot("cook_time") or ""
        difficulty = tracker.get_slot("difficulty") or ""
        restrictions = tracker.get_slot("dietary_restrictions") or ""
        avoid = tracker.get_slot("avoid_ingredients") or ""
        caloric = tracker.get_slot("caloric_preference") or ""


        df = RECIPE_DATASET.copy()
        if df.empty:
            dispatcher.utter_message(text="Erro: Base de dados indisponível.")
            return []

        # Normalizar strings
        cat_lower = _normalize_str(category)
        dif_lower = _normalize_str(difficulty)
        time_lower = time.lower().strip()
        cal_lower = _normalize_str(caloric)

        # FILTRO 1: CATEGORIA
        cat_map = {
            'entrada': ['entrada'],
            'principal': ['prato principal', 'principal'],
            'sobremesa': ['sobremesa'],
        }
        target_cat = None
        if 'entrada' in cat_lower: target_cat = 'entrada'
        elif 'sobremesa' in cat_lower: target_cat = 'sobremesa'
        elif 'principal' in cat_lower or 'prato' in cat_lower: target_cat = 'principal'

        if target_cat:
            possibles = [_normalize_str(p) for p in cat_map[target_cat]]
            df = df[df['categoria_norm'].apply(lambda v: any(p in v for p in possibles))]

        # FILTRO 2: DIFICULDADE
        if dif_lower and 'qualquer' not in dif_lower:
            if 'facil' in dif_lower:
                df = df[df['dificuldade_norm'].str.contains('facil', na=False)]
            elif 'medio' in dif_lower:
                df = df[df['dificuldade_norm'].str.contains('medio', na=False)]
            elif 'dificil' in dif_lower:
                df = df[df['dificuldade_norm'].str.contains('dificil', na=False)]

        # FILTRO 3: TEMPO (Lógica Numérica)
        if time_lower and 'qualquer' not in time_lower:
            t_clean = time_lower.replace('(', ' ').replace(')', ' ').replace(',', ' ').replace('–', '-').strip()
            
            # Intervalo (ex: 30-60)
            range_match = re.search(r"(\d+)\s*[-]\s*(\d+)", t_clean)
            
            if range_match:
                low, high = int(range_match.group(1)), int(range_match.group(2))
                df = df[df['tempo_minutes'].notnull() & (df['tempo_minutes'] >= low) & (df['tempo_minutes'] <= high)]
            else:
                # "Até 30" ou "30 min"
                if 'ate' in _normalize_str(t_clean) or ('30' in t_clean and '60' not in t_clean):
                    limit = 30
                    num = re.search(r"(\d+)", t_clean)
                    if num: limit = int(num.group(1))
                    df = df[df['tempo_minutes'].notnull() & (df['tempo_minutes'] <= limit)]
                # "Mais de 1h"
                elif 'mais' in t_clean or '>' in t_clean or '1h' in t_clean or 'hora' in t_clean:
                    df = df[df['tempo_minutes'].notnull() & (df['tempo_minutes'] >= 60)]

        # FILTRO 4: RESTRIÇÕES
        restr_norm = _normalize_str(restrictions)
        if restr_norm and 'nenhuma' not in restr_norm and 'outro' not in restr_norm:
            kws = [restr_norm]
            if 'vegetariano' in restr_norm: kws = ['vegetariano']
            elif 'vegan' in restr_norm: kws = ['vegan']
            elif 'gluten' in restr_norm: kws = ['sem gluten']
            
            df = df[df['criterios_norm'].apply(lambda v: any(k in v for k in kws))]

        # FILTRO 5: EVITAR INGREDIENTES
        if avoid:
            tokens = [t.strip() for t in re.split(r'[|,;e]+', avoid) if t.strip()]
            tokens = [_normalize_str(t) for t in tokens]
            if tokens:
                df = df[~df['ingredientes_search'].apply(lambda x: any(t in x for t in tokens))]

        # FILTRO 6: CALORIAS
        if cal_lower and 'sem restricao' not in cal_lower:
            if 'leve' in cal_lower:
                df = df[df['calorias_num'].notnull() & (df['calorias_num'] <= 300)]
            elif 'moderado' in cal_lower:
                df = df[df['calorias_num'].notnull() & (df['calorias_num'] > 300) & (df['calorias_num'] <= 600)]

        # Ordenar
        if 'rating_num' in df.columns:
            df = df.sort_values(by='rating_num', ascending=False)

        num_results = len(df)

        if num_results == 0:
            msg_fail = "Não encontrei nada exato no meu livro de receitas para esses critérios."
            
            if HAS_GEMINI:
                dispatcher.utter_message(text=f"{msg_fail} Mas vou pedir ao meu Chef AI para criar uma exclusiva para ti... Um momento! 👨‍🍳✨")
                # --- TRADUÇÃO PARA LINGUAGEM NATURAL ---
                
                # 1. Traduzir Calorias
                prompt_caloric = caloric # Default
                if 'leve' in cal_lower:
                    prompt_caloric = "Baixas calorias (menos de 300 Kcal por dose)"
                elif 'moderado' in cal_lower:
                    prompt_caloric = "Moderado (entre 300 e 600 Kcal)"
                elif 'sem restricao' in cal_lower:
                    prompt_caloric = "Sem restrição calórica"

                # 2. Traduzir Tempo
                prompt_time = time # Default
                t_debug = time_lower.replace('(', '').replace(')', '')
                if '30-60' in t_debug or ('30' in t_debug and '60' in t_debug):
                    prompt_time = "Entre 30 e 60 minutos"
                elif 'ate' in _normalize_str(t_debug) or ('30' in t_debug and '60' not in t_debug):
                    prompt_time = "Rápido (menos de 30 minutos)"
                elif 'mais' in t_debug or '1h' in t_debug:
                    prompt_time = "Prato elaborado (mais de 1 hora)"

                # 3. Chamar Gemini com valores descritivos
                recipe_ai = generate_recipe_with_gemini(
                    category=category,
                    difficulty=difficulty,
                    time_desc=prompt_time,       
                    restrictions=restrictions,
                    avoid=avoid,
                    caloric_desc=prompt_caloric 
                )
                
                if recipe_ai:
                    dispatcher.utter_message(text=recipe_ai)
                else:
                    dispatcher.utter_message(text="Ocorreu um erro ao gerar a receita automática.")
            else:
                dispatcher.utter_message(text=f"{msg_fail} Tenta mudar os filtros.")
            
            return [SlotSet('search_results', [])]

        # SUCESSO -> MOSTRAR RECEITAS
        top_n = 5
        top = df.head(top_n)
        results_lines = []
        
        for i, row in top.iterrows():
            title = row.get('titulo', '')
            info = f"{row.get('dificuldade','')} | {row.get('tempo_total','')} | {row.get('calorias','')}"
            results_lines.append(f"{i+1}. **{title}** ({info})")

        text_out = "\n".join(results_lines)
        dispatcher.utter_message(text=f"Encontrei {num_results} receitas! 🥘 Aqui estão as melhores:\n\n{text_out}")

        return [SlotSet('search_results', top.to_dict('records'))]