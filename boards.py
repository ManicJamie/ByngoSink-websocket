from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generators import T_GENERATOR
    from goals import T_GOAL

class Board():
    """Basic unbiased board"""
    name = "Board"
    def __init__(self, w, h, generator: "T_GENERATOR", seed: str) -> None:
        self.width = w
        self.height = h
        self.game = generator.game
        self.generatorName = generator.name
        self.languages = generator.languages
        self.seed = seed
        self.goals: list[T_GOAL] = generator.get(seed, w*h)
        self.marks: dict[str, set] = {} # {Teamid : {goals}}
    
    def __min_view(self):
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName}
    
    def get_minimum_view(self) -> dict:
        """Provides a minimum amount of data on the board for display (used for unteamed users)"""
        return self.__min_view()
    
    def get_team_view(self, teamId) -> dict:
        """Provides a view on the board for a given team."""
        return self.get_full_view()
    
    def get_spectator_view(self) -> dict:
        """Provides the base spectator view (this may not include all goals for some formats)"""
        return self.get_full_view()

    def get_full_view(self) -> dict:
        """Provides a complete view on all goals and marks"""
        return self.__min_view() | {"goals": {i:g.get_repr() for i, g in enumerate(self.goals)},
                                          "marks": {t:list(g) for t, g in self.marks.items()}}
    
    def can_mark(self, index, teamid):
        """Checked on mark and occasionally as extra board view detail (eg invasion, roguelike)"""
        return True
    
    def mark(self, index: int, teamid: str) -> bool:
        if not self.can_mark(index, teamid): return False

        if teamid not in self.marks: 
            self.marks[teamid] = {index}
        elif index in self.marks[teamid]: 
            return False
        else: 
            self.marks[teamid].add(index)
        return True
    
    def unmark(self, index, teamid) -> bool:
        if teamid not in self.marks: 
            return False
        elif index not in self.marks[teamid]: 
            return False
        else: 
            self.marks[teamid].remove(index)
        return False

    def get_dict(self) -> dict:
        return {"type": str(type(self)),
                "width": self.width,
                "height": self.height,
                "goals": self.goals,
                "marks": self.marks}

class Bingo(Board):
    """Alias for 5x5 board"""
    name = "Non-Lockout"
    def __init__(self, generator: "T_GENERATOR", seed) -> None:
        super().__init__(5, 5, generator, seed)
    
    """Non-hidden formats, minimum == full""" 
    def get_minimum_view(self) -> dict: return self.get_full_view()
    def get_team_view(self, teamId) -> dict: return self.get_full_view()

class Lockout(Bingo):
    """Basic lockout bingo board"""
    name = "Lockout"
    def can_mark(self, index, teamid):
        allmarked = set().union(*self.marks.values())
        if index in allmarked:
            return False
        else:
            return True

class Exploration(Board):
    """13x13 board with marks hidden between teams and only adjacent goals displayed. 
    
    Center->Corner"""
    name = "Exploration"
    base: set[int] = set()
    finals: set[int] = set()
    
    def get_minimum_view(self) -> dict:
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName,
                "goals": {i:self.goals[i].get_repr() for i in self.base},
                "base": list(self.base), "finals": list(self.finals)}
    
    def _get_base_team_view(self, teamId) -> dict:
        """Double blind, adjacent revealed goals"""
        if teamId is None: return self.get_minimum_view()
        seen_goals = self._get_seen(teamId)

        return self.get_minimum_view() | {"goals": {i:self.goals[i].get_repr() for i in seen_goals},
                                          "marks": {teamId:list(self.marks.get(teamId, set()))}}

    def get_team_view(self, teamId) -> dict: 
        """Double blind marks (No other team marks seen), adjacent goals revealed.
        
        `extras`: Currently empty until details of exploration spying are sorted"""
        return self._get_base_team_view(teamId) | {"extras": {}}
    
    def get_spectator_view(self) -> dict:
        seen_goals = self._get_all_seen()
        return self.get_minimum_view() | {"goals": {i:self.goals[i].get_repr() for i in seen_goals},
                                          "marks": {t:list(g) for t, g in self.marks.items()}}

    def can_mark(self, index: int, teamid: str) -> bool:
        if teamid is None: return False
        seen = self._get_seen(teamid)
        if index not in seen: return False
        else: return True

    def _get_surrounding(self, index):
        x = index % self.width
        y = index // self.height
        adj_xys = {(x - 1, y), (x + 1, y), (x, y + 1), (x, y - 1)}
        surrounds = set()
        for xy in adj_xys:
            if xy[0] >= 0 and xy[0] < self.width and xy[1] >= 0 and xy[1] < self.height:
                surrounds.add(xy[1] * self.width + xy[0])
        return surrounds
        
    def _get_seen(self, teamId):
        team_marks = self.marks.get(teamId, set())
        overall_seen = self.base.copy()
        for mark in team_marks:
            overall_seen.update(self._get_surrounding(mark))
        return overall_seen
    
    def _get_all_seen(self):
        all_marks = set().union(*self.marks.values())
        overall_seen = self.base.copy()
        for mark in all_marks:
            overall_seen.update(self._get_surrounding(mark))
        return overall_seen

class Exploration13(Exploration):
    """13x13 Exploration board"""
    base = {84}
    finals = {0, 12, 156, 168}
    def __init__(self, generator: "T_GENERATOR", seed) -> None:
        super().__init__(13, 13, generator, seed)

class GTTOS(Exploration):
    """13x13 board with marks hidden between teams and only adjacent goals displayed.
     
       Left->Right"""
    name="Get To The Other Side"

    def _get_mark_cols(self):
        out = {}
        for teamid, marks in self.marks.items():
            maxCol = 0
            for m in marks:
                col = m % self.width
                if col > maxCol:
                    maxCol = col
            out[teamid] = maxCol
        return out

    def get_team_view(self, teamId) -> dict: 
        """Double blind marks (No other team marks seen), adjacent goals revealed.
        
        `extras`: highest marked column for each team"""
        return self._get_base_team_view(teamId) | {"extras": {"colMarks": self._get_mark_cols()}}

class GTTOS13(GTTOS):
    base = {0, 13, 26, 39, 52, 65, 78, 91, 104, 117, 130, 143, 156}
    finals = {12, 25, 38, 51, 64, 77, 90, 103, 116, 129, 142, 155, 168}
    def __init__(self, generator: "T_GENERATOR", seed) -> None:
        super().__init__(13, 13, generator, seed)

ALIASES = {
    "Non-Lockout": Bingo,
    "Lockout": Lockout,
    "Exploration": Exploration13,
    "GTTOS": GTTOS13
}

def create_board(boardstr, generator: "T_GENERATOR", seed) -> Board:
    return ALIASES[boardstr](generator, seed)