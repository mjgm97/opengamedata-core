# global imports
import logging
from datetime import datetime
from schemas import Event
from typing import Any, List, Union
# local imports
import utils
from extractors.PerLevelFeature import PerLevelFeature
from schemas.Event import Event

class TotalLevelTime(PerLevelFeature):
    def __init__(self, name:str, description:str, count_index:int):
        PerLevelFeature.__init__(self, name=name, description=description, count_index=count_index)
        self._begin_times    : List[datetime] = []
        self._complete_times : List[datetime] = []

    def GetEventTypes(self) -> List[str]:
        return ["BEGIN.0", "COMPLETE.0"]

    def GetFeatureValues(self) -> List[Any]:
        if len(self._begin_times) < len(self._complete_times):
            utils.Logger.Log(f"Player began level {self._count_index} {len(self._begin_times)} times but completed it {len(self._complete_times)}.", logging.DEBUG)
        _num_plays = min(len(self._begin_times), len(self._complete_times))
        _diffs = [(self._complete_times[i] - self._begin_times[i]).total_seconds() for i in range(_num_plays)]
        return [sum(_diffs)]

    def _extractFromEvent(self, event:Event) -> None:
        if event.event_name == "BEGIN.0":
            self._begin_times.append(event.timestamp)
        elif event.event_name == "COMPLETE.0":
            self._complete_times.append(event.timestamp)
        else:
            utils.Logger.Log(f"AverageLevelTime received an event which was not a BEGIN or a COMPLETE!", logging.WARN)

    def MinVersion(self) -> Union[str,None]:
        return None

    def MaxVersion(self) -> Union[str,None]:
        return None
