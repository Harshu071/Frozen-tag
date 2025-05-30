# ba_meta require api 9
# ba_meta export game

"""BombSquad / Ballistica custom game-mode.

• Bots are the "Freezers": they chase and freeze any player they touch. • Two human teams are the "Runners": they must avoid the bots and can rescue (un-freeze) their own frozen teammates by touching them. • Punching is disabled for all players. • A round timer can end the game; otherwise the last team with an unfrozen player wins.

Drop this file in your mods folder, reload scripts (or restart the app), then pick Frozen Tag from the Custom tab. """

from future import annotations

from typing import List, Sequence, Dict

import random 
import math
import babase 
import bascenev1 as bs 
import bascenev1lib.bots as bs_bots

----------------------------------------------------------------------

#✅ Player & Team subclasses ------------------------------------------------

class Player(bs.Player["Team"]): """Our player class stores a frozen flag."""

frozen: bool = False

class Team(bs.Team[Player]): """Our team class has no special data for now."""

----------------------------------------------------------------------

#✅ Main Activity -----------------------------------------------------------

class FrozenTag(bs.TeamGameActivity[Player, Team]): """Frozen Tag – runners vs freezer-bots (API 9)."""

name = "Frozen Tag"
description = (
    "Avoid the freezer-bots; touch your frozen teammates to thaw them. "
    "Last team with a mobile player wins!"
)

# Activity settings that show up in the custom tab (seconds).
available_settings = [
    bs.IntSetting("Round Length", default=90, min_value=30, max_value=300, increment=15)
]

# We are symmetric: any map that works for melee should be ok.
@classmethod
def get_supported_maps(cls, session: bs.Session) -> List[str]:
    return bs.getmaps("melee")

# ------------------------------------------------------------------
# ⚙️ Activity lifecycle -------------------------------------------

def __init__(self, settings: dict):
    super().__init__(settings)
    self._round_length = float(settings["Round Length"])
    self._bots: bs_bots.BotSet | None = None
    self._update_timer: bs.Timer | None = None

def on_begin(self) -> None:
    super().on_begin()

    # ▶️ Spawn freezer bots (1 per 4 players, min 1).
    num_bots = max(1, math.ceil(len(self.players) / 4))
    self._bots = bs_bots.BotSet()
    for _ in range(num_bots):
        # SoldierBot is fairly quick and will punch/tag runners.
        self._bots.spawn_bot(bs_bots.SoldierBot, pos=self.map.get_spawn_point())

    # Disable punching for all existing and future players.
    for p in self.players:
        if p.is_alive():
            assert p.actor
            p.actor.node.punch_pressed = False
            p.actor.node.punch_power = 0.0

    # Round end timer.
    bs.timer(self._round_length, self._end_round)

    # Frequent updater – check win conditions & give bots targets.
    self._update_timer = bs.Timer(0.5, self._update, repeat=True)

# ----------------------------------------------------------------

