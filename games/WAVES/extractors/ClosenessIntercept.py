from schemas import Event
from typing import Any, List, Union
# local imports
from extractors.Feature import Feature
from schemas.Event import Event

class ClosenessIntercept(Feature):
    def __init__(self, name:str, description:str, count_index:int):
        Feature.__init__(self, name=name, description=description, count_index=count_index)

    def GetEventTypes(self) -> List[str]:
        return []

    def GetFeatureValues(self) -> List[Any]:
        return []

    def _extractFromEvent(self, event:Event) -> None:
    #     closenesses = self.move_closenesses_tx[lvl]['completeness']
    #     times = self.move_closenesses_tx[lvl]['t']
    #     ranges = self.move_closenesses_tx[lvl]['range']
    #     if times:
    #         try:
    #             X = [(times[i]-times[0]).seconds for i in range(len(times))]
    #         except Exception as err:
    #             utils.Logger.toStdOut(times[0])
    #             raise err
    #         y = closenesses
    #         if len(X) > 1:
    #             intercept, slope, r_sq = self._2D_linear_regression(X, y)
    #             r_sq = r_sq if not np.isnan(r_sq) else 0
    #         else:
    #             intercept, slope, r_sq = 0,0,0
    #         self._features.setValByIndex(feature_name='closenessIntercept', index=lvl, new_value=intercept)
    #         self._features.setValByIndex(feature_name='closenessSlope', index=lvl, new_value=slope)
    #         self._features.setValByIndex(feature_name='closenessR2', index=lvl, new_value=r_sq)
        pass

    def MinVersion(self) -> Union[str,None]:
        return None

    def MaxVersion(self) -> Union[str,None]:
        return None
