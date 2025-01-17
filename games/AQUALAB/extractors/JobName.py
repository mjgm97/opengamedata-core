from datetime import timedelta
from typing import Any, List

from extractors.Feature import Feature
from schemas.Event import Event

class JobName(Feature):

    def __init__(self, name:str, description:str, job_num:int, job_map:dict):
        self._job_map = job_map
        super().__init__(name=name, description=description, count_index=job_num)

    def GetEventTypes(self) -> List[str]:
        return []

    def GetFeatureValues(self) -> List[Any]:
        for key in self._job_map.keys():
            if self._job_map[key] == self._count_index:
                return [key]
        return ["Job Name Not in Schema"]

    def _extractFromEvent(self, event:Event) -> None:
        return