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
        self.__dict__.update(params)
    
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        return random.sample(self.goals, n)

class MutexGenerator(BaseGenerator):
    # TODO: switch to using dict exclusion
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        available = list(self.goals.values())
        sample = []
        excludes: set[str] = set()
        for i in range(n):
            while True:
                choice = random.choice(available)
                if choice.id in excludes:
                    available.remove(choice)
                    continue
                sample.append(choice)
                available.remove(choice)
                if isinstance(choice, ExclusionGoal):
                    excludes.update(choice.exclusions)
                break

        return sample
    
class TiebreakerGenerator(BaseGenerator):
    def __init__(self, name, generator={}) -> None:
        self.tiebreakers: int = generator.get("tiebreakerMax", 0)
        super().__init__(name, generator)
    
    # TODO: switch to using dict exclusion
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        sample = []
        available = list(self.goals.values())
        tiebreakers = self.tiebreakers
        for i in range(n):
            while True:
                choice = random.choice(available)
                if isinstance(choice, TiebreakerGoal):
                    if tiebreakers <= 0:
                        available.remove(choice)
                        continue
                    else:
                        tiebreakers -= 1
                sample.append(choice)
                available.remove(choice)
                break
        
        return sample

class TiebreakerMutexGenerator(TiebreakerGenerator):    
    def get(self, seed, n) -> list["T_GOAL"]:
        random.seed(seed)
        sample = []
        available = list(self.goals.values())
        tiebreakers = self.tiebreakers
        excludes: set[str] = set()
        for i in range(n):
            while True:
                choice = random.choice(available)
                if choice.id in excludes:
                    available.remove(choice)
                    continue
                if isinstance(choice, TiebreakerGoal):
                    if tiebreakers <= 0:
                        available.remove(choice)
                        continue
                    else:
                        tiebreakers -= 1
                sample.append(choice)
                available.remove(choice)
                if isinstance(choice, ExclusionGoal):
                    excludes.update(choice.exclusions)
                break
        
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