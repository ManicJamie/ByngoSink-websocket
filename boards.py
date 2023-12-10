from typing import TYPE_CHECKING
from functools import reduce

if TYPE_CHECKING:
    from generators import T_GENERATOR
    from goals import T_GOAL
    from rooms import Room

class Mark():
    def __init__(self, team, goal, marked: bool) -> None:
        self.team = team
        self.goal = goal
        self.marked = marked

    def get(self) -> dict[str]:
        return {"team": self.team, "goal": self.goal, "marked": self.marked}

class Board():
    """Basic unbiased board"""
    name = "Board"
    def __init__(self, w, h, generator: "T_GENERATOR", seed: str, room: "Room") -> None:
        self.width = w
        self.height = h
        self.game = generator.game
        self.generatorName = generator.name
        self.seed = seed
        self.goals: list[T_GOAL] = generator.get(seed, w*h)
        self.marks: dict[str, set] = {} # {Teamid : {goals}}
        self.markHistory: list[Mark] = []
        self.room = room
    
    def get_minimum_view(self) -> dict:
        """Provides a minimum amount of data on the board for display (used for unteamed users)"""
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName}
    
    def get_team_view(self, teamId) -> dict:
        """Provides a view on the board for a given team."""
        return self.get_full_view()
    
    def get_spectator_view(self) -> dict:
        """Provides the base spectator view (this may not include all goals for some formats)"""
        return self.get_full_view()

    def get_full_view(self) -> dict:
        """Provides a complete view on all goals and marks"""
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName} | {"goals": {i:g.get_repr() for i, g in enumerate(self.goals)},
                "marks": {t:list(g) for t, g in self.marks.items()}}
    
    def can_mark(self, index, teamid):
        """Checked on mark and occasionally as extra board view detail (eg invasion, roguelike)"""
        return True
    
    def mark(self, index: int, teamid: str) -> bool:
        if not self.can_mark(index, teamid):
            return False

        # Add team if team DNE
        if teamid not in self.marks: 
            self.marks[teamid] = {index}
            return True
        
        # Return False if the goal is already marked
        elif index in self.marks[teamid]:
            return False
        else: 
            self.marks[teamid].add(index)
            self.markHistory.append(Mark(teamid, index, True))
            return True
    
    def unmark(self, index, teamid) -> bool:
        if teamid not in self.marks: 
            return False
        elif index not in self.marks[teamid]: 
            return False
        else: 
            self.marks[teamid].remove(index)
            self.markHistory.append(Mark(teamid, index, False))
            return True

class IrregularBoard(Board):
    """A special board type that supplies shape data alongside the minimum to construct an arbitrary board"""
    ... #TODO: for roguelike. needs major frontend changes to even begin thinking about for now

class ShowsUnmarkable(Board):
    """A special board type that gives teams data on goals they are not allowed to mark yet.
    
    Must add get_unmarkables as `unmarkables` in `get_team_view`."""
    def get_unmarkables(self, teamId):
        unmarkable = set()
        for i in range(len(self.goals)):
            if not self.can_mark(i, teamId): unmarkable.add(i)
        return unmarkable

class Bingo(Board):
    """Alias for 5x5 board"""
    name = "Non-Lockout"
    def __init__(self, generator: "T_GENERATOR", seed, room) -> None:
        super().__init__(5, 5, generator, seed, room)
    
    """Non-hidden formats, minimum == full""" 
    def get_minimum_view(self) -> dict: return self.get_full_view()
    def get_team_view(self, teamId) -> dict: return self.get_full_view()

class Lockout(Bingo):
    """Basic lockout bingo board"""
    name = "Lockout"
    def can_mark(self, index, teamid):
        team_marks = self.marks.get(teamid, set())
        if index in team_marks: return True
        allmarked = set().union(*self.marks.values())
        if index in allmarked:
            return False
        else:
            return True

