import logging

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from generators import T_GENERATOR
    from goals import T_GOAL
    
_log = logging.getLogger("byngosink")
_log.propagate = False

class Board():
    """Basic unbiased board"""
    name = "Board"
    def __init__(self, w, h, generator: "T_GENERATOR", seed: str) -> None:
        self.width = w
        self.height = h
        self.generator = generator
        self.game = generator.game
        self.generatorName = generator.name
        self.languages = generator.languages
        self.seed = seed
        self.goals: list[T_GOAL] = generator.get(seed, w*h)
        self.marks: dict[str, set] = {} # {Teamid : {goals}}
    
    def __min_view(self):
        return {"type": self.name, "width": self.width, "height": self.height,
                "maxMarksPerSquare": self.max_marks_per_square(), "game": self.game, "generatorName": self.generatorName}
    
    def max_marks_per_square(self):
        return 0  # Infinity
    
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
    
    def can_mark(self, index, teamid) -> bool:
        """Checked on mark and occasionally as extra board view detail (eg invasion, roguelike)"""
        return teamid is not None and index not in self.marks.get(teamid, {})
    
    def mark(self, index: int, teamid: str) -> bool:
        if not self.can_mark(index, teamid): return False

        if teamid not in self.marks: 
            self.marks[teamid] = {index}
        else: 
            self.marks[teamid].add(index)
        return True

    def can_unmark(self, index, teamid) -> bool:
        """Checked on unmark to maintain board invariants."""
        return teamid in self.marks and index in self.marks[teamid]
    
    def unmark(self, index, teamid) -> bool:
        if not self.can_unmark(index, teamid): return False

        marks = self.marks[teamid]
        marks.remove(index)
        if not marks:
            self.marks.remove(teamid)
        return True

    def get_dict(self) -> dict:
        return {"type": str(type(self)),
                "width": self.width,
                "height": self.height,
                "maxMarksPerSquare": self.max_marks_per_square(),
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

    # TODO: Chaos lockout
    def max_marks_per_square(self):
        return 1

    def can_mark(self, index, teamid):
        marked = set([v for marks in self.marks.values() for v in marks])
        return index not in marked

INVASION_TOP = 1
INVASION_LEFT = 2
INVASION_RIGHT = 3
INVASION_BOTTOM = 4
INVASION_ALL = frozenset([1, 2, 3, 4])

class Invasion(Lockout):
    """Basic invasion bingo board"""
    name = "Invasion"
    def __init__(self, generator: "T_GENERATOR", seed) -> None:
        super().__init__(generator, seed)
        self.start_constraints = dict()  # teamId -> invasionStart

        self.ranks = dict()  # constraint -> list[set(index)]
        self.ranks[INVASION_TOP] = [frozenset([self.index(x, y) for x in range(self.width)]) for y in range(self.height)]
        self.ranks[INVASION_LEFT] = [frozenset([self.index(x, y) for y in range(self.height)]) for x in range(self.width)]
        self.ranks[INVASION_RIGHT] = list(reversed(self.ranks[INVASION_LEFT]))
        self.ranks[INVASION_BOTTOM] = list(reversed(self.ranks[INVASION_TOP]))

    def other_team(self, teamid):
        for t in self.start_constraints:
            if t != teamid: return t

    def index(self, x, y):
        return x + y * self.width

    def inv_marks(self):
        d = dict()
        for teamid, marks in self.marks.items():
            for index in marks:
                d[index] = teamid
        return d
    
    def valid_progression(self, teamid, constraint):  # set(index)
        inv = self.inv_marks()

        filled = []
        available = []
        for r, rank in enumerate(self.ranks[constraint]):
            f = 0
            a = []
            for i in rank:
                t = inv.get(i, None)
                if t == teamid:
                    f += 1
                elif t is None:
                    a.append(i)
            filled.append(f)
            available.append(a)

        # Each rank is only available if the fill count is less than the previous rank.
        l = []
        for r in range(len(filled)):
            if r == 0 or filled[r - 1] > filled[r]:
                l.extend(available[r])
        return frozenset(l)

    def valid_moves(self, teamid):  # dict[index: set(constraint)]
        constraints = INVASION_ALL
        if teamid not in self.start_constraints:
            if len(self.start_constraints) == 2:
                # Only two teams can play invasion.
                constraints = [] 
            elif len(self.start_constraints) == 1:
                # Can only start on the opposite constraints.
                constraints = [5 - c for c in self.start_constraints[self.other_team(teamid)]]
        else:
            constraints = self.start_constraints[teamid]
        
        d = dict()
        for c in constraints:
            for i in self.valid_progression(teamid, c):
                d[i] = d.get(i, frozenset()).union(frozenset([c]))
        return d
    
    def update_constraints(self, teamid, constraints):
        self.start_constraints[teamid] = constraints

        oid = self.other_team(teamid)
        if oid is not None:
            # Constrain the opposing team if they started in a corner.
            self.start_constraints[oid] = frozenset([5 - c for c in constraints]).intersection(self.start_constraints[oid])

    def mark(self, index, teamid) -> bool:
        moves = self.valid_moves(teamid)
        c = moves.get(index, None)
        if c is not None:
            super().mark(index, teamid)

            # Update constraints
            self.update_constraints(teamid, c)
            return True
        else:
            return False
    
    def replay(self, teamid, indexes, constraints) -> bool:
        tomove = set(indexes)
        while tomove:
            moves = self.valid_moves(teamid)
            found = False
            for i in tomove:
                c = moves.get(i, None)
                if c is not None and c.issuperset(constraints):
                    tomove.remove(i)
                    super().mark(i, teamid)
                    self.update_constraints(teamid, c)
                    found = True
                    break
            
            if not found: return False
        return True

    def unmark(self, index, teamid) -> bool:
        if not self.can_unmark(index, teamid): return False

        # Unmark is only allowed if the resulting board state is valid.
        # Attempt to regenerate it, and if successful, use the regen.
        b = Invasion(self.generator, self.seed)

        toplay = set(self.marks[teamid])
        toplay.remove(index)
        if not b.replay(teamid, toplay, self.start_constraints.get(teamid, INVASION_ALL)):
            return False

        oid = self.other_team(teamid)
        if oid is not None:
            if not b.replay(oid, self.marks.get(oid, []), self.start_constraints.get(oid, INVASION_ALL)):
                return False

        self.marks = b.marks
        self.start_constraints = b.start_constraints
        return True

    def get_team_view(self, teamId) -> dict: 
        """`extras`: valid next moves"""
        return super().get_team_view(teamId) | {"extras": {"invasionMoves": list(self.valid_moves(teamId).keys())}}

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
    "Invasion": Invasion,
    "Exploration": Exploration13,
    "GTTOS": GTTOS13
}

def create_board(boardstr, generator: "T_GENERATOR", seed) -> Board:
    return ALIASES[boardstr](generator, seed)