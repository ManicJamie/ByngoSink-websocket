import pyjson5 as jsonc
import os
import random

from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from goals import T_GOAL
    T_GENERATOR = Union[
        "BaseGenerator",
        "FixedGenerator"]

from goals import parse_goal, ExclusionGoal, TiebreakerGoal

class FixedGenerator():
    def __init__(self, name, generator={}, **params) -> None:
        self.name = name
        self.goals = generator["goals"] # This is just a list of strings in this case (and this case only)
        self.game = generator["game"]
        self.__dict__.update(params)
    
    def get(self, seed, n) -> list["T_GOAL"]:
        return self.goals[:n]

class BaseGenerator():
    def __init__(self, name, generator:dict={}, **params) -> None:
        self.name = name
        self.goals: dict[str, "T_GOAL"] = {gid:parse_goal(gid, g) for gid, g in generator.get("goals").items()}
        self.count = len(self.goals)
        self.game = generator["game"]
        self.languages : dict[str, bool] = generator.get("languages", {})
        self.__dict__.update(params)
    
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        return random.sample(list(self.goals.values()), n)

class MutexGenerator(BaseGenerator):
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        available = self.goals.copy()
        sample = []
        for i in range(n):
            choice_key = random.choice(list(available.keys()))
            choice = available[choice_key]
            sample.append(choice)
            available.pop(choice_key)
            if isinstance(choice, ExclusionGoal):
                for e in choice.exclusions: available.pop(e, None)

        return sample
    
class TiebreakerGenerator(BaseGenerator):
    def __init__(self, name, generator={}) -> None:
        self.tiebreakers: int = generator.get("tiebreakerMax", 0)
        super().__init__(name, generator)
    
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        sample = []
        available = self.goals.copy()
        tiebreakers = self.tiebreakers
        for i in range(n):
            if tiebreakers <= 0:
                keys = list(available.keys())
                for gid in keys:
                    goal = available[gid]
                    if isinstance(goal, TiebreakerGoal): available.pop(gid)
            
            choice_key = random.choice(list(available.keys()))
            choice = available[choice_key]
            sample.append(choice)
            available.pop(choice_key)
            if isinstance(choice, TiebreakerGoal): tiebreakers -= 1
        
        return sample

class TiebreakerMutexGenerator(TiebreakerGenerator):    
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        sample = []
        available = self.goals.copy()
        tiebreakers = self.tiebreakers
        for i in range(n):
            if tiebreakers <= 0:
                keys = list(available.keys())
                for gid in keys:
                    goal = available[gid]
                    if isinstance(goal, TiebreakerGoal): available.pop(gid)
            
            choice_key = random.choice(list(available.keys()))
            choice = available[choice_key]
            sample.append(choice)
            available.pop(choice_key)
            if isinstance(choice, TiebreakerGoal): tiebreakers -= 1
            if isinstance(choice, ExclusionGoal):
                for e in choice.exclusions: available.pop(e, None)
    
        return sample

#TODO: add weighted generators!

def _create_gen(name, gendict: dict) -> Union[BaseGenerator, FixedGenerator]:
    typestr = gendict.pop("type")
    genType: type = globals()[typestr]
    return genType(name, gendict)

def get_generator(game_name, gen_name):
    return ALL[game_name][gen_name]

ALL: dict[str, dict[str, "T_GENERATOR"]] = {}
for gamepath in os.listdir("generators"):
    if not gamepath.endswith(".jsonc") or gamepath.startswith("_"): continue
    with open(f"generators/{gamepath}", encoding="utf-8") as f:
        game_name = os.path.splitext(gamepath)[0]
        ALL[game_name] = {name:_create_gen(name, gendict | {"game": game_name}) for name, gendict in jsonc.load(f).items()}