class Invasion(Lockout):
    """i am in great pain"""
    name = "Invasion"

    def __init__(self, generator: "T_GENERATOR", seed, room) -> None:

        super().__init__(generator, seed, room)

        self.team1 = None
        self.team2 = None

        self.team1_possible_directions = {'left', 'right', 'top', 'jamie'}

        left = [ set(row * self.width + col for row in range(self.height)) for col in range(self.width)]
        right = left[::-1]
        top  = [ set(row * self.width + col for col in range(self.width)) for row in range(self.height)]
        jamie = top[::-1]

        self.line_order = {'left': left, 'right': right, 'top': top, 'jamie': jamie}

    def mark(self, index, teamid):
        marked = super().mark(index, teamid)

        # Step 1: We hope we don't need to do anything
        if not marked:
            return False

        # Step 2: This means the goal is allowed to be marked and has been marked. We need only update the teams.
        
        # Add the team if it's not already there
        if (not self.team1) or self.team1 == teamid:
            self.team1 = teamid
        elif (not self.team2) or self.team2 == teamid:
            self.team2 = teamid
        else:
            # We shouldn't be here. Panic. I don't know what logging system you have but you should pray to it right about now
            pass

        # Update what possible directions we can go in
        self.team1_possible_directions = self.get_valid_team_directions(self.team1, self.team2, self.marks[self.team1], self.marks[self.team2] if self.team2 else set(), self.team1_possible_directions)

        return True
    
    def opp(self, direction):
        return {'left': 'right', 'right': 'left', 'top': 'jamie', 'jamie': 'top'}[direction]

    def get_valid_team_directions(self, t1_id, t2_id, t1_marked, t2_marked, t1_possible_directions):
        t1_valid = set()

        # Go through all directions that the teams can still do, and validate
        for d in t1_possible_directions:
            if (self.valid_invasion(t1_marked, self.line_order[d]) and self.valid_invasion(t2_marked, self.line_order[self.opp(d)])):
                t1_valid.add(d)
        
        return t1_valid

    def valid_invasion(self, marked_goals, order):
        num_marked = [len(marked_goals & line) for line in order]
        return all(num_marked[i] >= num_marked[i + 1] for i in range(len(num_marked) - 1))

    def can_mark(self, index, teamid):
        can_mark_ = super().can_mark(index, teamid)
        
        # Step 1: We hope we don't need to do anything
        if not can_mark_:
            return False
        
        team1_marks = self.marks[self.team1] if self.team1 else set()
        team2_marks = self.marks[self.team2] if self.team2 else set()

        # If this team_id is or will be team 1 ...
        if (not self.team1) or self.team1 == teamid:
            vtd = self.get_valid_team_directions(self.team1, self.team2, team1_marks | {index}, team2_marks, self.team1_possible_directions)

        # If this team_id is or will be team 2 ...
        elif (not self.team2) or self.team2 == teamid:
            vtd = self.get_valid_team_directions(self.team1, self.team2, team1_marks, team2_marks | {index}, self.team1_possible_directions)
        
        # No I am not implementing more than 2 teams
        else:
            return False

        return len(vtd) > 0
            
class Chaos(Bingo):
    """1v...v1 lockout"""
    name = "Chaos Lockout"

    def __init__(self, generator: "T_GENERATOR", seed, room) -> None:
        super().__init__(generator, seed, room)
    
    ... #TODO:


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
        
    def _get_seen(self, teamId):
        team_marks = self.marks.get(teamId, set())
        overall_seen = self.base.copy()
        for i in self.base:
            overall_seen.update(self._recurse_seen_goals(i, team_marks, overall_seen))
        return overall_seen
    
    def _get_all_seen(self):
        all_marks = set().union(*self.marks.values())
        overall_seen = self.base.copy()
        for i in self.base:
            overall_seen.update(self._recurse_seen_goals(i, all_marks, overall_seen))
        return overall_seen
    
    def _recurse_seen_goals(self, i, team_marks, seen:set):
        if i in team_marks:
            x = i % 13
            y = i // 13
            adj_xys = {(x - 1, y), (x + 1, y), (x, y + 1), (x, y - 1)}
            to_check = set()
            for xy in adj_xys:
                if xy[0] >= 0 and xy[0] <= 12 and xy[1] >= 0 and xy[1] <= 12:
                    index = xy[1] * 13 + xy[0]
                    if index not in seen: to_check.add(index)
            to_check.difference_update(seen) # don't check already seen values
            seen.update(to_check)
            for i in to_check:
                self._recurse_seen_goals(i, team_marks, seen)
        return seen

class Exploration13(Exploration):
    """13x13 Exploration board"""
    base = {84}
    finals = {0, 12, 156, 168}
    def __init__(self, generator: "T_GENERATOR", seed, room) -> None:
        super().__init__(13, 13, generator, seed, room)

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
    def __init__(self, generator: "T_GENERATOR", seed, room) -> None:
        super().__init__(13, 13, generator, seed, room)

ALIASES = {
    "Non-Lockout": Bingo,
    "Lockout": Lockout,
    "Exploration": Exploration13,
    "GTTOS": GTTOS13,
    "Invasion": Invasion
}

def create_board(boardstr, generator: "T_GENERATOR", seed, room) -> Board:
    return ALIASES[boardstr](generator, seed, room)

print("Begin")
