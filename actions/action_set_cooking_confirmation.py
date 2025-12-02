from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


class ActionSetCookingConfirmation(Action):
    """Define o slot cooking_confirmation baseado no intent"""
    
    def name(self) -> Text:
        return "action_set_cooking_confirmation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        intent = tracker.latest_message.get('intent', {}).get('name')
        
        if intent == "has_ingredients_confirm":
            return [SlotSet("cooking_confirmation", "confirm")]
        elif intent == "show_ingredients_first":
            return [SlotSet("cooking_confirmation", "show_ingredients")]
        
        return []
    