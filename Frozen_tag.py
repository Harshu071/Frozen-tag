# frozen_tag_with_bots.py
# BombSquad plugin: Frozen Tag with Bots (Two teams of runners, bots freeze players)
# Players can't punch (punch disabled)

import bs
import random

class FrozenTagGame(bs.TeamGameActivity):
    @classmethod
    def get_name(cls):
        return "Frozen Tag with Bots"

    @classmethod
    def get_description(cls, session):
        return "Bots freeze players by tagging. Players unfreeze teammates by touch."

    @classmethod
    def get_supported_maps(cls, session):
        return bs.getmaps("melee")

    def __init__(self, settings):
        super().__init__(settings)
        self._bots = []
        self._freeze_time = 9999  # Freeze duration effectively infinite until unfreeze
        self._round_length = 60  # seconds

    def on_begin(self):
        super().on_begin()
        self._spawn_bots()
        self._update()

        # Start round timer
        self._timer = bs.Timer(self._round_length * 1000, self._on_round_end)

    def _spawn_bots(self):
        # Spawn 2 bots as freezers, with simple AI
        for i in range(2):
            bot = bs.Bot(
                spawn_position=(random.uniform(-5, 5), 1, random.uniform(-5, 5)),
                color=(0.2, 0.8, 1),  # Blueish color for bots
                character="Spaz",
                highlight=False,
                name=f"FreezerBot {i+1}",
            )
            bot.connect_controls_to_player()
            self._bots.append(bot)

    def handlemessage(self, msg):
        if isinstance(msg, bs.PlayerDiedMessage):
            self._check_for_win()

        if isinstance(msg, bs.HitMessage):
            self._handle_hit(msg)

        if isinstance(msg, bs.PunchHitMessage):
            # Block punch hits from players
            # Ignore punches from players, allow from bots
            if hasattr(msg.source, "player") and msg.source.player.is_human:
                return True  # block punch damage

        if isinstance(msg, bs.PickupMessage):
            # No punching, but allow pickup if needed
            pass

        if isinstance(msg, bs.PlayerSpawnMessage):
            # Disable punching for players
            player = msg.player
            if player.exists():
                player.actor.node.punch_callback = lambda *args, **kwargs: None
                player.actor.node.punch_power = 0
                player.actor.node.can_punch = False
                player.actor.node.handlemessage("disable_punch", True)

    def _handle_hit(self, msg: bs.HitMessage):
        # Bots freeze runners on contact
        # Only process if source is a bot and target is player
        if not hasattr(msg.source, "player") and msg.source and msg.source.exists():
            # Check if source is a bot in our freezer list
            if msg.source in [b.actor.node for b in self._bots]:
                # msg.hit_type might be "punch"
                victim_node = msg.target
                victim_player = None
                # Find player of victim_node
                for player in self.players:
                    if player.exists() and player.actor and player.actor.node == victim_node:
                        victim_player = player
                        break
                if victim_player is not None and not getattr(victim_player, "frozen", False):
                    self._freeze_player(victim_player)

        # Allow unfreeze by player touch
        if hasattr(msg.source, "player") and hasattr(msg.target, "player"):
            source_player = msg.source.player
            target_player = msg.target.player
            if source_player is not None and target_player is not None:
                if getattr(target_player, "frozen", False) and source_player.team == target_player.team:
                    self._unfreeze_player(target_player)

    def _freeze_player(self, player):
        player.frozen = True
        node = player.actor.node
        node.handlemessage(bs.DieMessage())  # temporarily kill and respawn frozen animation?
        # Actually better to disable movement and actions
        node.invincible = True
        node.punch_power = 0
        node.can_punch = False
        node.move_up = 0
        node.move_down = 0
        node.move_left = 0
        node.move_right = 0
        node.velocity = (0, 0, 0)
        node.handlemessage("freeze")
        bs.screenmessage(f"{player.getname()} got frozen!", color=(0, 0.5, 1))
        # Show some ice effect? Optional

    def _unfreeze_player(self, player):
        player.frozen = False
        node = player.actor.node
        node.invincible = False
        node.punch_power = 1
        node.can_punch = True
        bs.screenmessage(f"{player.getname()} was unfrozen!", color=(0, 1, 0))

    def _check_for_win(self):
        teams_alive = []
        for team in self.teams:
            if any(player.exists() and not getattr(player, "frozen", False) for player in team.players):
                teams_alive.append(team)
        if len(teams_alive) == 1:
            bs.screenmessage(f"Team {teams_alive[0].get_team_name()} wins!")
            self.end_game()

    def _on_round_end(self):
        # Check teams with unfrozen players
        teams_alive = []
        for team in self.teams:
            if any(player.exists() and not getattr(player, "frozen", False) for player in team.players):
                teams_alive.append(team)
        if len(teams_alive) == 1:
            bs.screenmessage(f"Team {teams_alive[0].get_team_name()} wins by surviving!")
        else:
            bs.screenmessage("Round ended with no winner.")
        self.end_game()

    def _update(self):
        # Periodically update bot AI to chase nearest runner
        for bot in self._bots:
            if bot.exists():
                nearest_player = None
                nearest_dist = 9999
                bot_pos = bot.actor.node.position
                for player in self.players:
                    if player.exists() and not getattr(player, "frozen", False):
                        p_pos = player.actor.node.position
                        dist = ((bot_pos[0] - p_pos[0])**2 + (bot_pos[1] - p_pos[1])**2 + (bot_pos[2] - p_pos[2])**2)**0.5
                        if dist < nearest_dist:
                            nearest_dist = dist
                            nearest_player = player
                if nearest_player:
                    bot.actor.node.move_towards(nearest_player.actor.node.position, 1.0)
        bs.Timer(1000, self._update)

def bs_get():
    return FrozenTagGame
