from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    T_GOAL = Union["BaseGoal", "ExclusionGoal"]

def parse_goal(goal: dict) -> "T_GOAL":
    typestr = goal.pop("type")
    goalType: type = globals()[typestr]
    return goalType(**goal)

class BaseGoal():
    def __init__(self, name, description, weight, **params) -> None:
        self.name = name
        self.description = description
        self.weight = weight
        self.__dict__.update(params)

    def __str__(self) -> str:
        return self.description

class ExclusionGoal(BaseGoal):
    def __init__(self, name, description, exclusions:set[str]={}, **params) -> None:
        self.exclusions = exclusions
        super().__init__(name, description, **params)

class TiebreakerGoal(BaseGoal):
    pass

class TiebreakerExclusionGoal(ExclusionGoal, TiebreakerGoal):
    pass