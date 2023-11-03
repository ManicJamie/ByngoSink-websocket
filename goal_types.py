from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    T_GOAL = Union["BaseGoal",
                    "WeightedGoal",
                    "ExclusionGoal",
                    "WeightedExclusionGoal",
                    "TiebreakerGoal",
                    "TiebreakerExclusionGoal",
                    "WeightedTiebreakerExclusionGoal",
                    "WeightedTiebreakerGoal"]

def parse_goal(goal: dict) -> "T_GOAL":
    typestr = goal.pop("type", None)
    if typestr is None:
        # attempt inferral (WARN: WILL NOT CATCH COMPLEX SUBCLASSES, specify type in this case)
        weighted = "weight" in dict.keys()
        exclusion = "exclusions" in dict.keys()
        if weighted and exclusion:
            goalType = WeightedExclusionGoal
        elif weighted:
            goalType = WeightedGoal
        elif exclusion:
            goalType = ExclusionGoal
        else:
            goalType = BaseGoal
    else:
        goalType: type = globals()[typestr]
    return goalType(**goal)

#### Goal types

class BaseGoal():
    def __init__(self, name, **params) -> None:
        self.name = name
        self.__dict__.update(params)

    def __str__(self) -> str:
        return self.name
    
class WeightedGoal(BaseGoal):
    def __init__(self, weight, **params) -> None:
        self.weight = weight
        super().__init__( **params)

class ExclusionGoal(BaseGoal):
    def __init__(self, exclusions:set[str]={}, **params) -> None:
        self.exclusions = exclusions
        super().__init__(**params)

class WeightedExclusionGoal(ExclusionGoal, WeightedGoal):
    pass

class TiebreakerGoal(BaseGoal):
    pass

class TiebreakerExclusionGoal(ExclusionGoal, TiebreakerGoal):
    pass

class WeightedTiebreakerExclusionGoal(WeightedExclusionGoal, TiebreakerGoal):
    pass

class WeightedTiebreakerGoal(WeightedGoal, TiebreakerGoal):
    pass