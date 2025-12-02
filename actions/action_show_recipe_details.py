import re
from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


class ActionShowRecipeDetails(Action):
    def name(self) -> Text:
        return "action_show_recipe_details"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Obter a lista de receitas guardada
        search_results = tracker.get_slot("search_results")
        
        if not search_results or len(search_results) == 0:
            dispatcher.utter_message(text="Não tenho receitas guardadas. Faz uma pesquisa primeiro!")
            return []

        # --- Lógica de EXTRAÇÃO do número da receita ---
        selected_num = tracker.get_slot("selected_recipe_number")
        recipe_num = None
        
        # 1. Tentar obter do slot direto
        if selected_num is not None:
            try:
                recipe_num = int(selected_num)
            except (ValueError, TypeError):
                recipe_num = None
        
        # 2. Se não estiver no slot, tentar extrair da última mensagem
        if recipe_num is None:
            user_message = tracker.latest_message.get('text', '').lower()
            
            # Padrão: "receita 3", "receita número 2"
            match = re.search(r'receita\s*(?:n[úu]mero\s*)?(\d+)', user_message)
            if match:
                recipe_num = int(match.group(1))
            
            # Padrão: Apenas um número (ex: "mostra a 2", "2")
            if not recipe_num:
                match = re.search(r'\b(\d+)\b', user_message)
                if match:
                    recipe_num = int(match.group(1))
            
            # Padrão: Ordinais
            if not recipe_num:
                ordinals = {
                    'primeira': 1, 'primeiro': 1,
                    'segunda': 2, 'segundo': 2,
                    'terceira': 3, 'terceiro': 3,
                    'quarta': 4, 'quarto': 4,
                    'quinta': 5, 'quinto': 5
                }
                for word, num in ordinals.items():
                    if word in user_message:
                        recipe_num = num
                        break

        # Se ainda assim for None, desistir
        if recipe_num is None:
            dispatcher.utter_message(
                text="Não percebi qual receita queres. Podes dizer 'receita 1', '2', ou 'a terceira'?"
            )
            return [SlotSet("selected_recipe_number", None)]

        # --- Validação ---
        recipe_index = recipe_num - 1 # Converter para índice de lista (0-based)

        if recipe_index < 0 or recipe_index >= len(search_results):
            dispatcher.utter_message(
                text=f"Número inválido! Escolhe entre 1 e {len(search_results)}."
            )
            return [SlotSet("selected_recipe_number", None)]

        # --- Obter dados da receita ---
        recipe = search_results[recipe_index]

        # Formatar detalhes
        titulo = recipe.get('titulo', 'Sem título')
        categoria = recipe.get('categoria', 'N/A')
        dificuldade = recipe.get('dificuldade', 'N/A')
        tempo = recipe.get('tempo_total', 'N/A')
        calorias = recipe.get('calorias', 'N/A')
        rating = recipe.get('rating', 'N/A')
        
        # Ingredientes (separados por |)
        ingredientes_raw = recipe.get('ingredientes', '')
        if ingredientes_raw:
            ingredientes_list = [f"  • {ing.strip()}" for ing in ingredientes_raw.split('|')]
            ingredientes_text = "\n".join(ingredientes_list)
        else:
            ingredientes_text = "  (Não especificado)"
        
        # Passos (separados por |) - Calcular total_steps aqui
        passos_raw = recipe.get('passos', '')
        if passos_raw:
            passos_list_clean = [p for p in passos_raw.split('|') if p.strip()]
            passos_formatted = [f"  {i+1}. {passo.strip()}" for i, passo in enumerate(passos_list_clean)]
            passos_text = "\n".join(passos_formatted)
            total_steps = float(len(passos_list_clean))
        else:
            passos_text = "  (Não especificado)"
            total_steps = 0.0
        
        # Critérios
        criterios = recipe.get('criterios', 'N/A')

        # Montar mensagem final
        message = f"""**{titulo}**

**Informações:**
  • Categoria: {categoria}
  • Dificuldade: {dificuldade}
  • Tempo: {tempo}
  • Calorias: {calorias}
  • Avaliação: ⭐ {rating}/5
  
**Características:** {criterios}

**Ingredientes:**
{ingredientes_text}

**Modo de Preparo:**
{passos_text}

---
Bom apetite!
"""

        dispatcher.utter_message(text=message)
        
        # --- CORREÇÃO FINAL E ESSENCIAL ---
        # Retorna o número da receita E o total de passos para persistir nos slots
        # return [
        #     SlotSet("selected_recipe_number", str(recipe_num)),
        #     SlotSet("total_steps", total_steps)
        # ]
        
        
        return [
            SlotSet("selected_recipe_number", str(recipe_num)),
            SlotSet("total_steps", float(total_steps)),
            # Adicione isto para garantir que o search_results não desaparece
            SlotSet("search_results", search_results) 
        ]