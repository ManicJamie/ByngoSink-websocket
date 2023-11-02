import json
import os
import random

from goal_types import *

class BaseGenerator():
    def __init__(self, name, seed, generator={}) -> None:
        self.name = name
        self.goals: list[BaseGoal] = [parse_goal(g) for g in generator.get("goals")]
        self.seed = seed
    
    def get(self, n) -> list[BaseGoal]:
        random.seed(self.seed)
        return random.sample(self.goals, n)

class MutexGenerator(BaseGenerator):
    def get(self, n) -> list["T_GOAL"]:
        random.seed(self.seed)
        available = self.goals
        sample = []
        excludes: set[str] = set()
        for i in range(n):
            while True:
                choice = random.choice(available)
                if choice.name in excludes:
                    available.remove(choice)
                    continue
                sample.append(choice)
                if isinstance(choice, ExclusionGoal):
                    excludes.update(choice.exclusions)
                break

        return sample
    
class TiebreakerGenerator(BaseGenerator):
    def __init__(self, name, seed, generator={}) -> None:
        self.tiebreakers: int = generator.get("tiebreakerMax", 0)
        super().__init__(name, seed, generator)
    
    def get(self, n) -> list["T_GOAL"]:
        random.seed(self.seed)
        sample = []
        available = self.goals
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
                break
        
        return sample

class TiebreakerMutexGenerator(BaseGenerator):
    def __init__(self, name, seed, generator={}) -> None:
        self.tiebreakers: int = generator.get("tiebreakerMax", 0)
        super().__init__(name, seed, generator)
    
    def get(self, n) -> list["T_GOAL"]:
        sample = []
        available = self.goals
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
                break
        
        return sample

ALL = {}
for gamepath in os.listdir("generators"):
    with open(f"generators/{gamepath}") as f:
        ALL[os.path.splitext(gamepath)[0]] = json.load(f)