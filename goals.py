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

def parse_goal(id, goal: dict) -> "T_GOAL":
    typestr = goal.pop("type", None)
    goalType: type
    if typestr is None:
        # attempt inferral (WARN: WILL NOT CATCH COMPLEX SUBCLASSES, specify type in this case)
        weighted = "weight" in goal.keys()
        exclusion = "exclusions" in goal.keys()
        
        if weighted and exclusion:
            goalType = WeightedExclusionGoal
        elif weighted:
            goalType = WeightedGoal
        elif exclusion:
            goalType = ExclusionGoal
        else:
            goalType = BaseGoal
    else:
        goalType = globals()[typestr]
    return goalType(id=id, **goal)

# Goal types

class BaseGoal():
    def __init__(self, id, name, translations: dict[str, str] = {}, **params) -> None:
        self.id = id
        self.name = name
        self.marks: set[int] = set()
        self.translations = translations
        self.__dict__.update(params)
    
    def mark(self, teamId):
        if teamId in self.marks: return False
        self.marks.add(teamId)
        return True
    
    def unmark(self, teamId):
        if teamId not in self.marks: return False
        self.marks.remove(teamId)
        return True

    def __str__(self) -> str:
        return self.name

    def get_repr(self) -> dict:
        return {"name": self.name, "translations": self.translations}
    
class WeightedGoal(BaseGoal):
    def __init__(self, weight, **params) -> None:
        self.weight = weight
        super().__init__(**params)

class ExclusionGoal(BaseGoal):
    def __init__(self, exclusions: set[str] = set(), **params) -> None:
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
