from datetime import timedelta
from typing import Any, List

from extractors.Feature import Feature
from schemas.Event import Event

class JobModelingTime(Feature):

    def __init__(self, name:str, description:str, sessionID:str):
        min_data_version = None
        max_data_version = None
        super().__init__(name, description, min_data_version, max_data_version)
        self._sessionID = sessionID
        self._modeling_start_time = None
        self._time = timedelta(0)

    def GetEventTypes(self) -> List[str]:
        return []

    def CalculateFinalValues(self) -> Any:
        return self._time

    def _extractFromEvent(self, event:Event) -> None:
        if event.event_name == "begin_modeling":
            self._modeling_start_time = event.timestamp
        elif event.event_name == "room_changed":
            self._time += event.timestamp - self._modeling_start_time
            self._modeling_start_time = None
