import re
from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction


# --- Funções Auxiliares ---

def get_recipe_details(tracker: Tracker) -> tuple[Dict[Text, Any] | None, list[str] | None]:
    """Obtém a receita selecionada e a lista de passos (separados)."""
    search_results = tracker.get_slot("search_results")
    selected_num = tracker.get_slot("selected_recipe_number")
    
    # Debug prints
    print(f"🔍 DEBUG - selected_recipe_number: {selected_num}")
    
    if not search_results or not selected_num:
        return None, None
    
    try:
        recipe_index = int(selected_num) - 1
        
        if recipe_index < 0 or recipe_index >= len(search_results):
            return None, None
            
        recipe = search_results[recipe_index]
        
        # Os passos estão no campo 'passos', separados por '|'
        passos_raw = recipe.get('passos', '')
        steps = [step.strip() for step in passos_raw.split('|') if step.strip()]
        
        return recipe, steps
    except (ValueError, IndexError, TypeError) as e:
        print(f"⚠️ DEBUG - Exceção na extração da receita: {e}")
        return None, None


# 1. Ação para iniciar o modo de cozinha
class ActionStartCookingMode(Action):
    """Inicia o modo passo-a-passo."""
    
    def name(self) -> Text:
        # CORRIGIDO: Nome exato conforme domain.yml e cooking_flow.yml
        return "action_start_cooking_mode"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        search_results = tracker.get_slot("search_results")
        selected_num = tracker.get_slot("selected_recipe_number")

        print(f"🔍 DEBUG START - selected_num: {selected_num}")

        if not search_results or not selected_num:
            dispatcher.utter_message(
                text="❌ Não foi possível carregar a receita selecionada. Por favor, seleciona uma receita primeiro."
            )
            return []

        # Validação simples para garantir que o número é válido
        try:
            recipe_index = int(selected_num) - 1
            if recipe_index < 0 or recipe_index >= len(search_results):
                 dispatcher.utter_message(text="❌ Número da receita inválido.")
                 return [SlotSet("selected_recipe_number", None)]
        except (ValueError, TypeError):
             dispatcher.utter_message(text="❌ Erro ao ler o número da receita.")
             return [SlotSet("selected_recipe_number", None)]

        # Sucesso: Inicializar o modo de cozinha
        # current_step_number: Começa no 0.0. A action_next_step passará para 1.0.
        return [
            SlotSet("cooking_mode_active", True),
            SlotSet("current_step_number", 0.0), 
        ]


# 2. Ação para avançar para o próximo passo
class ActionNextStep(Action):
    """Avança para o próximo passo da receita."""
    
    def name(self) -> Text:
        return "action_next_step"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        current_step = tracker.get_slot("current_step_number")
        total_steps = tracker.get_slot("total_steps")

        if current_step is None or total_steps is None:
            dispatcher.utter_message(text="Erro: O modo de cozinha não foi inicializado corretamente.")
            return [SlotSet("cooking_mode_active", False)]
        
        current_step = int(current_step)
        total_steps = int(total_steps)

        next_step = current_step + 1

        if next_step > total_steps:
            # Se exceder o total, finaliza a receita
            return [FollowupAction("action_complete_recipe")]
        
        return [SlotSet("current_step_number", float(next_step))]


# 3. Ação para voltar para o passo anterior
class ActionPreviousStep(Action):
    """Volta para o passo anterior da receita."""
    
    def name(self) -> Text:
        return "action_previous_step"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        current_step = tracker.get_slot("current_step_number")

        if current_step is None:
            dispatcher.utter_message(text="Erro: Passo atual não definido.")
            return []

        current_step = int(current_step)

        if current_step <= 1:
            dispatcher.utter_message(text="Já estás no primeiro passo!")
            return []

        previous_step = current_step - 1
        return [SlotSet("current_step_number", float(previous_step))]


# 4. Ação para mostrar o passo atual
class ActionShowCurrentStep(Action):
    """Mostra o passo atual da receita com botões de navegação."""
    
    def name(self) -> Text:
        return "action_show_current_step"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        
        recipe, steps = get_recipe_details(tracker)
        current_step = tracker.get_slot("current_step_number")
        total_steps = tracker.get_slot("total_steps")

        if not recipe or current_step is None:
            dispatcher.utter_message(text="❌ Erro: Não foi possível exibir o passo da receita.")
            return []
        
        # Se total_steps não estiver definido no slot, tentamos inferir da lista de passos
        if total_steps is None and steps:
            total_steps = len(steps)
        elif total_steps is None:
            total_steps = 0

        current_step_int = int(current_step)
        total_steps_int = int(total_steps)

        # Verifica se o passo atual é válido
        if current_step_int < 1 or current_step_int > total_steps_int:
            # Se for 0, provavelmente ainda não começou, não faz nada ou avisa
             if current_step_int == 0:
                 return []
             dispatcher.utter_message(text="❌ Erro: Passo fora do intervalo.")
             return [SlotSet("cooking_mode_active", False)]

        # Obter o texto do passo (índice é passo - 1)
        if steps and (current_step_int - 1) < len(steps):
            step_text = steps[current_step_int - 1]
        else:
            step_text = "Texto do passo não encontrado."

        # Mensagem formatada
        message = f"PASSO **{current_step_int} de {total_steps_int}**:\n{step_text}"
        
        # --- Botões de Navegação ---
        buttons = []
        
        # Botão Próximo Passo
        if current_step_int < total_steps_int:
             buttons.append({"title": "Próximo Passo", "payload": "/next_step"})
        else:
             buttons.append({"title": "Terminar Receita", "payload": "/complete_recipe"})

        # Botão Voltar
        if current_step_int > 1:
            buttons.append({"title": "Voltar", "payload": "/previous_step"})
        
        # Botões extra
        buttons.append({"title": "Repetir", "payload": "/repeat_step"})
        buttons.append({"title": "Ajuda", "payload": "/need_help_step"})

        dispatcher.utter_message(text=message, buttons=buttons)

        return []


# 5. Ação para finalizar a receita
class ActionCompleteRecipe(Action):
    """Marca a receita como completa e limpa os slots."""
    
    def name(self) -> Text:
        return "action_complete_recipe"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(
            text="🎉 Parabéns! Terminaste a receita!\n\nComo correu?",
            buttons=[
                {"title": "⭐⭐⭐⭐⭐", "payload": "/rate{\"stars\":5}"},
                {"title": "⭐⭐⭐⭐", "payload": "/rate{\"stars\":4}"},
                {"title": "⭐⭐⭐", "payload": "/rate{\"stars\":3}"}
            ]
        )
        
        # Resetar slots para sair do modo de cozinha
        return [
            SlotSet("cooking_mode_active", False),
            SlotSet("current_step_number", None),
            SlotSet("total_steps", None),
            SlotSet("selected_recipe_number", None),
        ]