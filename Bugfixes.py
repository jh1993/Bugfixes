from Spells import *
from Upgrades import *
from Level import *
from Shrines import *
from Mutators import *
from CommonContent import *
from Consumables import *
from Monsters import *
from RareMonsters import *
from Variants import *
from RiftWizard import *

import CommonContent, Spells

import sys
curr_module = sys.modules[__name__]

def push(target, source, squares):
    dir_x = target.x - source.x
    dir_y = target.y - source.y

    mag_sq = dir_x * dir_x + dir_y * dir_y
    mag = math.sqrt(mag_sq)

    dir_x = dir_x / mag
    dir_y = dir_y / mag

    dest_x = round(target.x + 3*squares*dir_x)
    dest_y = round(target.y + 3*squares*dir_y)

    return pull(target, Point(dest_x, dest_y), squares, find_clear=False)

class RemoveBuffOnPreAdvance(Buff):

    def __init__(self, buff_class):
        self.buff_class = buff_class
        Buff.__init__(self)
        self.buff_type = BUFF_TYPE_PASSIVE
        self.stack_type = STACK_INTENSITY
    
    def on_attempt_apply(self, owner):
        for buff in owner.buffs:
            if isinstance(buff, RemoveBuffOnPreAdvance) and buff.buff_class == self.buff_class:
                return False
        return True

    def on_pre_advance(self):
        self.owner.remove_buff(self)

    def on_unapplied(self):
        for unit in list(self.owner.level.units):
            for buff in list(unit.buffs):
                if isinstance(buff, self.buff_class):
                    if hasattr(buff, "applier") and buff.applier is not self.owner:
                        continue
                    unit.remove_buff(buff)

class EventOnPreDamagedPenetration:
    def __init__(self, evt, penetration):
        self.unit = evt.unit
        self.damage = evt.damage
        self.damage_type = evt.damage_type
        self.source = evt.source
        self.penetration = penetration

class EventOnDamagedPenetration:
    def __init__(self, evt, penetration):
        self.unit = evt.unit
        self.damage = evt.damage
        self.damage_type = evt.damage_type
        self.source = evt.source
        self.penetration = penetration

class MinionBuffAura(Buff):

    def __init__(self, buff_class, qualifies, name, minion_desc):
        Buff.__init__(self)
        self.buff_class = buff_class
        self.qualifies = qualifies
        self.name = name
        example = self.buff_class()
        self.description = "All %s you summon gain %s for a duration equal to this buff's remaining duration." % (minion_desc, example.name)
        self.color = example.color
        self.global_triggers[EventOnUnitAdded] = self.on_unit_added
        self.buff_dict = defaultdict(lambda: None)

    def modify_unit(self, unit, duration):

        if are_hostile(self.owner, unit) or (unit is self.owner):
            return
        if not self.qualifies(unit):
            return
        
        if not unit.is_alive() and unit in self.buff_dict.keys():
            self.buff_dict.pop(unit)
            return

        if unit not in self.buff_dict.keys() or not self.buff_dict[unit] or not self.buff_dict[unit].applied:
            buff = self.buff_class()
            unit.apply_buff(buff, duration)
            self.buff_dict[unit] = buff

    def on_unit_added(self, evt):
        self.modify_unit(evt.unit, self.turns_left - 1)
    
    def on_advance(self):
        for unit in list(self.buff_dict.keys()):
            if not unit.is_alive():
                self.buff_dict.pop(unit)
        for unit in list(self.owner.level.units):
            self.modify_unit(unit, self.turns_left)

def raise_skeleton(owner, unit, source=None, summon=True):
    if unit.has_been_raised:
        return

    if Tags.Living not in unit.tags:
        return

    unit.has_been_raised = True

    skeleton = Unit()
    skeleton.name = "Skeletal %s" % unit.name
    skeleton.sprite.char = 's'
    if unit.max_hp >= 40:
        skeleton.sprite.char = 'S'
    skeleton.sprite.color = Color(201, 213, 214)
    skeleton.max_hp = unit.max_hp
    skeleton.spells.append(SimpleMeleeAttack(5))
    skeleton.tags.append(Tags.Undead)
    skeleton.stationary = unit.stationary
    skeleton.team = owner.team
    skeleton.flying = unit.flying
    skeleton.source = source

    if not summon:
        return skeleton

    p = unit.level.get_summon_point(unit.x, unit.y, flying=unit.flying)
    if p:
        owner.level.summon(owner=owner, unit=skeleton, target=p)
        return skeleton
    else:
        return None

class FrostbittenBuff(Buff):

    def __init__(self, upgrade):
        Buff.__init__(self)

        self.upgrade = upgrade
        self.name = "Frostbitten"
        self.buff_type = BUFF_TYPE_PASSIVE
        self.owner_triggers[EventOnBuffRemove] = self.on_unfreeze

    def on_unfreeze(self, evt):
        if isinstance(evt.buff, FrozenBuff):
            self.owner.remove_buff(self)

    def on_advance(self):
        self.owner.deal_damage(self.upgrade.get_stat('damage'), Tags.Dark, self.upgrade)

WizardSwap.can_threaten = lambda self, x, y: False

GrantSorcery.can_threaten = lambda self, x, y: False

GeminiCloneSpell.can_threaten = lambda self, x, y: False

TreeThornSummon.can_threaten = lambda self, x, y: False

TombstoneSummon.can_threaten = lambda self, x, y: False

RedRiderBerserkingSpell.can_threaten = lambda self, x, y: self.caster.level.can_see(self.caster.x, self.caster.y, x, y)

HagDrain.can_threaten = lambda self, x, y: self.caster.level.can_see(self.caster.x, self.caster.y, x, y)

SimpleCurse.can_threaten = lambda self, x, y: Spell.can_cast(self, x, y)

JackolanternSpell.can_threaten = lambda self, x, y: False

VolcanoTurtleBuff.can_threaten = lambda self, x, y: distance(Point(x, y), self.owner) <= 8

GoatHeadBray.can_threaten = lambda self, x, y: False

PhoenixBuff.can_threaten = lambda self, x, y: distance(Point(x, y), self.owner) <= 6

ArcanePhoenixBuff.can_threaten = lambda self, x, y: distance(Point(x, y), self.owner) <= 6

class RotBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)

    def on_init(self):
        self.color = Tags.Undead.color
        self.name = "Hollow Flesh"
        self.asset = ['status', 'rot']
        self.buff_type = BUFF_TYPE_CURSE
        self.frac = 1 - self.spell.get_stat('max_health_loss')/100
        self.resists[Tags.Dark] = 100
        self.resists[Tags.Holy] = -100
        self.resists[Tags.Fire] = -self.spell.get_stat('fire_vulnerability')
        self.resists[Tags.Heal] = 100
        self.originally_living = False
        self.originally_undead = False

    def on_applied(self, owner):
        self.owner.max_hp = math.floor(self.owner.max_hp*self.frac)
        self.owner.max_hp = max(self.owner.max_hp, 1)
        self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)
        if Tags.Living in self.owner.tags:
            self.owner.tags.remove(Tags.Living)
            self.originally_living = True
        if Tags.Undead in self.owner.tags:
            self.originally_undead = True
        else:
            self.owner.tags.append(Tags.Undead)
    
    def on_unapplied(self):
        self.owner.max_hp = math.ceil(self.owner.max_hp/self.frac)
        if not self.originally_undead and Tags.Undead in self.owner.tags:
            self.owner.tags.remove(Tags.Undead)
        if self.originally_living and Tags.Living not in self.owner.tags:
            self.owner.tags.append(Tags.Living)

def fix_unit(unit):
    if unit.name in bugged_units_fixer.keys():
        if hasattr(unit, "fixed"):
            return
        bugged_units_fixer[unit.name](unit)
        unit.fixed = True

set_asset = lambda unit, asset: setattr(unit, "asset_name", asset)

fix_copper_unit = lambda unit: unit.tags.append(Tags.Lightning)

fix_furnace_unit = lambda unit: unit.tags.append(Tags.Fire)

def fix_vampire_bat(unit):
    if unit.is_coward:
        unit.name = "Vampire Bat"
        unit.tags = [Tags.Dark, Tags.Undead]
        unit.spells = []

def fix_glass_mushboom_desc(unit):
    # Don't change player-summoned glass mushbooms in my Underused Options mod that doesn't use onhit
    if unit.spells[0].onhit:
        unit.spells[0].description = "Applies 2 turns of glassify"

def fix_bloodghast_desc(unit):
    # Don't change player-summoned bloodghasts in my Missing Synergies mod
    if unit.team == TEAM_ENEMY:
        unit.spells[0].description = "Gain +1 damage for 10 turns with each attack"

def fix_giant_worm_ball(unit):
    def summon_worms(caster, target):
        worms = WormBall(5)
        worms.team = caster.team
        worms.source = caster.source
        p = caster.level.get_summon_point(target.x, target.y, 1.5)
        if p:
            caster.level.add_obj(worms, p.x, p.y)
    unit.spells[0].onhit = summon_worms

bugged_units_fixer = {
    "Swamp Queen": lambda unit: setattr(unit.spells[2], "onhit", lambda caster, target: target.apply_buff(Poison(), 4)),
    "Slimesoul Idol": lambda unit: set_asset(unit, "slimesoul_idol"),
    "Crucible of Pain": lambda unit: set_asset(unit, "crucible_of_pain_idol"),
    "Idol of Fiery Vengeance": lambda unit: set_asset(unit, "fiery_vengeance_idol"),
    "Concussive Idol": lambda unit: set_asset(unit, "concussive_idol"),
    "Idol of Vampirism": lambda unit: set_asset(unit, "vampirism_idol"),
    "Hallowed Earth Elemental": lambda unit: setattr(unit, "tags", [Tags.Elemental, Tags.Holy]),
    "Copper Spider": fix_copper_unit,
    "Furnace Spider": fix_furnace_unit,
    "Copper Mantis": fix_copper_unit,
    "Furnace Mantis": fix_furnace_unit,
    "Copper Spike Ball": fix_copper_unit,
    "Bat": fix_vampire_bat,
    "Bloodghast": fix_bloodghast_desc,
    "Ash Imp": lambda unit: setattr(unit.spells[0], "damage_type", [Tags.Fire, Tags.Dark, Tags.Poison]),
    "Glass Mushboom": fix_glass_mushboom_desc,
    "Frostfire Tormentor": lambda unit: setattr(unit.spells[1], "description", "Applies frozen for 1 turn"),
    "Deathchill Tormentor": lambda unit: setattr(unit.spells[0], "description", "Applies frozen for 1 turn"),
    "Giant Worm Ball": fix_giant_worm_ball
}

class OakenBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.resists[Tags.Physical] = 50
        self.resists[Tags.Holy] = 50

class TundraBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.resists[Tags.Ice] = 50

class SwampBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.resists[Tags.Poison] = 100

class SandstoneBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.resists[Tags.Physical] = 50
        self.resists[Tags.Fire] = 50

class BlueSkyBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.resists[Tags.Lightning] = 100

class NaturalVigorBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.resists[Tags.Fire] = 25
        self.resists[Tags.Ice] = 25
        self.resists[Tags.Lightning] = 25
        self.resists[Tags.Physical] = 25

def modify_class(cls):

    if cls is Frostbite:

        def on_init(self):
            self.name = "Frostbite"
            self.level = 6
            self.tags = [Tags.Ice, Tags.Dark]
            self.damage = 7
            self.global_triggers[EventOnBuffApply] = lambda evt: on_buff_apply(self, evt)

        def on_buff_apply(self, evt):
            if not isinstance(evt.buff, FrozenBuff):
                return
            if not are_hostile(self.owner, evt.unit):
                return
            evt.unit.apply_buff(curr_module.FrostbittenBuff(self))
        
        on_advance = lambda self: None

    if cls is MercurialVengeance:

        def on_init(self):
            self.owner_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Metallic.color
            self.description = "The killer of this unit is inflicted with Mercurize."

        def on_death(self, evt):
            if evt.damage_event and evt.damage_event.source and evt.damage_event.source.owner:
                evt.damage_event.source.owner.apply_buff(MercurizeBuff(self.spell), self.spell.get_stat("duration"))

    if cls is ThunderStrike:

        def cast(self, x, y):

            in_cloud = isinstance(self.caster.level.tiles[x][y].cloud, StormCloud)
            duration = self.get_stat('duration')
            radius = self.get_stat('radius')
            if in_cloud and self.get_stat('storm_power'):
                duration = self.get_stat('duration') * 2
                radius = radius * 2

            self.caster.level.deal_damage(x, y, self.get_stat('damage'), self.damage_type, self)
            yield

            if self.get_stat('heaven_strike'):
                for i in range(3):
                    yield

                self.caster.level.deal_damage(x, y, self.get_stat('damage'), Tags.Holy, self)

            for stage in Burst(self.caster.level, Point(x, y), radius):
                for point in stage:

                    self.caster.level.flash(point.x, point.y, Tags.Physical.color)
                    cur_target = self.caster.level.get_unit_at(point.x, point.y)
                    if cur_target and self.caster.level.are_hostile(cur_target, self.caster):
                        cur_target.apply_buff(Stun(), duration)
                yield

    if cls is HealAlly:

        def __init__(self, heal, range, tag=None):
            Spell.__init__(self)
            self.name = "Heal Ally"
            self.heal = heal
            self.range = range
            self.tag = tag

        def get_description(self):
            if self.tag:
                return "Heals one %s ally for %d" % (self.tag.name, self.heal)
            return "Heals an ally for %d" % self.heal

        def get_ai_target(self):
            units_in_range = self.caster.level.get_units_in_ball(Point(self.caster.x, self.caster.y), self.get_stat("range"))
            units_in_range = [u for u in units_in_range if not self.caster.level.are_hostile(self.caster, u)]
            units_in_range = [u for u in units_in_range if self.can_cast(u.x, u.y)]
            units_in_range = [u for u in units_in_range if not u.is_player_controlled]

            if self.tag:
                units_in_range = [u for u in units_in_range if self.tag in u.tags]

            wounded_units = [u for u in units_in_range if u.cur_hp < u.max_hp and u.resists[Tags.Heal] < 100]
            if wounded_units:
                target = random.choice(wounded_units)
                return Point(target.x, target.y)
            else:
                return None

    if cls is AetherDaggerSpell:

        def get_impacted_tiles(self, x, y):
            for u in self.owner.level.get_units_in_los(self.caster):
                if are_hostile(u, self.caster):
                    shown = False
                    for t in u.resists:
                        if t == Tags.Heal:
                            continue
                        if u.resists[t] > 0:
                            yield u

        def cast_instant(self, x, y):
            for u in self.owner.level.get_units_in_los(self.caster):
                if are_hostile(u, self.caster):
                    shown = False
                    for t in u.resists:
                        if u.resists[t] > 0:
                            if t == Tags.Heal:
                                continue
                            u.resists[t] = 0
                            if not shown:
                                self.owner.level.show_effect(u.x, u.y, Tags.Arcane)
                                shown = True

    if cls is OrbBuff:

        def on_advance(self):
            # first advance: Radiate around self, do not move
            if self.first:
                self.first = False
                self.spell.on_orb_move(self.owner, self.owner)

            path = None
            if not self.spell.get_stat('melt_walls'):
                path = self.owner.level.find_path(self.owner, self.dest, self.owner, pythonize=True)
            else:
                path = self.owner.level.get_points_in_line(self.owner, self.dest)[1:]
            next_point = None
            if path:
                next_point = path[0]

            # Melt wall if needed
            if next_point and self.owner.level.tiles[next_point.x][next_point.y].is_wall() and self.spell.get_stat('melt_walls'):
                self.owner.level.make_floor(next_point.x, next_point.y)

            # otherwise- try to move one space foward
            if next_point and self.owner.level.can_move(self.owner, next_point.x, next_point.y, teleport=True):
                self.owner.level.act_move(self.owner, next_point.x, next_point.y, teleport=True)
                self.spell.on_orb_move(self.owner, next_point)
            else:
                self.spell.on_orb_move(self.owner, self.owner)

            # Do not destroy the orb if there is no path, otherwise the orb disappears if surrounded
            # Only destroy the orb when it reaches its destination
            if self.owner.x == self.dest.x and self.owner.y == self.dest.y:
                self.owner.kill()

    if cls is PyGameView:

        def get_anim(self, unit, forced_name=None):

            # Find the asset name
            if forced_name:
                asset = ["char", forced_name]
            else:
                asset = get_unit_asset(unit)

            # Determine lair colors for lairs
            lair_colors = None
            if unit.is_lair:
                example_monster = unit.buffs[0].example_monster
                example_sprite_name = example_monster.get_asset_name()
                example_sprite = self.get_sprite_sheet(get_unit_asset(example_monster))
                lair_colors = example_sprite.get_lair_colors()

            sprite = self.get_sprite_sheet(asset, lair_colors=lair_colors)

            return UnitSprite(unit, sprite, view=self)

        def draw_wrapped_string(self, string, surface, x, y, width, color=(255, 255, 255), center=False, indent=False, extra_space=False):
            lines = string.split('\n')

            cur_x = x
            cur_y = y
            linesize = self.linesize
            num_lines = 0

            char_width = self.font.size('w')[0]
            chars_per_line = width // char_width
            for line in lines:
                #words = line.split(' ')
                # This regex separates periods, spaces, commas, and tokens
                exp = '[\[\]:|\w\|\'|%|-]+|.| |,'
                words = re.findall(exp, line)
                words.reverse()
                chars_left = chars_per_line

                # Start each line all the way to the left
                cur_x = x
                assert(all(len(word) < chars_per_line) for word in words)

                while words:
                    cur_color = color

                    word = words.pop()
                    if word != ' ':

                        # Process complex tooltips- strip off the []s and look up the color
                        if word and word[0] == '[' and word[-1] == ']':
                            tokens = word[1:-1].split(':')
                            if len(tokens) == 1:
                                word = tokens[0] # todo- fmt attribute?
                                cur_color = tooltip_colors[word.lower()].to_tup()
                            elif len(tokens) == 2:
                                word = tokens[0]
                                cur_color = tooltip_colors[tokens[1].lower()].to_tup()

                        sub_words = word.split("_")
                        num_sub_words = len(sub_words)
                        n = 1
                        for sub_word in sub_words:
                            max_size = chars_left if sub_word in [' ', '.', ','] else chars_left - 1
                            if len(sub_word) > max_size:
                                cur_y += linesize
                                num_lines += 1
                                # Indent by one for next line
                                cur_x = x + char_width
                                chars_left = chars_per_line

                            self.draw_string(sub_word, surface, cur_x, cur_y, cur_color, content_width=width)
                            cur_x += (len(sub_word)) * char_width
                            chars_left -= len(sub_word)
                            if n < num_sub_words:
                                cur_x += char_width
                                chars_left -= 1
                            n += 1
                    else:
                        cur_x += char_width
                        chars_left -= 1

                cur_y += linesize
                num_lines += 1
                if extra_space:
                    cur_y += linesize
                    num_lines += 1

            return num_lines

        def choose_spell(self, spell):
            if spell.show_tt:
                self.examine_target = spell

            if self.deploy_target:
                self.play_sound("menu_abort")
                return

            if not spell.can_pay_costs():
                self.play_sound("menu_abort")
                self.cast_fail_frames = SPELL_FAIL_LOCKOUT_FRAMES
                return

            prev_spell = self.cur_spell
            self.cur_spell = spell

            def can_tab_target(t):
                unit = self.game.cur_level.get_unit_at(t.x, t.y)
                if unit is None:
                    return False
                return are_hostile(self.game.p1, unit)  

            self.play_sound("menu_confirm")
            #p = self.get_mouse_level_point()
            #if p and spell.can_cast(*p):
            #   self.cur_spell_target = p
            self.targetable_tiles = spell.get_targetable_tiles()
            if hasattr(spell, 'get_tab_targets'):
                self.tab_targets = spell.get_tab_targets()
            else:
                self.tab_targets = [t for t in self.cur_spell.get_targetable_tiles() if can_tab_target(t)]
                self.tab_targets.sort(key=lambda t: distance(t, self.game.p1))

            self.tab_targets = [Point(t.x, t.y) if not isinstance(t, Point) else t for t in self.tab_targets]

            if self.options['smart_targeting']:
                # If the unit we last targeted is dead, dont target the empty space where it died
                if isinstance(self.cur_spell_target, Unit):
                    if not self.cur_spell_target.is_alive():
                        self.cur_spell_target = None

                # If we dont have a target, target the first tab target option if it exists
                if not self.cur_spell_target:
                    if self.tab_targets:
                        self.cur_spell_target = self.tab_targets[0]
                    else:
                        self.cur_spell_target = Point(self.game.p1.x, self.game.p1.y)
            else:
                if not prev_spell:
                    self.cur_spell_target = Point(self.game.p1.x, self.game.p1.y)

        def draw_examine_spell(self):

            self.draw_examine_icon()

            border_margin = self.border_margin
            cur_x = border_margin 
            cur_y = border_margin
            linesize = self.linesize

            spell = self.examine_target
            self.draw_string(spell.name, self.examine_display, cur_x, cur_y)
            cur_y += linesize
            cur_y += linesize
            tag_x = cur_x
            for tag in Tags:
                if tag not in spell.tags:
                    continue
                self.draw_string(tag.name, self.examine_display, tag_x, cur_y, (tag.color.r, tag.color.g, tag.color.b))
                cur_y += linesize
            cur_y += linesize

            if spell.level:
                self.draw_string("Level %d" % spell.level, self.examine_display, cur_x, cur_y)
                cur_y += linesize

            if spell.melee:
                self.draw_string("Melee Range", self.examine_display, cur_x, cur_y)
                cur_y += self.linesize
            elif spell.range:
                fmt = "Range %d" % spell.get_stat('range')
                if not spell.get_stat("requires_los"):
                    fmt += " (Ignores LOS)"
                self.draw_string(fmt, self.examine_display, cur_x, cur_y)
                cur_y += self.linesize

            if spell.max_charges:
                self.draw_string("Charges: %d/%d " % (self.examine_target.cur_charges, self.examine_target.get_stat('max_charges')), self.examine_display, cur_x, cur_y)
                cur_y += self.linesize

            cur_y += linesize

            lines = self.draw_wrapped_string(spell.get_description(), self.examine_display, cur_x, cur_y, self.examine_display.get_width() - 2*self.border_margin, extra_space=True)
            cur_y += linesize * lines

            if spell.spell_upgrades:
                self.draw_string("Upgrades:", self.examine_display, cur_x, cur_y)
                cur_y += linesize

                for upg in spell.spell_upgrades:

                    cur_color = (255, 255, 255)
                    if self.game.has_upgrade(upg):
                        cur_color = (0, 255, 0)

                    self.draw_string('%d - %s' % (upg.level, upg.name), self.examine_display, cur_x, cur_y, color=cur_color)
                    cur_y += linesize

        def draw_pick_trial(self):

            num_modded_trials = len(all_trials) - 13
            shift_down = min(num_modded_trials, 5)
            shift_up = 0
            if num_modded_trials > 5:
                shift_up = num_modded_trials - 5

            rect_w = max(self.font.size(trial.name)[0] for trial in all_trials)
            cur_x = self.screen.get_width() // 2 - rect_w // 2
            cur_y = self.screen.get_height() // 2 - self.linesize * (4 + shift_up)

            cur_color = (255, 255, 255)
            for trial in all_trials:
                self.draw_string(trial.name, self.screen, cur_x, cur_y, cur_color, mouse_content=trial, content_width=rect_w)
                if SteamAdapter.get_trial_status(trial.name):
                    self.draw_string("*", self.screen, cur_x - 16, cur_y, COLOR_VICTORY)
                cur_y += self.linesize

            cur_y += self.linesize * (10 - shift_down)

            if isinstance(self.examine_target, Trial):
                desc = self.examine_target.get_description()
                for line in desc.split('\n'):
                    cur_x = (self.screen.get_width() // 2) - (self.font.size(line)[0] // 2)
                    self.draw_string(line, self.screen, cur_x, cur_y)
                    cur_y += self.linesize

        def draw_level(self):
            if self.gameover_frames >= 8:
                return

            level = self.get_display_level()
            self.level_display.fill((0, 0, 0))
            
            #Transform and drain the levels effects
            to_remove = []
            for effect in level.effects:
                if not hasattr(effect, 'graphic'):
                    graphic = self.get_effect(effect)
                    if not graphic:
                        to_remove.append(effect)
                        continue

                    effect.graphic = graphic
                    graphic.level_effect = effect
                    # Queue buff effects, instantly play other effects

                    # Damage effects can replace damage effects
                    # Buff effects queue after everything
                    # Damage effects queue after buff effects

                    queued_colors = [
                        Tags.Buff_Apply.color,
                        Tags.Debuff_Apply.color,
                        Tags.Shield_Apply.color,
                        Tags.Shield_Expire.color,
                    ]
                    if hasattr(effect, 'color') and effect.color in queued_colors:
                        self.queue_effect(graphic)
                    else:
                        self.effects.append(graphic)
                    
            # Kill sound effects
            for effect in to_remove:
                level.effects.remove(effect)

            # Draw the board
            self.advance_queued_effects()

            effect_tiles = set()
            for e in self.effects:
                effect_tiles.add((e.x, e.y))

            if hasattr(self.examine_target, 'level') and hasattr(self.examine_target, 'x') and hasattr(self.examine_target, 'y'):
                if isinstance(self.examine_target, Unit) and self.examine_target.cur_hp > 0:

                    if self.examine_target.has_buff(Soulbound):
                        b = self.examine_target.get_buff(Soulbound)

                        rect = (b.guardian.x * SPRITE_SIZE, b.guardian.y * SPRITE_SIZE, SPRITE_SIZE, SPRITE_SIZE)
                        color = (60, 0, 0)
                        pygame.draw.rect(self.level_display, color, rect)

                    if self.examine_target.has_buff(ChannelBuff):
                        b = self.examine_target.get_buff(ChannelBuff)

                        rect = (b.spell_target.x * SPRITE_SIZE, b.spell_target.y * SPRITE_SIZE, SPRITE_SIZE, SPRITE_SIZE)
                        color = (60, 0, 0)
                        # TODO- red target circle(or green if ally) instead of grey background block
                        # TODO- all impacted tiles of target
                        pygame.draw.rect(self.level_display, color, rect)

            if self.game.next_level:
                self.deploy_anim_frames += 1
                self.deploy_anim_frames = min(self.deploy_anim_frames, self.get_max_deploy_frames())
            elif self.game.prev_next_level and self.deploy_anim_frames > 0:
                self.deploy_anim_frames -= 1

            def get_level(i, j):
                if not self.deploy_anim_frames:
                    return self.game.cur_level

                cur_radius = DEPLOY_SPEED*self.deploy_anim_frames
                if abs(i-self.game.p1.x) + abs(j-self.game.p1.y) > cur_radius:
                    return self.game.cur_level
                else:
                    return self.game.next_level or self.game.prev_next_level


            for i in range(0, LEVEL_SIZE):
                for j in range(0, LEVEL_SIZE):

                    level = get_level(i, j)

                    tile = level.tiles[i][j]
                    
                    should_draw_tile = True
                    if tile.unit and not tile.is_chasm:
                        should_draw_tile = hasattr(tile.unit, "invisible") and tile.unit.invisible
                    if tile.prop:
                        should_draw_tile = False
                    if should_draw_tile:
                        partial_occulde = tile.unit or (i, j) in effect_tiles
                        self.draw_tile(tile, partial_occulde=partial_occulde)

                    if self.examine_target and (self.examine_target in [tile.unit, tile.cloud, tile.prop]):
                            if self.examine_target is not tile.unit or not hasattr(tile.unit, "invisible") or not tile.unit.invisible:
                                rect = (self.examine_target.x * SPRITE_SIZE, self.examine_target.y * SPRITE_SIZE, SPRITE_SIZE, SPRITE_SIZE)
                                color = (60, 60, 60)
                                pygame.draw.rect(self.level_display, color, rect)
        
            for i in range(0, LEVEL_SIZE):
                for j in range(0, LEVEL_SIZE):

                    level = get_level(i, j)

                    tile = level.tiles[i][j]
                    
                    if tile.unit:
                        if not hasattr(tile.unit, "invisible") or not tile.unit.invisible:
                            self.draw_unit(tile.unit)
                        if tile.cloud:
                            self.draw_cloud(tile.cloud)
                        elif hasattr(tile.unit, "invisible") and tile.unit.invisible and tile.prop and(i, j) not in effect_tiles:
                            self.draw_prop(tile.prop)
                    elif tile.cloud:
                        self.draw_cloud(tile.cloud)
                    elif tile.prop and(i, j) not in effect_tiles:
                        self.draw_prop(tile.prop)

            # Draw LOS if requested
            keys = pygame.key.get_pressed()
            if any(k and keys[k] for k in self.key_binds[KEY_BIND_LOS]):
                self.draw_los()
            # Draw targeting if a spell is chosen
            if self.cur_spell:    
                self.draw_targeting()
            # Draw threat if requested
            if any(k and keys[k] for k in self.key_binds[KEY_BIND_THREAT]) and self.game.is_awaiting_input():
                self.draw_threat()

            if isinstance(self.examine_target, Unit):
                buff = self.examine_target.get_buff(OrbBuff)
                if buff and buff.dest:
                    dest = buff.dest
                    rect = (dest.x * SPRITE_SIZE, dest.y * SPRITE_SIZE, SPRITE_SIZE, SPRITE_SIZE)
                    self.level_display.blit(self.hostile_los_image, (dest.x * SPRITE_SIZE, dest.y * SPRITE_SIZE))

            for e in self.effects:
                self.draw_effect(e)

            for e in self.effects:
                if e.finished:
                    if hasattr(e, 'level_effect'):
                        # Sometimes this will fail if you transfer to the next level
                        # Whatever (itll be garbage collected with the level anyway)
                        if e.level_effect in self.game.cur_level.effects:
                            self.game.cur_level.effects.remove(e.level_effect)
                        elif self.game.next_level and e.level_effect in self.game.next_level.effects:
                            self.game.next_level.effects.remove(e.level_effect)

            self.effects = [e for e in self.effects if not e.finished]

            # Draw deploy
            if self.game.deploying and self.deploy_target:
                image = get_image(["UI", "deploy_ok_animated"]) if level.can_stand(self.deploy_target.x, self.deploy_target.y, self.game.p1) else get_image(["UI", "deploy_no_animated"])
                deploy_frames = image.get_width() // SPRITE_SIZE
                deploy_frame = idle_frame % deploy_frames
                self.level_display.blit(image, (self.deploy_target.x * SPRITE_SIZE, self.deploy_target.y * SPRITE_SIZE), (deploy_frame * SPRITE_SIZE, 0, SPRITE_SIZE, SPRITE_SIZE))

            # Blit to main screen
            pygame.transform.scale(self.whole_level_display, (self.screen.get_width(), self.screen.get_height()), self.screen)

        def draw_character(self):

            self.draw_panel(self.character_display)

            self.char_panel_examine_lines = {}

            cur_x = self.border_margin
            cur_y = self.border_margin
            linesize = self.linesize

            hpcolor = (255, 255, 255)
            if self.game.p1.cur_hp <= 25:
                hpcolor = (255, 0, 0)

            self.draw_string("%s %d/%d" % (CHAR_HEART, self.game.p1.cur_hp, self.game.p1.max_hp), self.character_display, cur_x, cur_y, color=hpcolor)
            self.draw_string("%s" % CHAR_HEART, self.character_display, cur_x, cur_y, (255, 0, 0))
            cur_y += linesize

            if self.game.p1.shields:
                self.draw_string("%s %d" % (CHAR_SHIELD, self.game.p1.shields), self.character_display, cur_x, cur_y)
                self.draw_string("%s" % (CHAR_SHIELD), self.character_display, cur_x, cur_y, color=COLOR_SHIELD.to_tup())
                cur_y += linesize

            self.draw_string("SP %d" % self.game.p1.xp, self.character_display, cur_x, cur_y, color=COLOR_XP)
            cur_y += linesize

            self.draw_string("Realm %d" % self.game.level_num, self.character_display, cur_x, cur_y)
            cur_y += linesize

            # TODO- buffs here

            cur_y += linesize

            self.draw_string("Spells:", self.character_display, cur_x, cur_y)
            cur_y += linesize

            # Spells
            index = 1
            for spell in self.game.p1.spells:

                
                spell_number = (index) % 10
                mod_key = 'C' if index > 20 else 'S' if index > 10 else ''
                hotkey_str = "%s%d" % (mod_key, spell_number)

                if spell == self.cur_spell:
                    cur_color = (0, 255, 0)
                elif spell.can_pay_costs():
                    cur_color = (255, 255, 255)
                else:
                    cur_color = (128, 128, 128)
                
                fmt = "%2s  %-17s%2d" % (hotkey_str, spell.name, spell.cur_charges)

                self.draw_string(fmt, self.character_display, cur_x, cur_y, cur_color, mouse_content=SpellCharacterWrapper(spell), char_panel=True)
                self.draw_spell_icon(spell, self.character_display, cur_x + 38, cur_y)

                cur_y += linesize
                index += 1

            cur_y += linesize
            # Items

            self.draw_string("Items:", self.character_display, cur_x, cur_y)
            cur_y += linesize
            index = 1
            for item in self.game.p1.items:

                hotkey_str = "A%d" % (index % 10)

                cur_color = (255, 255, 255)
                if item.spell == self.cur_spell:
                    cur_color = (0, 255, 0)
                fmt = "%2s  %-17s%2d" % (hotkey_str, item.name, item.quantity)          

                self.draw_string(fmt, self.character_display, cur_x, cur_y, cur_color, mouse_content=item)
                self.draw_spell_icon(item, self.character_display, cur_x + 38, cur_y)

                cur_y += linesize
                index += 1

            # Buffs
            status_effects = [b for b in self.game.p1.buffs if b.buff_type != BUFF_TYPE_PASSIVE]
            counts = {}
            for effect in status_effects:
                if effect.name not in counts:
                    counts[effect.name] = (effect, 0, 0, None)
                _, stacks, duration, color = counts[effect.name]
                stacks += 1
                duration = max(duration, effect.turns_left)

                counts[effect.name] = (effect, stacks, duration, effect.get_tooltip_color().to_tup())

            if status_effects:
                cur_y += linesize
                self.draw_string("Status Effects:", self.character_display, cur_x, cur_y, (255, 255, 255))
                cur_y += linesize
                for buff_name, (buff, stacks, duration, color) in counts.items():

                    fmt = buff_name

                    if stacks > 1:
                        fmt += ' x%d' % stacks

                    if duration:
                        fmt += ' (%d)' % duration

                    self.draw_string(fmt, self.character_display, cur_x, cur_y, color, mouse_content=buff)
                    cur_y += linesize

            skills = [b for b in self.game.p1.buffs if isinstance(b, Upgrade) and not b.prereq]
            if skills:
                cur_y += linesize

                self.draw_string("Skills:", self.character_display, cur_x, cur_y)
                cur_y += linesize

                skill_x_max = self.character_display.get_width() - self.border_margin - 16
                for skill in skills:
                    self.draw_spell_icon(skill, self.character_display, cur_x, cur_y)
                    cur_x += 18
                    if cur_x > skill_x_max:
                        cur_x = self.border_margin
                        cur_y += self.linesize

            cur_x = self.border_margin
            cur_y = self.character_display.get_height() - self.border_margin - 3*self.linesize

            self.draw_string("Menu (ESC)", self.character_display, cur_x, cur_y, mouse_content=OPTIONS_TARGET)
            cur_y += linesize

            self.draw_string("How to Play (H)", self.character_display, cur_x, cur_y, mouse_content=INSTRUCTIONS_TARGET)
            cur_y += linesize

            color = self.game.p1.discount_tag.color.to_tup() if self.game.p1.discount_tag else (255, 255, 255)
            self.draw_string("Character Sheet (C)", self.character_display, cur_x, cur_y, color=color, mouse_content=CHAR_SHEET_TARGET)

            self.screen.blit(self.character_display, (0, 0))

        def draw_examine_unit(self):

            # If a game is running, do not display dead monsters or the player
            if self.game:
                if self.examine_target.cur_hp <= 0:
                    return

                if self.examine_target == self.game.p1:
                    return

            if self.state == STATE_SHOP and self.shop_type == SHOP_TYPE_BESTIARY:
                if not SteamAdapter.has_slain(self.examine_target.name):
                    return

            border_margin = self.border_margin
            cur_x = border_margin
            cur_y = border_margin
            linesize = self.linesize
            unit = self.examine_target

            lines = self.draw_wrapped_string(unit.name, self.examine_display, cur_x, cur_y, width=17*16)
            cur_y += (lines+1) * linesize

            if unit.team == TEAM_PLAYER:
                self.draw_string("Friendly", self.examine_display, cur_x, cur_y, Tags.Conjuration.color.to_tup())
                cur_y += linesize

            if unit.turns_to_death:
                self.draw_string("%d turns left" % unit.turns_to_death, self.examine_display, cur_x, cur_y)
                cur_y += linesize


            self.examine_icon_surface.fill((0, 0, 0))

            if not self.examine_target.Anim:
                self.examine_target.Anim = self.get_anim(self.examine_target)

            if self.examine_target.Anim:
                self.examine_target.Anim.draw(self.examine_icon_surface, True)

            subsurface = self.examine_display.subsurface((self.examine_display.get_width() - self.border_margin - 64, self.border_margin, 64, 64))
            pygame.transform.scale(self.examine_icon_surface, (64, 64), subsurface)


            self.draw_string("%s %d/%d" % (CHAR_HEART, unit.cur_hp, unit.max_hp), self.examine_display, cur_x, cur_y)
            self.draw_string("%s" % CHAR_HEART, self.examine_display, cur_x, cur_y, (255, 0, 0))
            cur_y += linesize
            
            if unit.shields:
                self.draw_string("%s %d" % (CHAR_SHIELD, unit.shields), self.examine_display, cur_x, cur_y)
                self.draw_string("%s" % (CHAR_SHIELD), self.examine_display, cur_x, cur_y, color=COLOR_SHIELD.to_tup())
                cur_y += linesize

            if unit.clarity:
                self.draw_string("%s %d" % (CHAR_CLARITY, unit.clarity), self.examine_display, cur_x, cur_y)
                self.draw_string("%s" % (CHAR_CLARITY), self.examine_display, cur_x, cur_y, color=COLOR_CLARITY)
                cur_y += linesize

            cur_y += linesize
            for tag in unit.tags:
                self.draw_string(tag.name, self.examine_display, cur_x, cur_y, (tag.color.r, tag.color.g, tag.color.b))
                cur_y += linesize

            cur_y += linesize
            for spell in unit.spells:
                if hasattr(spell, 'damage_type') and isinstance(spell.damage_type, Tag):
                    cur_color = spell.damage_type.color.to_tup()
                else:
                    cur_color = (255, 255, 255)

                fmt = "%s" % spell.name
                self.draw_string(fmt, self.examine_display, cur_x, cur_y, cur_color)
                cur_y += linesize
                hasattrs = False
                word = " and " if hasattr(spell, "all_damage_types") else " or "
                if hasattr(spell, 'damage'):
                    if hasattr(spell, 'damage_type') and isinstance(spell.damage_type, Tag):
                        fmt = ' %d %s damage' % (spell.get_stat('damage'), spell.damage_type.name)
                    elif hasattr(spell, 'damage_type') and isinstance(spell.damage_type, list):
                        fmt = ' %d %s damage' % (spell.get_stat('damage'), word.join([t.name for t in spell.damage_type]))
                    else:
                        fmt = ' %d damage' % spell.get_stat('damage')
                    lines = self.draw_wrapped_string(fmt, self.examine_display, cur_x, cur_y, self.examine_display.get_width() - 2*border_margin, color=COLOR_DAMAGE.to_tup())
                    cur_y += lines * linesize
                    hasattrs = True
                if spell.range > 1.5:
                    fmt = ' %d range' % spell.get_stat('range')
                    self.draw_string(fmt, self.examine_display, cur_x, cur_y, COLOR_RANGE.to_tup())
                    cur_y += linesize
                    hasattrs = True
                if hasattr(spell, 'radius') and spell.get_stat('radius') > 0:
                    fmt = ' %d radius' % spell.get_stat('radius')
                    self.draw_string(fmt, self.examine_display, cur_x, cur_y, attr_colors['radius'].to_tup())
                    cur_y += linesize
                    hasattrs = True
                if spell.cool_down > 0:
                    rem_cd = spell.caster.cool_downs.get(spell, 0)
                    if not rem_cd:
                        fmt = ' %d turn cooldown' % spell.cool_down
                    else:
                        fmt = ' %d turn cooldown (%d)' % (spell.cool_down, rem_cd)
                    self.draw_string(fmt, self.examine_display, cur_x, cur_y)
                    cur_y += linesize
                    hasattrs = True

                # Prioritize spell.description so it can be overriden
                desc = spell.description or spell.get_description()
                if desc:
                    indent = 16
                    lines = self.draw_wrapped_string(desc, self.examine_display, cur_x+16, cur_y, self.examine_display.get_width() - (indent+2*border_margin))
                    cur_y += lines*linesize
                cur_y += linesize

            if unit.flying:
                self.draw_string("Flying", self.examine_display, cur_x, cur_y)
                cur_y += linesize

            if unit.stationary:
                self.draw_string("Immobile", self.examine_display, cur_x, cur_y)
                cur_y += linesize

            if unit.flying or unit.stationary:
                cur_y += linesize

            resist_tags = [t for t in Tags if t in self.examine_target.resists and self.examine_target.resists[t] != 0]
            resist_tags.sort(key = lambda t: -self.examine_target.resists[t])

            for negative in [False, True]:
                has_resists = False
                for tag in resist_tags:
                    
                    if not ((self.examine_target.resists[tag] < 0) == negative):
                        continue

                    self.draw_string('%d%% Resist %s' % (self.examine_target.resists[tag], tag.name), self.examine_display, cur_x, cur_y, tag.color.to_tup())
                    has_resists = True
                    cur_y += self.linesize

                if has_resists:
                    cur_y += self.linesize

            # Unit Passives
            for buff in unit.buffs:
                if buff.buff_type != BUFF_TYPE_PASSIVE:
                    continue

                buff_desc = buff.get_tooltip()
                if not buff_desc:
                    continue

                buff_color = buff.get_tooltip_color()
                if not buff_color:
                    buff_color = Color(255, 255, 255)
                buff_color = (buff_color.r, buff_color.g, buff_color.b)


                lines = self.draw_wrapped_string(buff_desc, self.examine_display, cur_x, cur_y, self.examine_display.get_width() - 2*border_margin, buff_color)
                cur_y += linesize * (lines+1)

            cur_y += linesize

            status_effects = [b for b in self.examine_target.buffs if b.buff_type != BUFF_TYPE_PASSIVE]
            counts = {}
            for effect in status_effects:
                if effect.name not in counts:
                    counts[effect.name] = (effect, 0, 0, None)
                _, stacks, duration, color = counts[effect.name]
                stacks += 1
                duration = max(duration, effect.turns_left)

                counts[effect.name] = (effect, stacks, duration, effect.get_tooltip_color().to_tup())


            if status_effects:
                cur_y += linesize
                self.draw_string("Status Effects:", self.examine_display, cur_x, cur_y, (255, 255, 255))
                cur_y += linesize
                for buff_name, (buff, stacks, duration, color) in counts.items():

                    fmt = buff_name

                    if stacks > 1:
                        fmt += ' x%d' % stacks

                    if duration:
                        fmt += ' (%d)' % duration

                    self.draw_string(fmt, self.examine_display, cur_x, cur_y, color, mouse_content=buff)
                    cur_y += linesize

        def move_examine_target(self, movedir):
            # if is spell that has upgrades
            if isinstance(self.examine_target, Spell) and self.examine_target.spell_upgrades:
                if movedir == 1:
                    self.examine_target = self.examine_target.spell_upgrades[0]
                else:
                    self.examine_target = self.examine_target.spell_upgrades[-1]
            # if it is a spell upgrade
            elif hasattr(self.examine_target, 'prereq') and isinstance(self.examine_target.prereq, Spell):
                # We assume the spell upgrade is in the spells list of spell upgrades
                assert(self.examine_target in self.examine_target.prereq.spell_upgrades)

                cur_idx = self.examine_target.prereq.spell_upgrades.index(self.examine_target)
                cur_idx += movedir
                cur_idx = cur_idx % (len(self.examine_target.prereq.spell_upgrades) + 1)

                if cur_idx == len(self.examine_target.prereq.spell_upgrades):
                    self.examine_target = self.examine_target.prereq
                else:
                    self.examine_target = self.examine_target.prereq.spell_upgrades[cur_idx]

        def draw_threat(self):
            level = self.get_display_level()
            # Narrow to one unit maybe
            highlighted_unit = None
            mouse_point = self.get_mouse_level_point()
            if mouse_point:
                highlighted_unit = level.get_unit_at(mouse_point.x, mouse_point.y)
            
            if highlighted_unit and highlighted_unit.is_player_controlled:
                highlighted_unit = None
            
            if not self.threat_zone or highlighted_unit != self.last_threat_highlight:
                self.last_threat_highlight = highlighted_unit
                self.threat_zone = set()

                
                units = []
                possible_spells = []
                possible_buffs = []
                if not highlighted_unit:
                    for u in level.units:
                        if are_hostile(self.game.p1, u):
                            self.threat_zone.add((u.x, u.y))
                            if not u.is_stunned():
                                possible_spells += u.spells
                            possible_buffs += u.buffs
                            units.append(u)
                else:
                    units.append(highlighted_unit)
                    if not highlighted_unit.is_stunned():
                        possible_spells += highlighted_unit.spells
                    possible_buffs += highlighted_unit.buffs
                    self.threat_zone.add((highlighted_unit.x, highlighted_unit.y))
                
                spells = []
                for s in possible_spells:
                    if s.melee:
                        self.add_threat(level, s.caster.x-1, s.caster.y-1)
                        self.add_threat(level, s.caster.x-1, s.caster.y)
                        self.add_threat(level, s.caster.x-1, s.caster.y+1)
                        self.add_threat(level, s.caster.x, s.caster.y-1)
                        self.add_threat(level, s.caster.x, s.caster.y+1)
                        self.add_threat(level, s.caster.x+1, s.caster.y-1)
                        self.add_threat(level, s.caster.x+1, s.caster.y)
                        self.add_threat(level, s.caster.x+1, s.caster.y+1)
                    else:
                        spells.append(s)
                
                spells.sort(key = lambda s: s.range, reverse = True)
                
                buffs = []
                for b in possible_buffs:
                    # kind of bizarre but Buff.can_threaten always returns false
                    # so we just have to detect those buffs with the default method
                    if not b.can_threaten.__func__ == Buff.can_threaten:
                        buffs.append(b)

                for t in level.iter_tiles():
                    # Dont bother with walls
                    if not t.can_walk and not t.can_fly:
                        continue
                    
                    if t in self.threat_zone:
                        continue

                    for s in spells:
                        if s.can_threaten(t.x, t.y) and s.can_pay_costs():
                            self.threat_zone.add((t.x, t.y))
                            break
                    for b in buffs:
                        if b.can_threaten(t.x, t.y):
                            self.threat_zone.add((t.x, t.y))
                            break

            blit_area = (idle_frame * SPRITE_SIZE, 0, SPRITE_SIZE, SPRITE_SIZE)

            to_blit = []
            
            image = self.tile_invalid_target_image
            for t in self.threat_zone:
                to_blit.append((image, (SPRITE_SIZE * t[0], SPRITE_SIZE * t[1]), blit_area))
            
            self.level_display.blits(to_blit)

        def draw_examine_portal(self):


            border_margin = self.border_margin
            cur_x = border_margin
            cur_y = border_margin

            linesize = self.linesize

            gen_params = self.examine_target.level_gen_params

            self.draw_string("Rift", self.examine_display, cur_x, cur_y)
            cur_y += linesize

            if self.game.next_level:
                cur_y += linesize
                self.draw_string("????????", self.examine_display, cur_x, cur_y)
                return

            if self.examine_target.locked:
                cur_y += linesize
                
                width = self.examine_display.get_width() - 2*border_margin
                lines = self.draw_wrapped_string("(Defeat all enemies and destroy all gates to unlock)", self.examine_display, cur_x, cur_y, width)
                cur_y += lines*linesize

            cur_y += linesize

            self.draw_string("Contents:", self.examine_display, cur_x, cur_y)
            cur_y += 2*linesize

            images = []

            COLOR_POP = (255, 255, 255)
            COLOR_BOSS = (253, 143, 77)
            COLOR_ELITE = COLOR_BOSS
            COLOR_ENC = (255, 0, 0)

            for s, l in gen_params.spawn_options:
                unit = s()
                fix_unit(unit)
                sprite_sheet = self.get_sprite_sheet(get_unit_asset(unit))
                images.append((sprite_sheet, unit.name, COLOR_POP))

                #lair_sheet = self.get_sprite_sheet('lair', fill_color=sprite_sheet.get_lair_color())
                #images.append((lair_sheet, '%s Lair' % unit.name))

            drawn_bosses = set()
            for b in gen_params.bosses:
                if b.name in drawn_bosses:
                    continue
                # Dont draw old style bosses
                if 'boss' in b.get_asset_name():
                    continue
                fix_unit(b)
                drawn_bosses.add(b.name)

                sprite_sheet = self.get_sprite_sheet(get_unit_asset(b))
                images.append((sprite_sheet, b.name, COLOR_BOSS if not b.is_boss else COLOR_ENC))

            for image, name, color in images:

                frame = (cloud_frame_clock // 12) % (len(image.anim_frames[ANIM_IDLE]))
                
                sprite = image.anim_frames[ANIM_IDLE][frame]
                scaledimage = pygame.transform.scale(sprite, (32, 32))

                self.examine_display.blit(scaledimage, (cur_x, cur_y))
                if len(name) > 20:
                    name = name[0:18] + '..'
                self.draw_string(name, self.examine_display, cur_x + 36, cur_y + 10, color)
                cur_y += 32 + 4

            cur_y += linesize

            width = self.examine_display.get_width() - 2 *border_margin
            if gen_params.shrine:
                name = gen_params.shrine.name
                
                image = self.get_prop_image(gen_params.shrine)
                frame = (cloud_frame_clock // 12) % (image.get_width() // 16)
                sourcerect = (SPRITE_SIZE * frame, 0, SPRITE_SIZE, SPRITE_SIZE)
                subimage = image.subsurface(sourcerect) 
                scaledimage = pygame.transform.scale(subimage, (64, 64))

                self.examine_display.blit(scaledimage, (cur_x, cur_y))
                
                self.draw_string(gen_params.shrine.name, self.examine_display, 64 + border_margin, cur_y + 24, content_width=width)
                
                cur_y += 64 + linesize

                lines = self.draw_wrapped_string(gen_params.shrine.description, self.examine_display, cur_x, cur_y, width, extra_space=True)
                cur_y += linesize * lines 


            for item in gen_params.items:
                image = get_image(item.get_asset())

                frame = (cloud_frame_clock // 12) % (image.get_width() // 16)
                sourcerect = (SPRITE_SIZE * frame, 0, SPRITE_SIZE, SPRITE_SIZE)
                subimage = image.subsurface(sourcerect)
                scaledimage = pygame.transform.scale(subimage, (32, 32))

                self.examine_display.blit(scaledimage, (cur_x, cur_y))
                self.draw_string(item.name, self.examine_display, cur_x + 38, cur_y+8)

                cur_y += 32

            for s in gen_params.scroll_spells:
                asset = ['tiles', 'library', 'library_white']
                image = get_image(asset)

                frame = (cloud_frame_clock // 12) % (image.get_width() // 16)
                sourcerect = (SPRITE_SIZE * frame, 0, SPRITE_SIZE, SPRITE_SIZE)
                subimage = image.subsurface(sourcerect)
                scaledimage = pygame.transform.scale(subimage, (32, 32))

                self.examine_display.blit(scaledimage, (cur_x, cur_y))
                self.draw_wrapped_string(s.name, self.examine_display, cur_x + 38, cur_y+8, width - 38)

                cur_y += 32

            cur_x = border_margin
        
        def draw_char_sheet(self):
            self.middle_menu_display.fill((0, 0, 0))
            self.draw_panel(self.middle_menu_display)

            # Spells
            spell_x_offset = self.border_margin + 18
            cur_x = spell_x_offset
            cur_y = self.linesize
            self.draw_string("Spells", self.middle_menu_display, cur_x, cur_y)

            m_loc = self.get_mouse_pos()

            cur_y += self.linesize
            cur_y += self.linesize
            spell_index = 0

            col_width = self.middle_menu_display.get_width() // 2 - 2*self.border_margin

            #Spells
            for spell in self.game.p1.spells:

                self.draw_string(spell.name, self.middle_menu_display, cur_x, cur_y, mouse_content=spell, content_width=col_width)
                cur_y += self.linesize

                # Upgrades
                upgrades = sorted((b for b in self.game.p1.buffs if isinstance(b, Upgrade) and b.prereq == spell), key=lambda b: b.shrine_name is None)
                for upgrade in upgrades:
                    fmt = upgrade.name
                    if upgrade.shrine_name:
                        color = COLOR_XP
                        fmt = upgrade.name.replace('(%s)' % spell.name, '')
                    else:
                        color = (255, 255, 255)
                    self.draw_string(' ' + fmt, self.middle_menu_display, cur_x, cur_y, mouse_content=upgrade, content_width=col_width, color=color)

                    cur_y += self.linesize

                available_upgrades = len([b for b in spell.spell_upgrades if b not in upgrades and (not hasattr(b, "exc_class") or b.exc_class not in [upg.exc_class for upg in upgrades if hasattr(upg, "exc_class") and upg.exc_class])])
                if available_upgrades:
                    self.draw_string(' %d Upgrades Available' % available_upgrades, self.middle_menu_display, cur_x, cur_y)
                    cur_y += self.linesize
                spell_index += 1


            learn_color = (255, 255, 255) if len(self.game.p1.spells) < 20 else (170, 170, 170)

            self.draw_string("Learn New Spell (S)", self.middle_menu_display, cur_x, cur_y, learn_color, mouse_content=LEARN_SPELL_TARGET, content_width=col_width)

            # Skills
            skill_x_offset = self.middle_menu_display.get_width() // 2 + self.border_margin
            cur_x = skill_x_offset
            cur_y = self.linesize
            self.draw_string("Skills", self.middle_menu_display, cur_x, cur_y)
            
            cur_y += self.linesize
            cur_y += self.linesize

            for skill in self.game.p1.get_skills():
                self.draw_string(skill.name, self.middle_menu_display, cur_x, cur_y, mouse_content=skill, content_width=col_width)
                cur_y += self.linesize
            self.draw_string("Learn New Skill (K)", self.middle_menu_display, cur_x, cur_y, mouse_content=LEARN_SKILL_TARGET,  content_width=col_width)
            
            self.screen.blit(self.middle_menu_display, (self.h_margin, 0))

        def process_level_input(self):
            
            if self.cast_fail_frames:
                self.cast_fail_frames -= 1

            if any(evt.type == pygame.KEYDOWN for evt in self.events) and self.gameover_frames > 8 and not self.gameover_tiles:
                self.enter_reminisce()
                return

            level_point = self.get_mouse_level_point()
            movedir = None
            keys = pygame.key.get_pressed()

            if self.can_execute_inputs() and self.path:
                if not self.path_delay:
                    next_point = self.path[0]
                    self.path = self.path[1:]
                    movedir = Point(next_point.x - self.game.p1.x, next_point.y - self.game.p1.y)
                    self.try_move(movedir)
                    self.path_delay = MAX_PATH_DELAY
                else:
                    self.path_delay -= 1

            # Disable ff after 1 round
            if self.can_execute_inputs() and self.fast_forward:
                self.fast_forward = False

            for evt in self.events:
                if not evt.type == pygame.KEYDOWN:
                    continue

                # Cancel path on key down
                # do this here instead of by checking pressed keys to deal with pygame alt tab bug
                self.path = []
                
                if evt.key == pygame.K_BACKSPACE:
                    self.fast_forward = True

                if self.can_execute_inputs():
                    if evt.key in self.key_binds[KEY_BIND_UP]:
                        movedir = Point(0, -1)
                    if evt.key in self.key_binds[KEY_BIND_DOWN]:
                        movedir = Point(0, 1)
                    if evt.key in self.key_binds[KEY_BIND_LEFT]:
                        movedir = Point(-1, 0)
                    if evt.key in self.key_binds[KEY_BIND_RIGHT]:
                        movedir = Point(1, 0)
                    if evt.key in self.key_binds[KEY_BIND_DOWN_RIGHT]:
                        movedir = Point(1, 1)
                    if evt.key in self.key_binds[KEY_BIND_DOWN_LEFT]:
                        movedir = Point(-1, 1)
                    if evt.key in self.key_binds[KEY_BIND_UP_LEFT]:
                        movedir = Point(-1, -1)
                    if evt.key in self.key_binds[KEY_BIND_UP_RIGHT]:
                        movedir = Point(1, -1)

                    if evt.key in self.key_binds[KEY_BIND_CONFIRM]:
                        if self.cur_spell:
                            self.cast_cur_spell()
                        elif self.game.deploying:
                            self.deploy(level_point)

                    if evt.key in self.key_binds[KEY_BIND_PASS]:
                        if not self.cur_spell:
                            self.game.try_pass()

                    for bind in range(KEY_BIND_SPELL_1, KEY_BIND_SPELL_10+1):
                        if evt.key in self.key_binds[bind] and not self.game.deploying:
                            index = bind - KEY_BIND_SPELL_1

                            for modifier in self.key_binds[KEY_BIND_MODIFIER_1]:
                                if modifier and keys[modifier]:
                                    index += 10
                            
                            # Item
                            is_item = False
                            for modifier in self.key_binds[KEY_BIND_MODIFIER_2]:
                                if modifier and keys[modifier]:
                                    is_item = True
                            
                            if is_item:
                                if len(self.game.p1.items) > index:
                                    self.choose_spell(self.game.p1.items[index].spell)
                            else:
                                if len(self.game.p1.spells) > index:
                                    self.choose_spell(self.game.p1.spells[index])

                    if evt.key in self.key_binds[KEY_BIND_WALK]:
                        if not any(are_hostile(u, self.game.p1) for u in self.game.cur_level.units):
                            spell = WalkSpell()
                            spell.caster = self.game.p1
                            self.choose_spell(spell)

                    if evt.key in self.key_binds[KEY_BIND_VIEW]:
                        spell = LookSpell()
                        spell.caster = self.game.p1
                        self.choose_spell(spell)

                    if evt.key in self.key_binds[KEY_BIND_CHAR]:
                        self.open_char_sheet()
                        self.char_sheet_select_index = 0

                    if evt.key in self.key_binds[KEY_BIND_SPELLS]:
                        self.open_shop(SHOP_TYPE_SPELLS)

                    if evt.key in self.key_binds[KEY_BIND_SKILLS]:
                        self.open_shop(SHOP_TYPE_UPGRADES)

                    if evt.key in self.key_binds[KEY_BIND_TAB] and (self.cur_spell or self.deploy_target):
                        self.cycle_tab_targets()

                    if evt.key in self.key_binds[KEY_BIND_HELP]:
                        self.show_help()

                    if evt.key in self.key_binds[KEY_BIND_AUTOPICKUP] and all(not are_hostile(self.game.p1, u) for u in self.game.cur_level.units):
                        self.autopickup()

                    if evt.key in self.key_binds[KEY_BIND_INTERACT] and self.game.cur_level.tiles[self.game.p1.x][self.game.p1.y].prop:
                        self.game.cur_level.tiles[self.game.p1.x][self.game.p1.y].prop.on_player_enter(self.game.p1)

                        if self.game.cur_level.cur_shop:
                            self.open_shop(SHOP_TYPE_SHOP)

                        if self.game.cur_level.cur_portal and not self.game.deploying:
                            self.game.enter_portal()

                    if evt.key in self.key_binds[KEY_BIND_ABORT]:
                        if self.cur_spell:
                            self.abort_cur_spell()
                        elif self.game.deploying:
                            self.deploy_target = None
                            self.examine_target = None
                            self.game.try_abort_deploy()
                            self.play_sound("menu_abort")
                        else:
                            self.open_options()

                    if evt.key in self.key_binds[KEY_BIND_MESSAGE_LOG]:
                        self.open_combat_log()

                global cheats_enabled
                if can_enable_cheats and evt.key == pygame.K_z and keys[pygame.K_LSHIFT] and keys[pygame.K_LCTRL]:
                    cheats_enabled = not cheats_enabled

                if cheats_enabled:
                    if evt.key == pygame.K_t and level_point:
                        if self.game.cur_level.can_move(self.game.p1, level_point.x, level_point.y, teleport=True):
                            self.game.cur_level.act_move(self.game.p1, level_point.x, level_point.y, teleport=True)

                    if evt.key == pygame.K_x:
                        self.game.p1.xp += 100

                    if evt.key == pygame.K_y:
                        self.game.p1.xp -= 10

                    if evt.key == pygame.K_h:
                        self.game.p1.max_hp += 250
                        self.game.p1.cur_hp += 250

                    if evt.key == pygame.K_k:
                        for unit in list(self.game.cur_level.units):
                            if unit != self.game.p1:
                                unit.kill()

                    if evt.key == pygame.K_g:
                        self.game.p1.kill()

                    if evt.key == pygame.K_r:
                        for spell in self.game.p1.spells:
                            spell.cur_charges = spell.get_stat('max_charges')

                    if evt.key == pygame.K_i:
                        for i, c in all_consumables:
                            self.game.p1.add_item(i())

                    if evt.key == pygame.K_s:
                        self.game.save_game('./cheat_save')
                        
                    if evt.key == pygame.K_l:
                        self.game = continue_game('cheat_save')

                    if evt.key == pygame.K_c and keys[pygame.K_LSHIFT]:
                        x = self.game.cur_level.tiles[9999][9999]

                    if evt.key == pygame.K_h:
                        self.game.p1.cur_hp = self.game.p1.max_hp

                    if evt.key == pygame.K_d:
                        gates = [tile.prop for tile in self.game.cur_level.iter_tiles() if isinstance(tile.prop, Portal)]
                        for gate in gates:
                            gate.level_gen_params = LevelGenerator(self.game.level_num + 1, self.game)
                            gate.description = gate.level_gen_params.get_description()
                            gate.next_level = None
                            self.game.cur_level.flash(gate.x, gate.y, Tags.Arcane.color)

                    if evt.key == pygame.K_f:
                        self.examine_target = self.get_display_level().gen_params

                    if evt.key == pygame.K_v:
                        to_blit = self.screen
                        scale = 1 
                        w = to_blit.get_width() * scale
                        h = to_blit.get_height() * scale
                        surf = pygame.transform.scale(to_blit, (w, h))

                        for i in range(100):
                            path = "screencap\\ss_%d.png" % i
                            if not os.path.exists(path):
                                pygame.image.save(surf, path)
                                break

                    if evt.key == pygame.K_EQUALS:
                        self.game.level_num += 1

                    if evt.key == pygame.K_MINUS:
                        self.game.level_num -= 1

                    if evt.key == pygame.K_m:
                        for monster, cost in spawn_options:
                            unit = monster()
                            p = self.game.cur_level.get_summon_point(0, 0, radius_limit=40)
                            if p:
                                self.game.cur_level.add_obj(unit, p.x, p.y)

                    if evt.key == pygame.K_b and level_point:
                        if "mods.MordredOverhaul.MordredOverhaul" in sys.modules:
                            unit = sys.modules["mods.MordredOverhaul.MordredOverhaul"].MordredOverhauled()
                        else:
                            unit = Mordred()
                        p = self.game.cur_level.get_summon_point(level_point.x, level_point.y)
                        if p:
                            self.game.cur_level.add_obj(unit, p.x, p.y)

                    if evt.key == pygame.K_p:
                        import pdb
                        pdb.set_trace()

                    if evt.key == pygame.K_o and level_point:
                        self.game.cur_level.add_obj(ManaDot(), level_point.x, level_point.y)

                    if evt.key == pygame.K_q and level_point:
                        points = [p for p in self.game.cur_level.get_points_in_ball(level_point.x, level_point.y, RANGE_GLOBAL) if self.game.cur_level.can_walk(p.x, p.y) and not self.game.cur_level.get_unit_at(p.x, p.y)]
                        for s in new_shrines:
                            p = points.pop()
                            shrine = make_shrine(s[0](), self.game.p1)
                            self.game.cur_level.add_obj(shrine, p.x, p.y)

            if movedir:
                repeats = 1
                if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                    repeats = 4
                if self.cur_spell:
                    for _ in range(repeats):
                        new_spell_target = Point(self.cur_spell_target.x + movedir.x, self.cur_spell_target.y + movedir.y)
                        if self.game.cur_level.is_point_in_bounds(new_spell_target):
                            self.cur_spell_target = new_spell_target
                            self.try_examine_tile(new_spell_target)
                elif self.game.deploying and self.deploy_target:
                    for _ in range(repeats): 
                        new_point = Point(self.deploy_target.x + movedir.x, self.deploy_target.y + movedir.y)
                        if self.game.next_level.is_point_in_bounds(new_point):
                            self.deploy_target = new_point
                            self.try_examine_tile(new_point)
                else:
                    self.try_move(movedir)
                    self.cur_spell_target = None


            mouse_dx, mouse_dy = self.get_mouse_rel()
            if mouse_dx or mouse_dy:
                if level_point: 
                    if self.cur_spell:
                        self.cur_spell_target = level_point
                    if self.game.deploying:
                        self.deploy_target = level_point

                    self.try_examine_tile(level_point)

            for click in self.events:
                if click.type != pygame.MOUSEBUTTONDOWN:
                    continue

                # Cancel click to move on subsequent clicks
                self.path = []
                
                if self.gameover_frames > 8 and not self.gameover_tiles:
                    self.enter_reminisce()
                    return

                mx, my = self.get_mouse_pos()
                if mx < self.h_margin:
                    self.process_click_character(click.button, mx, my)

                if click.button == pygame.BUTTON_LEFT and self.can_execute_inputs():
                    if self.cur_spell and click.button == pygame.BUTTON_LEFT and level_point:
                        self.cur_spell_target = level_point
                        self.cast_cur_spell()
                    elif self.game.deploying and level_point:
                        self.deploy_target = level_point
                        self.deploy(self.deploy_target)
                    elif level_point and all(u.team == TEAM_PLAYER for u in self.game.cur_level.units):
                        self.path = self.game.cur_level.find_path(self.game.p1, level_point, self.game.p1, pythonize=True, cosmetic=True)
                    elif level_point and distance(level_point, self.game.p1, diag=True) >= 1:
                        path = self.game.cur_level.find_path(self.game.p1, level_point, self.game.p1, pythonize=True, cosmetic=True)
                        if path:
                            movedir = Point(path[0].x - self.game.p1.x, path[0].y - self.game.p1.y)
                            self.try_move(movedir)
                    elif level_point and distance(level_point, self.game.p1) == 0:
                        self.game.try_pass()

                if click.button == pygame.BUTTON_RIGHT:
                    if self.cur_spell:
                        self.abort_cur_spell()
                    if self.game.deploying:
                        self.deploy_target = None
                        self.examine_target = None
                        self.game.try_abort_deploy()
                        self.play_sound("menu_abort")

                # Only process one mouse evt per frame
                #break

    if cls is HibernationBuff:

        def on_init(self):
            self.buff_type = BUFF_TYPE_PASSIVE
            self.resists[Tags.Ice] = 75
            self.owner_triggers[EventOnDamaged] = self.on_damaged
            self.name = "Hibernation"

        def on_pre_advance(self):
            if Tags.Living not in self.owner.tags:
                self.owner.remove_buff(self)
                return
            if self.owner.has_buff(FrozenBuff):
                self.owner.deal_damage(-15, Tags.Heal, self)

    if cls is Hibernation:

        def on_advance(self):
            for unit in [unit for unit in self.owner.level.units if unit is not self.owner and not are_hostile(self.owner, unit)]:
                if Tags.Living in unit.tags and not unit.has_buff(HibernationBuff):
                    unit.apply_buff(HibernationBuff())

    if cls is MulticastBuff:

        def on_spell_cast(self, evt):
            if evt.spell.item:
                return
            if Tags.Sorcery not in evt.spell.tags:
                return

            if self.can_copy:
                self.can_copy = False
                for i in range(self.spell.get_stat('copies')):
                    if evt.spell.can_cast(evt.x, evt.y):
                        evt.caster.level.act_cast(evt.caster, evt.spell, evt.x, evt.y, pay_costs=False)
                evt.caster.level.queue_spell(self.reset())

    if cls is MulticastSpell:

        def get_description(self):
            return ("Whenever you cast a [sorcery] spell, copy it [{copies}:sorcery] times. No more spells will be copied until all currently copied spells have resolved.\n"
                    "Lasts [{duration}_turns:duration]").format(**self.fmt_dict())

    if cls is TouchOfDeath:

        def get_description(self):
            return "Deal [{damage}_dark:dark] damage to one unit in melee range.\nThe range of this spell is fixed, and cannot be increased using shrines, skills, or buffs.".format(**self.fmt_dict())

        def on_init(self):
            self.damage = 200
            self.element = Tags.Dark
            self.range = 1
            self.melee = True
            self.can_target_self = False
            self.max_charges = 9
            self.name = "Touch of Death"
            self.tags = [Tags.Dark, Tags.Sorcery]
            self.level = 2

            self.can_target_empty = False

            self.fire_damage = 0
            self.arcane_damage = 0
            self.physical_damage = 0
            self.upgrades['arcane_damage'] = (150, 1, "Voidtouch", "Touch of death also deals [{extra_damage}_arcane:arcane] damage.")
            self.upgrades['fire_damage'] = (150, 1, "Flametouch", "Touch of death also deals [{extra_damage}_fire:fire] damage.")
            self.upgrades['physical_damage'] = (150, 1, "Wrathtouch", "Touch of death also deals [{extra_damage}_physical:physical] damage.")
            self.upgrades['raise_raven'] = (1, 2, 'Touch of the Raven', 'When a [living] target dies to touch of death, it is raised as a friendly Raven.', 'raising')
            self.upgrades['raise_vampire'] = (1, 4, 'Touch of the Vampire', 'When a [living] target dies to touch of death, it is raised as a friendly Vampire.', 'raising')
            self.upgrades['raise_reaper']= (1, 6, 'Touch of the Reaper', 'When a [living] target dies to touch of death, it is raise as a friendly Reaper for [{minion_duration}_turns:minion_duration].', 'raising')

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["extra_damage"] = self.get_stat("damage", base=150)
            stats["minion_duration"] = self.get_stat('minion_duration', base=6)
            return stats

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            extra_damage = self.get_stat('damage', base=150)
            self.caster.level.deal_damage(x, y, self.get_stat('damage'), self.element, self)
            if self.get_stat('arcane_damage'):
                self.caster.level.deal_damage(x, y, extra_damage, Tags.Arcane, self)
            if self.get_stat('fire_damage'):
                self.caster.level.deal_damage(x, y, extra_damage, Tags.Fire, self)
            if self.get_stat('physical_damage'):
                self.caster.level.deal_damage(x, y, extra_damage, Tags.Physical, self)

            if unit and not unit.is_alive() and Tags.Living in unit.tags:
                if self.get_stat('raise_vampire'):
                    vampire = Vampire()
                    apply_minion_bonuses(self, vampire)
                    self.summon(vampire, Point(unit.x, unit.y))
                    unit.has_been_raised = True
                elif self.get_stat('raise_reaper'):
                    reaper = Reaper()
                    reaper.turns_to_death = self.get_stat('minion_duration', base=6)
                    self.summon(reaper, Point(unit.x, unit.y))
                    unit.has_been_raised = True
                elif self.get_stat('raise_raven'):
                    hag = Raven()
                    apply_minion_bonuses(self, hag),
                    self.summon(hag, Point(unit.x, unit.y))
                    unit.has_been_raised = True

    if cls is BestowImmortality:

        def can_cast(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            return unit and unit is not self.caster and Spell.can_cast(self, x, y)

        def get_description(self):
            return "Target unit gains the ability to reincarnate on death [{lives}_times:holy] for [{duration}_turns:duration].".format(**self.fmt_dict())

    if cls is Enlarge:

        def get_ai_target(self):
            imps = [u for u in self.caster.level.units if u is not self.caster and self.monster_name.lower() in u.name.lower() and "Gate" not in u.name and "Collector" not in u.name]
            if imps:
                return random.choice(imps)
            else:
                return None

    if cls is LightningHaloBuff:

        def nova(self):
            self.owner.level.show_effect(0, 0, Tags.Sound_Effect, 'sorcery_ally')
            points = self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.radius)
            points = [p for p in points if p != Point(self.owner.x, self.owner.y) and distance(self.owner, p) >= self.radius - 1]

            for p in points:
                self.owner.level.deal_damage(p.x, p.y, self.spell.get_stat('damage'), self.spell.element, self.spell)
            
            yield

    if cls is LightningHaloSpell:

        def cast_instant(self, x, y):

            buff = LightningHaloBuff(self)
            buff.radius = self.get_stat('radius')
            self.caster.apply_buff(buff, self.get_stat('duration'))

    if cls is ClarityIdolBuff:

        def on_advance(self):
            units = list(self.owner.level.units)
            random.shuffle(units)
            for u in units:
                if u.team != self.owner.team:
                    continue
                buf = u.get_buff(Stun) or u.get_buff(BerserkBuff)
                if buf:
                    u.remove_buff(buf)
                    self.owner.level.show_path_effect(self.owner, u, Tags.Holy, minor=True)
                    return

    if cls is Unit:

        def deal_damage(self, amount, damage_type, spell, penetration=0):
            if not self.is_alive():
                return 0
            return self.level.deal_damage(self.x, self.y, amount, damage_type, spell, penetration=penetration)

        def kill(self, damage_event=None, trigger_death_event=True):
            # Sometimes you kill something twice, whatever.
            if self.killed:
                return
            self.cur_hp = 0
            self.killed = True

            # TODO- trigger on death events and such?
            if trigger_death_event:
                self.level.event_manager.raise_event(EventOnDeath(self, damage_event), self)
            self.level.remove_obj(self)

        def pre_advance(self):
            # Pre turn effects
            self.cool_downs = { spell : (cooldown - 1) for (spell, cooldown) in self.cool_downs.items() if cooldown > 1}

            for b in list(self.buffs):
                b.on_pre_advance()

        def get_buff(self, buff_class):
            candidates = [b for b in self.buffs if isinstance(b, buff_class)]
            if candidates:
                return candidates[0]
            else:
                return None

        def apply_buff(self, buff, duration=0, trigger_buff_apply_event=True, prepend=False):
            assert(isinstance(buff, Buff))
            
            # Do not apply buffs to dead units
            if not self.is_alive():
                return

            if self.clarity > 0 and buff.buff_type == BUFF_TYPE_CURSE:
                self.clarity -= 1
                return

            if not buff.on_attempt_apply(self):
                return	

            if buff.buff_type == BUFF_TYPE_CURSE and self.debuff_immune:
                return
            if buff.buff_type == BUFF_TYPE_BLESS and self.buff_immune:
                return

            #assert(self.level)
            # For now unstackable = stack_type stack duration

            def same_buff(b1, b2):
                return b1.name == b2.name and type(b1) == type(b2)

            existing = [b for b in self.buffs if same_buff(b, buff)]
            if existing:
                if buff.stack_type == STACK_NONE:
                    existing[0].turns_left = max(duration, existing[0].turns_left)
                    return
                elif buff.stack_type == STACK_DURATION:
                    existing[0].turns_left += duration
                    return
                elif buff.stack_type == STACK_REPLACE:
                    self.remove_buff(existing[0])
                    # And continue to add this one

            if buff.stack_type == STACK_TYPE_TRANSFORM:
                existing = [b for b in self.buffs if b != buff and b.stack_type == STACK_TYPE_TRANSFORM]
                if existing:
                    self.remove_buff(existing[0])

            assert(isinstance(buff, Buff))
            buff.turns_left = duration

            if prepend:
                self.buffs.insert(0, buff)
            else:
                self.buffs.append(buff)
            result = buff.apply(self)
            if result == ABORT_BUFF_APPLY:
                self.buffs.remove(buff)
                return

            if buff.show_effect:
                if buff.buff_type == BUFF_TYPE_BLESS:
                    if self.buff_immune:
                        return
                    self.level.show_effect(self.x, self.y, Tags.Buff_Apply, buff.color)
                if buff.buff_type == BUFF_TYPE_CURSE:
                    if self.debuff_immune:
                        return
                    self.level.show_effect(self.x, self.y, Tags.Debuff_Apply, buff.color)
            
            if trigger_buff_apply_event:
                self.level.event_manager.raise_event(EventOnBuffApply(buff, self), self)

        def remove_buff(self, buff, trigger_buff_remove_event=True):

            if buff not in self.buffs:
                return
            if not buff.applied:
                return

            self.buffs.remove(buff)
            buff.unapply()

            if trigger_buff_remove_event:
                self.level.event_manager.raise_event(EventOnBuffRemove(buff, self), self)

        def get_skills(self):
            return sorted((b for b in self.buffs if isinstance(b, Upgrade) and b.prereq is None), key=lambda b: b.name)

    if cls is Buff:

        def summon(self, unit, target=None, radius=3, team=None, sort_dist=True):
            if not unit.source :
                unit.source = self
            if not target:
                target = Point(self.owner.x, self.owner.y)
            return self.owner.level.summon(self.owner, unit, target, radius, team, sort_dist)

    if cls is HallowFlesh:

        def cast(self, x, y):
            points = self.get_impacted_tiles(x, y)
            for p in points:
                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit:
                    unit.apply_buff(curr_module.RotBuff(self))
                    yield

    if cls is DarknessBuff:

        def effect_unit(self, unit):
            if Tags.Demon not in unit.tags and Tags.Undead not in unit.tags:
                unit.apply_buff(BlindBuff(), 1, prepend=unit is self.owner)

        def on_advance(self):
            for unit in self.owner.level.units:
                self.effect_unit(unit)

        on_applied = lambda self, owner: None
        on_unapplied = lambda self: None

    if cls is VenomSpit:

        def on_init(self):
            self.name = "Venom Spit"
            self.tags = [Tags.Nature]
            self.level = 4
            self.minion_damage = 4
            self.minion_range = 6
            self.duration = 10
            self.global_triggers[EventOnUnitAdded] = lambda evt: on_unit_added(self, evt)

        def on_unit_added(self, evt):
            if self.should_grant(evt.unit):
                add_spell(self, evt.unit)

        def on_advance(self):
            for unit in self.owner.level.units:
                spit = [s for s in unit.spells if isinstance(s, VenomSpitSpell)]
                if spit and not self.should_grant(unit):
                    unit.remove_spell(spit[0])
                elif not spit and self.should_grant(unit):
                    add_spell(self, unit)

        def add_spell(self, unit):
            spell = VenomSpitSpell()
            spell.damage = self.get_stat('minion_damage')
            spell.range = self.get_stat('minion_range')
            spell.buff_duration = self.get_stat("duration")
            #weird cause im trying to insert at 0
            spell.caster = unit
            spell.owner = unit
            unit.spells.insert(0, spell)

        def get_description(self):
            return ("Your summoned [living] and [nature] units gain Venom Spit.\n"
                    "Venom spit is a ranged attack which deals [{minion_damage}_poison:poison] damage and inflicts [poison] for [{duration}_turns:duration].\n"
                    "Venom spit has a [{minion_range}_tile:range] range, and a [4_turn:cooldown] cooldown.").format(**self.fmt_dict())

    if cls is VenomSpitSpell:

        def __init__(self):
            SimpleRangedAttack.__init__(self, name="Venom Spit", damage=4, damage_type=Tags.Poison, cool_down=4, range=6, buff=Poison, buff_duration=10)

    if cls is Hunger:

        def on_init(self):
            self.name = "Hungry Dead"
            self.tags = [Tags.Dark]
            self.level = 4
            self.minion_range = 3
            self.minion_damage = 7
            self.global_triggers[EventOnUnitAdded] = lambda evt: on_unit_added(self, evt)

        def on_unit_added(self, evt):
            if self.should_grant(evt.unit):
                add_spell(self, evt.unit)

        def on_advance(self):
            for unit in self.owner.level.units:
                hunger = [s for s in unit.spells if isinstance(s, HungerLifeLeechSpell)]
                if hunger and not self.should_grant(unit):
                    unit.remove_spell(hunger[0])
                elif not hunger and self.should_grant(unit):
                    add_spell(self, unit)

        def add_spell(self, unit):
            spell = HungerLifeLeechSpell()
            spell.damage = self.get_stat('minion_damage')
            spell.range = self.get_stat('minion_range')
            #weird cause im trying to insert at 0
            spell.caster = unit
            spell.owner = unit
            unit.spells.insert(0, spell)

    if cls is EyeOfRageSpell:

        def cast_instant(self, x, y):
            buff = RageEyeBuff(self.get_stat("shot_cooldown"), self.get_stat('berserk_duration'), self)
            self.caster.apply_buff(buff, self.get_stat('duration'))

    if cls is Level:

        def deal_damage(self, x, y, amount, damage_type, source, flash=True, penetration=0):

            # Auto make effects if none were already made
            if flash:
                effect = Effect(x, y, damage_type.color, Color(0, 0, 0), 12)
                if amount == 0:
                    effect.minor = True
                self.effects.append(effect)

            cloud = self.tiles[x][y].cloud
            if cloud and amount > 0:
                cloud.on_damage(damage_type)

            unit = self.get_unit_at(x, y)
            if not unit:
                return 0
            if not unit.is_alive():
                return 0


            # Raise pre damage event (for conversions)
            pre_damage_event = EventOnPreDamaged(unit, amount, damage_type, source)
            if penetration:
                pre_damage_event = EventOnPreDamagedPenetration(pre_damage_event, penetration)
            self.event_manager.raise_event(pre_damage_event, unit)

            # Factor in shields and resistances after raising the raw pre damage event
            resist_amount = unit.resists.get(damage_type, 0) - penetration

            # Cap effective resists at 100- shenanigans ensue if we do not
            resist_amount = min(resist_amount, 100)

            if resist_amount:
                multiplier = (100 - resist_amount) / 100.0
                amount = int(math.ceil(amount * multiplier))

            if amount > 0 and unit.shields > 0:
                unit.shields = unit.shields - 1
                self.combat_log.debug("%s blocked %d %s damage from %s" % (unit.name, amount, damage_type.name, source.name))
                self.show_effect(unit.x, unit.y, Tags.Shield_Expire)				
                return 0

            amount = min(amount, unit.cur_hp)
            unit.cur_hp = unit.cur_hp - amount

            if amount > 0:
                self.combat_log.debug("%s took %d %s damage from %s" % (unit.name, amount, damage_type.name, source.name))
            elif amount < 0:
                self.combat_log.debug("%s healed %d from %s" % (unit.name, -amount, source.name))

            if (amount > 0):

                # Record damage for post level summary
                if source.owner and source.owner != self.player_unit:
                    source_key = "%s (%s)" % (source.name, source.owner.name)
                    self.damage_taken_sources
                else:
                    source_key = "%s" % source.name

                # Record damage sources when a player unit exists (aka not in unittests)
                if self.player_unit:
                    if are_hostile(unit, self.player_unit):
                        key = source.name
                        if source.owner and source.owner.source:
                            key = source.owner.name

                        self.damage_dealt_sources[key] += amount
                    elif unit == self.player_unit:
                        if source.owner:
                            key = source.owner.name
                        else:
                            key = source.name	
                        self.damage_taken_sources[key] += amount

                damage_event = EventOnDamaged(unit, amount, damage_type, source)
                if penetration:
                    damage_event = EventOnDamagedPenetration(damage_event, penetration)
                self.event_manager.raise_event(damage_event, unit)
            
                if (unit.cur_hp <= 0):
                    unit.kill(damage_event = damage_event)			

                    if (unit.cur_hp <= 0):
                        unit.kill(damage_event = damage_event)			
                    
                if (unit.cur_hp > unit.max_hp):
                    unit.cur_hp = unit.max_hp
            # set amount to 0 if there is no unit- ie, if an empty tile or dead unit was hit
            else:
                amount = 0

            if (unit.cur_hp > unit.max_hp):
                unit.cur_hp = unit.max_hp

            return amount

        def add_obj(self, obj, x, y, trigger_summon_event=True):
            obj.x = x
            obj.y = y
            obj.level = self

            if not hasattr(obj, 'level_id'):
                obj.level_id = self.level_id

            if isinstance(obj, Unit):
                if trigger_summon_event:
                    self.event_manager.raise_event(EventOnUnitPreAdded(obj), obj)

                if not obj.cur_hp:
                    obj.cur_hp = obj.max_hp
                    assert(obj.cur_hp > 0)
                    
                assert(self.tiles[x][y].unit is None)
                self.tiles[x][y].unit = obj

                # Hack- allow improper adding in monsters.py
                for spell in obj.spells:
                    spell.caster = obj
                    spell.owner = obj

                fix_unit(obj if not obj.is_lair else obj.buffs[0].example_monster)

                self.set_default_resitances(obj)

                for buff in list(obj.buffs):
                    # Apply unapplied buffs- these can come from Content on new units
                    could_apply = buff.apply(obj) != ABORT_BUFF_APPLY

                    # Remove buffs which cannot be applied (happens with stun + clarity potentially)
                    if not could_apply:
                        obj.buffs.remove(obj)

                    # Monster buffs are all passives
                    if not obj.is_player_controlled:
                        buff.buff_type = BUFF_TYPE_PASSIVE

                self.units.append(obj)
                if trigger_summon_event:
                    self.event_manager.raise_event(EventOnUnitAdded(obj), obj)

                obj.ever_spawned = True

            elif isinstance(obj, Cloud):

                # kill any existing clouds
                cur_cloud = self.tiles[x][y].cloud 
                if cur_cloud is not None:

                    if cur_cloud.can_be_replaced_by(obj):
                        cur_cloud.kill()
                    else:
                        return

                self.tiles[x][y].cloud = obj
                self.clouds.append(obj)

            elif isinstance(obj, Prop):
                self.add_prop(obj, x, y)

            else:
                assert(False) # Unknown obj type

        def queue_spell(self, spell, prepend=False):
            assert(hasattr(spell, "__next__"))
            if prepend:
                self.active_spells.insert(0, spell)
            else:
                self.active_spells.append(spell)

        def remove_obj(self, obj):
            if isinstance(obj, Unit):

                # Unapply to unsubscribe
                for buff in obj.buffs:
                    buff.unapply()
                
                if obj.Anim:
                    obj.Anim.unregister()
                    obj.Anim = None
                for evt_type in self.event_manager._handlers.keys():
                    if obj in self.event_manager._handlers[evt_type].keys():
                        self.event_manager._handlers[evt_type].pop(obj)

                assert(self.tiles[obj.x][obj.y].unit == obj)
                self.tiles[obj.x][obj.y].unit = None

                assert(obj in self.units)
                self.units.remove(obj)

            if isinstance(obj, Cloud):
                assert(self.tiles[obj.x][obj.y].cloud == obj)
                self.tiles[obj.x][obj.y].cloud = None
                self.clouds.remove(obj)

            if isinstance(obj, Prop):
                self.remove_prop(obj)

            obj.removed = True

        def make_wall(self, x, y, calc_glyph=True):

            tile = self.tiles[x][y]
            tile.sprites = None
            tile.can_walk = False
            tile.can_see = False
            tile.can_fly = False
            tile.is_chasm = False

            if self.tcod_map:
                libtcod.map_set_properties(self.tcod_map, tile.x, tile.y, tile.can_see, tile.can_walk)

        def make_floor(self, x, y, calc_glyph=True):

            tile = self.tiles[x][y]
            tile.sprites = None
            tile.can_walk = True
            tile.can_see = True
            tile.can_fly = True
            tile.is_chasm = False

            if self.tcod_map:
                libtcod.map_set_properties(self.tcod_map, tile.x, tile.y, tile.can_see, tile.can_walk)

        def make_chasm(self, x, y, calc_glyph=True):
            tile = self.tiles[x][y]
            tile.sprites = None
            tile.can_walk = False
            tile.can_see = True
            tile.can_fly = True
            tile.is_chasm = True

            if self.tcod_map:
                libtcod.map_set_properties(self.tcod_map, tile.x, tile.y, tile.can_see, tile.can_walk)

    if cls is ReincarnationBuff:

        def respawn(self):
            self.owner.killed = False

            respawn_points = [p for p in self.owner.level.iter_tiles() if self.owner.level.can_stand(p.x, p.y, self.owner)]
            if respawn_points:

                # Restore original shields
                self.owner.shields = self.shields

                # Heal any max hp damage
                self.owner.max_hp = max(self.owner.max_hp, self.max_hp)

                dest = random.choice(respawn_points)
                self.owner.cur_hp = self.owner.max_hp
                self.owner.turns_to_death = self.turns_to_death
                self.owner.level.add_obj(self.owner, dest.x, dest.y, trigger_summon_event=False)


            # Reapply self if removed- happens if reincarnation was granted as a non passive buff
            if self not in self.owner.buffs:
                self.owner.apply_buff(self, self.turns_left, trigger_buff_apply_event=False)

            if self.lives == 0:
                self.owner.remove_buff(self)

            # Stun for 1 turn so units dont teleport next to stuff and kill them while they reincarnate
            self.owner.apply_buff(Stun(), 1)
            yield

        def on_death(self, evt):
            if self.lives >= 1:

                to_remove = [b for b in self.owner.buffs if b.buff_type != BUFF_TYPE_PASSIVE]
                for b in to_remove:
                    self.owner.remove_buff(b, trigger_buff_remove_event=(b is not self))

                self.lives -= 1
                self.owner.level.queue_spell(self.respawn())
                self.name = "Reincarnation %d" % self.lives

        def on_applied(self, owner):
            # Cache the initial turns to death value
            if owner.turns_to_death is not None:
                if owner.source and hasattr(owner.source, "minion_duration") and owner.source.get_stat('minion_duration'):
                    self.turns_to_death = owner.source.get_stat('minion_duration')
                else:
                    self.turns_to_death = owner.turns_to_death
            # Cache initial shields
            self.shields = self.owner.shields
            # Cache max hp in case it gets reduced
            self.max_hp = self.owner.max_hp

    if cls is MagicMissile:

        def on_init(self):
            self.name = "Magic Missile"
            self.range = 12
            self.tags = [Tags.Arcane, Tags.Sorcery]
            self.level = 1

            self.damage = 11
            self.damage_type = Tags.Arcane

            self.max_charges = 20
            self.shield_burn = 0

            self.upgrades['max_charges'] = (15, 2)
            self.upgrades['damage'] = (10, 3)
            self.upgrades['range'] = (5, 1)
            self.upgrades['shield_burn'] = (3, 1, "Shield Burn", "Magic Missile removes up to 3 SH from the target before dealing damage.")

            self.upgrades['slaughter'] = (1, 4, "Slaughter Bolt", "If Magic Missile targets a [living] unit, it deals [poison], [dark], and [physical] damage instead of [arcane].", 'bolt')
            self.upgrades['holy'] = (1, 4, "Holy Bolt", "If Magic Missile targets a [demon] or [undead] unit, it deals [holy] damage in addition to [arcane] damage.", 'bolt')
            self.upgrades['disruption'] = (1, 6, "Disruption Bolt", "If Magic Missile targets an [arcane] unit, it deals [dark] and [holy] damage instead of [arcane].", 'bolt')

        def cast(self, x, y):
            dtypes = [Tags.Arcane]
            unit = self.caster.level.get_unit_at(x, y)
                    
            for p in Bolt(self.caster.level, self.caster, Point(x, y)):
                self.caster.level.show_effect(p.x, p.y, Tags.Arcane, minor=True)
                yield

            if unit:
                if self.get_stat('shield_burn'):
                    unit.shields -= self.get_stat('shield_burn')
                    unit.shields = max(unit.shields, 0)

                if self.get_stat('slaughter') and Tags.Living in unit.tags:
                    dtypes = [Tags.Poison, Tags.Dark, Tags.Physical]
                if self.get_stat('disruption') and Tags.Arcane in unit.tags:
                    dtypes = [Tags.Holy, Tags.Dark]
                if self.get_stat('holy') and (Tags.Undead in unit.tags or Tags.Demon in unit.tags):
                    dtypes = [Tags.Holy, Tags.Arcane]

            for dtype in dtypes:
                self.caster.level.deal_damage(x, y, self.get_stat('damage'), dtype, self)
                if len(dtypes)> 1:
                    for i in range(4):
                        yield

    if cls is InvokeSavagerySpell:

        def get_impacted_tiles(self, x, y):
            return [u for u in self.caster.level.units if u is not self.caster and not are_hostile(u, self.caster) and Tags.Living in u.tags]

    if cls is ConductanceSpell:

        def get_description(self):
            return ("Curse an enemy with the essence of conductivity.\n"
                    "That enemy loses [{resistance_debuff}_lightning:lightning] resist.\n"
                    "Whenever you cast a [lightning] spell targeting that enemy, copy that spell.\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is StormNova:

        def cast_instant(self, x, y):
            for stage in Burst(self.caster.level, self.caster, self.get_stat('radius')):
                for p in stage:
                    if (p.x, p.y) == (self.caster.x, self.caster.y):
                        continue
                    dtype = random.choice([Tags.Ice, Tags.Lightning])

                    self.caster.level.deal_damage(p.x, p.y, self.get_stat('damage'), dtype, self)
                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if unit:
                        if dtype == Tags.Ice:
                            unit.apply_buff(FrozenBuff(), self.get_stat('duration'))
                        if dtype == Tags.Lightning:
                            unit.apply_buff(Stun(), self.get_stat('duration'))

                    if self.get_stat('clouds'):
                        if dtype == Tags.Ice:
                            cloud = BlizzardCloud(self.caster)
                        if dtype == Tags.Lightning:
                            cloud = StormCloud(self.caster)
                        cloud.source = self
                        self.caster.level.add_obj(cloud, p.x, p.y)

    if cls is IcePhoenixBuff:

        def on_init(self):
            self.color = Tags.Ice.color
            self.owner_triggers[EventOnDeath] = self.on_death
            self.name = "Phoenix Freeze"
            self.radius = 6
            self.damage = 25

        def get_tooltip(self):
            return "On death, deal %i ice damage to enemies and applies 2 SH to allies in a %i radius." % (self.damage, self.radius)

        def on_death(self, evt):
            for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.radius):
                unit = self.owner.level.get_unit_at(*p)
                if unit and not are_hostile(unit, self.owner):
                    unit.add_shields(2)
                else:
                    self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Ice, self)

    if cls is SummonIcePhoenix:

        def on_init(self):
            self.name = "Ice Phoenix"
            self.level = 5
            self.max_charges = 2
            self.tags = [Tags.Conjuration, Tags.Ice, Tags.Holy]

            self.minion_health = 74
            self.minion_damage = 9
            self.minion_range = 4
            self.lives = 1
            self.radius = 6

            self.upgrades['lives'] = (2, 3, "Reincarnations", "The phoenix will reincarnate 2 more times")
            self.upgrades['minion_damage'] = (9, 2)

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["explosion_damage"] = self.get_stat("minion_damage", base=25)
            return stats

        def get_description(self):
            return ("Summon an ice phoenix.\n"
                    "The phoenix has [{minion_health}_HP:minion_health], flies, and reincarnates [{lives}_times:holy] upon death.\n"
                    "The phoenix has a ranged attack which deals [{minion_damage}_ice:ice] damage with a [{minion_range}_tile:minion_range] range.\n"
                    "When the phoenix dies, it explodes in a [{radius}_tile:radius] radius, dealing [{explosion_damage}_ice:ice] damage to enemies and granting [2_SH:shields] to allies.").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            phoenix = Unit()
            phoenix.max_hp = self.get_stat('minion_health')
            phoenix.name = "Ice Phoenix"

            phoenix.tags = [Tags.Ice, Tags.Holy]

            buff = IcePhoenixBuff()
            buff.radius = self.get_stat("radius")
            buff.damage = self.get_stat("minion_damage", base=25)
            phoenix.buffs.append(buff)
            phoenix.buffs.append(ReincarnationBuff(self.get_stat('lives')))

            phoenix.flying = True

            phoenix.resists[Tags.Ice] = 100
            phoenix.resists[Tags.Dark] = -50

            phoenix.spells.append(SimpleRangedAttack(damage=self.get_stat('minion_damage'), range=self.get_stat('minion_range'), damage_type=Tags.Ice))
            self.summon(phoenix, target=Point(x, y))

    if cls is RingOfSpiders:

        def cast(self, x, y):

            for p in self.get_impacted_tiles(x, y):
                unit = self.caster.level.get_unit_at(p.x, p.y)

                rank = max(abs(p.x - x), abs(p.y - y))

                if rank == 0:
                    if self.get_stat('damage'):
                        self.caster.level.deal_damage(x, y, self.get_stat('damage'), Tags.Poison, self)
                elif rank == 1:
                    if not unit:
                        if self.get_stat('aether_spiders'):
                            spider = PhaseSpider()
                        else:
                            spider = GiantSpider()
                        spider.team = self.caster.team
                        
                        spider.spells[0].damage = self.get_stat('minion_damage', base=spider.spells[0].damage)
                        spider.max_hp = self.get_stat('minion_health', base=spider.max_hp)

                        self.summon(spider, p)

                    if unit:
                        unit.apply_buff(Poison(), self.get_stat('duration'))
                else:
                    if not unit:
                        cloud = SpiderWeb()
                        cloud.owner = self.caster
                        self.caster.level.add_obj(cloud, *p)
                    if unit:
                        unit.apply_buff(Stun(), 1)
                yield

    if cls is SlimeformBuff:

        def on_init(self):
            self.name = "Slime Form"
            self.transform_asset_name = "slime_form"
            self.stack_type = STACK_TYPE_TRANSFORM
            self.resists[Tags.Poison] = 100
            self.resists[Tags.Physical] = 50
            self.color = Tags.Slime.color

        def make_summon(self, base):
            unit = base()
            unit.max_hp = self.spell.get_stat('minion_health')
            unit.spells[0].damage = self.spell.get_stat('minion_damage')
            if not unit.spells[0].melee:
                unit.spells[0].range = self.spell.get_stat('minion_range', base=unit.spells[0].range)
            # Make sure bonuses propogate
            unit.buffs[0].spawner = lambda : self.make_summon(base)
            unit.source = self.spell
            return unit

    if cls is LightningFrenzy:

        def on_init(self):
            self.tags = [Tags.Lightning]
            self.level = 5
            self.name = "Lightning Frenzy"
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.bonus = 4
            self.duration = 6

        def get_description(self):
            return "Whenever you cast a [lightning] spell, your [lightning] spells and skills gain [%d_damage:damage] for [%d_turns:duration]" % (self.bonus, self.get_stat("duration"))

        def on_spell_cast(self, evt):
            if Tags.Lightning in evt.spell.tags:
                self.owner.apply_buff(LightningFrenzyStack(self.bonus), self.get_stat("duration"))

    if cls is ArcaneCombustion:

        def on_init(self):
            self.tags = [Tags.Arcane]
            self.level = 4
            self.name = "Arcane Combustion"
            self.global_triggers[EventOnDeath] = self.on_death
            self.damage = 12
            self.radius = 1

        def explosion(self, evt):
            for p in self.owner.level.get_points_in_ball(evt.x, evt.y, self.get_stat("radius"), diag=True):
                self.owner.level.deal_damage(p.x, p.y, self.get_stat('damage'), Tags.Arcane, self)
                if self.owner.level.tiles[p.x][p.y].is_wall():
                    self.owner.level.make_floor(p.x, p.y)
            yield

        def get_description(self):
            return ("Whenever a unit is killed by arcane damage, that unit explodes for [%d_arcane:arcane] damage in a [%d_tile:radius] square, melting walls on effected tiles.") % (self.get_stat('damage'), 2*self.get_stat("radius") + 1)

    if cls is LightningWarp:

        def on_init(self):
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.damage = 12
            self.name = "Lightning Warp"
            self.level = 6
            self.radius = 3
            self.tags = [Tags.Lightning, Tags.Translocation]

        def get_description(self):
            return "Whenever you cast a [lightning] spell, all enemy units within [{radius}_tiles:radius] of the target are teleported to random spaces [4_to_8_tiles:range] away and take [{damage}_lightning:lightning] damage.".format(**self.fmt_dict())

        def do_teleports(self, evt):
            for unit in self.owner.level.get_units_in_ball(evt, self.get_stat("radius")):
                if not self.owner.level.are_hostile(unit, self.owner):
                    continue

                points = self.owner.level.get_points_in_ball(evt.x, evt.y, 8)
                points = [p for p in points if distance(p, self.owner) >= 4 and self.owner.level.can_stand(p.x, p.y, unit)]
                if points:
                    point = random.choice(points)
                    self.owner.level.act_move(unit, point.x, point.y, teleport=True)
                    unit.deal_damage(self.get_stat('damage'), Tags.Lightning, self)
                    yield

    if cls is NightmareBuff:

        def on_unapplied(self):
            creatures = []

            if self.spell.get_stat("electric_dream"):
                creatures = [(Elf, 80), (Thunderbird, 35), (SparkSpirit, 25)]
            if self.spell.get_stat("dark_dream"):
                creatures = [(OldWitch, 80), (Werewolf, 35), (Raven, 25)]
            if self.spell.get_stat("fever_dream"):
                creatures = [(FireSpawner, 80), (FireSpirit, 35), (FireLizard, 25)]

            for spawner, cost in creatures:
                for i in range(self.damage_dealt // cost):
                    unit = spawner()
                    unit.turns_to_death = random.randint(4, 13)
                    apply_minion_bonuses(self.spell, unit)
                    self.spell.summon(unit, sort_dist=False, radius=self.radius)

    if cls is HolyBlast:

        def on_init(self):

            self.name = "Heavenly Blast"
            self.range = 7
            self.radius = 1
            self.damage = 7

            self.damage_type = Tags.Holy
            
            self.max_charges = 14

            self.level = 2

            self.tags = [Tags.Holy, Tags.Sorcery] 

            self.upgrades['range'] = (3, 2)
            self.upgrades['radius'] = (1, 2)
            self.upgrades['damage'] = (9, 3)
            self.upgrades['max_charges'] = (7, 2)
            self.upgrades['spiritbind'] = (1, 6, "Spirit Bind", "Slain enemies create spirits for [{minion_duration}_turns:minion_duration].\nSpirit are [holy] [undead] minions with [{minion_health}_HP:minion_health] and attacks with [{minion_range}_range:minion_range] that deal [{minion_damage}_holy:holy] damage.")
            self.upgrades['shield'] = (1, 3, "Shield", "Affected ally units gain [2_SH:shields], to a maximum of [5_SH:shields].")
            self.upgrades['echo_heal'] = (1, 4, "Echo Heal", "Affected ally units are re-healed for half the initial amount each turn for [{duration}_turns:duration].")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_health"] = self.get_stat("minion_health", base=4)
            stats["minion_damage"] = self.get_stat("minion_damage", base=2)
            stats["minion_range"] = self.get_stat("minion_range", base=3)
            stats["minion_duration"] = self.get_stat("minion_duration", base=7)
            stats["duration"] = self.get_stat("duration", base=5)
            return stats

        def cast(self, x, y):
            target = Point(x, y)

            def deal_damage(point):
                no_damage = True
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if unit and not are_hostile(unit, self.caster) and not unit == self.caster and unit != self.statholder:
                    unit.deal_damage(-self.get_stat('damage'), Tags.Heal, self)
                    if self.get_stat('shield'):
                        if unit.shields < 4:
                            unit.add_shields(2)
                        elif unit.shields == 4:
                            unit.add_shields(1)
                    if self.get_stat('echo_heal'):
                        unit.apply_buff(RegenBuff(self.get_stat('damage') // 2), self.get_stat("duration", base=5))
                elif unit == self.caster:
                    pass
                elif unit and unit.is_player_controlled and not are_hostile(self.caster, unit):
                    pass
                else:
                    self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Holy, self)
                    no_damage = False
                    if unit and not unit.is_alive() and self.get_stat('spiritbind'):
                        spirit = Unit()
                        spirit.name = "Spirit"
                        spirit.asset_name = "holy_ghost" # temp
                        spirit.max_hp = 4
                        spirit.spells.append(SimpleRangedAttack(damage=2, damage_type=Tags.Holy, range=3))
                        spirit.turns_to_death = 7
                        spirit.tags = [Tags.Holy, Tags.Undead]
                        spirit.buffs.append(TeleportyBuff())
                        apply_minion_bonuses(self, spirit)
                        spirit.resists[Tags.Holy] = 100
                        spirit.resists[Tags.Dark] = -100
                        spirit.resists[Tags.Physical] = 100
                        self.summon(spirit, target=unit)
                if no_damage:
                    self.caster.level.show_effect(point.x, point.y, Tags.Holy)

            points_hit = set()
            for point in Bolt(self.caster.level, self.caster, target):
                deal_damage(point)
                points_hit.add(point)
                yield

            stagenum = 0
            for stage in Burst(self.caster.level, target, self.get_stat('radius')):
                for point in stage:
                    if point in points_hit:
                        continue
                    deal_damage(point)

                stagenum += 1
                yield

        def get_ai_target(self):
            enemy = self.get_corner_target(self.get_stat("radius"))
            if enemy:
                return enemy
            else:
                allies = [u for u in self.caster.level.get_units_in_ball(self.caster, self.get_stat('range')) if u != self.caster and not are_hostile(self.caster, u) and not u.is_player_controlled]
                allies = [u for u in allies if self.caster.level.can_see(self.caster.x, self.caster.y, u.x, u.y)]
                allies = [u for u in allies if u.cur_hp < u.max_hp]
                if allies:
                    return random.choice(allies)
            return None

    if cls is FalseProphetHolyBlast:

        def get_ai_target(self):
            enemy = self.get_corner_target(self.get_stat("radius"))
            if enemy:
                return enemy
            else:
                allies = [u for u in self.caster.level.get_units_in_ball(self.caster, self.get_stat('range')) if u != self.caster and not are_hostile(self.caster, u)]
                allies = [u for u in allies if self.caster.level.can_see(self.caster.x, self.caster.y, u.x, u.y)]
                allies = [u for u in allies if u.cur_hp < u.max_hp]
                if allies:
                    return random.choice(allies)
            return None

    if cls is Burst:

        def __iter__(self):

            already_exploded = set([self.origin])
            last_stage = set([self.origin])

            # start with the center point obviously
            if not self.burst_cone_params:
                yield set([self.origin])
            
            ball_radius = 1.5 if self.expand_diagonals else 1.1

            # For very narrow cones, we need to add the central beam of the cone to the impacted area, else some spots
            # fail to generate cones at all
            # Only do this for cones narrower than 60 degrees so that all cones in the base game don't need it, because
            # this apparently slows down threat display performance by a lot
            beam = None
            if self.burst_cone_params and self.burst_cone_params.angle < math.pi/6:
                beam = list(Bolt(self.level, self.origin, self.burst_cone_params.target, find_clear=not self.ignore_walls))

            for i in range(self.radius):
                next_stage = set()
                beam_next = None
                if beam and i < len(beam):
                    beam_next = beam[i]
                    next_stage.add(beam_next)

                for point in last_stage:
                    points = self.level.get_points_in_ball(point.x, point.y, ball_radius, diag=self.expand_diagonals)
                    next_stage.update(points)

                next_stage.difference_update(already_exploded)

                if not self.ignore_walls:
                    next_stage = [p for p in next_stage if self.level.tiles[p.x][p.y].can_see]

                if self.burst_cone_params:
                    next_stage = [p for p in next_stage if self.is_in_burst(p) or p == beam_next]

                already_exploded.update(next_stage)
                yield next_stage
                last_stage = next_stage

    if cls is RestlessDeadBuff:

        def on_init(self):
            self.global_triggers[EventOnDeath] = lambda evt: on_death(self, evt)
            self.name = "Restless Dead"
            self.color = Tags.Dark.color	

        def on_death(self, evt):
            if not self.owner.level.are_hostile(self.owner, evt.unit):
                return
            if Tags.Living in evt.unit.tags:
                self.owner.level.queue_spell(self.raise_skeleton(evt.unit))
            elif Tags.Construct in evt.unit.tags and self.spell.get_stat('salvage'):
                self.owner.level.queue_spell(self.raise_golem(evt.unit))
            if (Tags.Fire in evt.unit.tags or Tags.Lightning in evt.unit.tags or Tags.Ice in evt.unit.tags) and self.spell.get_stat('spirit_catcher'):
                self.owner.level.queue_spell(self.grant_sorcery(evt.unit))

        def raise_skeleton(self, unit):
            if unit and unit.cur_hp <= 0 and not self.owner.level.get_unit_at(unit.x, unit.y):
                skeleton = curr_module.raise_skeleton(self.owner, unit, source=self.spell, summon=False)
                if not skeleton:
                    return
                skeleton.spells[0].damage = self.spell.get_stat('minion_damage')
                self.spell.summon(skeleton, target=unit, radius=0)
                yield

    if cls is FlameGateBuff:

        def on_applied(self, owner):
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.owner_triggers[EventOnPass] = self.on_pass
            self.color = Tags.Fire.color

    if cls is StoneAuraBuff:

        def on_init(self):
            self.name = "Petrification Aura"
            self.description = "%s nearby enemies each turn" % ("Glassify" if self.spell.get_stat("glassify") else "Petrify")
            self.color = Tags.Glass.color if self.spell.get_stat("glassify") else Color(180, 180, 180)

    if cls is IronSkinBuff:

        def on_init(self):
            self.color = Tags.Metallic.color
            for tag in [Tags.Physical, Tags.Fire, Tags.Lightning]:
                self.resists[tag] = self.spell.get_stat('resist')
            if self.spell.get_stat('resist_arcane'):
                self.resists[Tags.Arcane] = self.spell.get_stat('resist')

    if cls is HolyShieldBuff:

        def __init__(self, resist):
            Buff.__init__(self)
            self.color = Tags.Holy.color
            self.name = "Holy Armor"
            self.buff_type = BUFF_TYPE_BLESS
            for tag in [Tags.Fire, Tags.Lightning, Tags.Dark, Tags.Physical]:
                self.resists[tag] = resist

    if cls is DispersionFieldBuff:

        def on_init(self):
            self.name = "Dispersion Field"
            self.description = "Teleport nearby enemies away each turn"
            self.color = Tags.Translocation.color

    if cls is SearingSealBuff:

        def on_init(self):
            self.name = "Seal of Searing"
            self.color = Tags.Fire.color
            self.charges = 0
            self.stack_type = STACK_REPLACE
            self.buff_type = BUFF_TYPE_BLESS
            self.global_triggers[EventOnDamaged] = self.on_damage

    if cls is MercurizeBuff:

        def on_init(self):
            self.buff_type = BUFF_TYPE_CURSE
            self.name = "Mercurized"
            self.asset = ['status', 'mercurized']
            self.owner_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Metallic.color

        def on_death(self, evt):
            geist = Ghost()
            geist.name = "Mercurial %s" % self.owner.name
            geist.asset_name = "mercurial_geist"
            geist.max_hp = self.owner.max_hp
            geist.tags.append(Tags.Metallic)
            trample = SimpleMeleeAttack(damage=self.spell.get_stat('minion_damage'))
            geist.spells = [trample]

            if self.spell.get_stat('noxious_aura'):
                geist.buffs.append(DamageAuraBuff(damage=1, damage_type=Tags.Poison, radius=self.spell.get_stat("radius", base=2)))
            if self.spell.get_stat('vengeance'):
                geist.buffs.append(MercurialVengeance(self.spell))
            
            self.owner.level.queue_spell(do_summon(self, geist))

        def do_summon(self, geist):
            self.spell.summon(geist, target=self.owner)
            yield

    if cls is MagnetizeBuff:

        def on_init(self):
            self.name = "Magnetized"
            self.asset = ['status', 'magnetized']
            self.color = Tags.Metallic.color

    if cls is BurningBuff:

        def on_init(self):
            self.name = "Burning (%d)" % self.damage
            self.description = "At end of this unit's turn, it takes %d damage and burning expires." % self.damage
            self.asset = ['status', 'burning']
            self.color = Tags.Fire.color
            self.stack_type = STACK_INTENSITY

    if cls is BurningShrineBuff:

        def on_damage(self, evt):
            if not isinstance(evt.source, self.spell_class) or evt.source.owner != self.owner or not are_hostile(evt.unit, self.owner):
                return
            evt.unit.apply_buff(BurningBuff(evt.damage))

    if cls is EntropyBuff:

        def on_init(self):
            self.name = "Entropy"
            self.resists[Tags.Arcane] = -25
            self.resists[Tags.Dark] = -25
            self.buff_type = BUFF_TYPE_CURSE
            self.color = Tags.Lightning.color

    if cls is EnervationBuff:

        def on_init(self):
            self.name = "Enervation"
            self.resists[Tags.Fire] = -25
            self.resists[Tags.Lightning] = -25
            self.resists[Tags.Ice] = -25
            self.buff_type = BUFF_TYPE_CURSE
            self.color = Tags.Arcane.color

    if cls is OrbSpell:

        def can_cast(self, x, y):
            if self.get_stat('orb_walk') and self.get_orb(x, y):
                return True

            if self.caster.level.tiles[x][y].is_wall():
                return False

            path = self.caster.level.get_points_in_line(Point(self.caster.x, self.caster.y), Point(x, y))
            if len(path) < 2:
                return False

            start_point = path[1]
            if self.caster.level.tiles[start_point.x][start_point.y].is_wall():
                return False
            blocker = self.caster.level.get_unit_at(start_point.x, start_point.y)
            if blocker:
                return False

            return Spell.can_cast(self, x, y)

        def cast(self, x, y):
            existing = self.get_orb(x, y)
            if self.get_stat('orb_walk') and existing:
                for r in self.on_orb_walk(existing):
                    yield r
                return

            path = self.caster.level.get_points_in_line(Point(self.caster.x, self.caster.y), Point(x, y))
            if len(path) < 1:
                return

            start_point = path[1]

            # Clear a wall at the starting point if it exists so the unit can be placed
            if self.get_stat('melt_walls'):
                if self.caster.level.tiles[start_point.x][start_point.y].is_wall():
                    self.caster.level.make_floor(start_point.x, start_point.y)

            unit = ProjectileUnit()
            unit.name = self.name
            unit.stationary = True
            unit.team = self.caster.team
            unit.turns_to_death = len(path) - 2

            unit.max_hp = self.get_stat('minion_health')
            
            # path[0] = caster, path[1] = start_point, path[2] = first point to move to
            buff = OrbBuff(spell=self, dest=Point(x, y))
            unit.buffs.append(buff)
            
            self.on_make_orb(unit)
            blocker = self.caster.level.get_unit_at(start_point.x, start_point.y)

            # Should be taken care of by can_cast- but weird situations could cause this
            if blocker:
                return

            self.summon(unit, start_point)

    if cls is StormBreath:

        def get_description(self):
            return "Breathes a cone of storm clouds, dealing %d damage" % self.get_stat("damage")

        def per_square_effect(self, x, y):
            self.caster.level.add_obj(StormCloud(self.caster, self.get_stat("damage")), x, y)

    if cls is FireBreath:

        def get_description(self):
            return "Breathes a cone of %s dealing %d damage" % (self.damage_type.name.lower(), self.get_stat("damage"))

        def per_square_effect(self, x, y):
            self.caster.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)

    if cls is IceBreath:

        def on_init(self):
            self.name = "Ice Breath"
            self.damage = 7
            self.damage_type = Tags.Ice
            self.duration = 2

        def get_description(self):
            return "Breathes a cone of ice dealing %d damage and freezing units for %d turns" % (self.get_stat("damage"), self.get_stat('duration'))

        def per_square_effect(self, x, y):
            self.caster.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.apply_buff(FrozenBuff(), self.get_stat('duration'))

    if cls is VoidBreath:

        def per_square_effect(self, x, y):

            if not self.caster.level.tiles[x][y].is_chasm:
                self.caster.level.make_floor(x, y)
            
            self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Arcane, self)

    if cls is HolyBreath:

        def per_square_effect(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if unit and not are_hostile(self.caster, unit):
                # Dont heal or hurt friendly players.
                if not unit.is_player_controlled:
                    self.caster.level.deal_damage(x, y, -self.get_stat("damage"), Tags.Heal, self)
            else:
                self.caster.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)

    if cls is DarkBreath:

        def per_square_effect(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            
            self.caster.level.deal_damage(x, y, self.get_stat('damage'), self.damage_type, self)

            if unit and not unit.is_alive():
                curr_module.raise_skeleton(self.caster, unit)

    if cls is GreyGorgonBreath:

        def __init__(self):
            BreathWeapon.__init__(self)
            self.name = "Grey Gorgon Breath"
            self.damage = 9
            self.damage_type = Tags.Physical
            self.cool_down = 10
            self.range = 5
            self.angle = math.pi / 6.0
            self.duration = 2

        def get_description(self):
            return "Breathes a petrifying gas dealing %d physical damage and petrifying living creatures" % self.get_stat('damage')

        def per_square_effect(self, x, y):
            self.caster.level.show_effect(x, y, Tags.Petrification)
            unit = self.caster.level.get_unit_at(x, y)
            if unit and Tags.Living in unit.tags:
                self.caster.level.deal_damage(x, y, self.get_stat('damage'), self.damage_type, self)
                unit.apply_buff(PetrifyBuff(), self.get_stat("duration"))

    if cls is BatBreath:

        def get_description(self):
            return "Breathes a cone of bats dealing %d damage to occupied tiles and summoning bats in empty ones." % self.get_stat('damage')

        def per_square_effect(self, x, y):
            
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                self.caster.level.deal_damage(x, y, self.get_stat('damage'), self.damage_type, self)
            else:
                self.summon(Bat(), Point(x, y))

    if cls is DragonRoarBuff:

        def on_init(self):
            self.name = "Dragon Roar"
            self.color = Tags.Dragon.color
            self.stack_type = STACK_INTENSITY
            self.buff_type = BUFF_TYPE_BLESS
            self.global_bonuses["damage"] = self.spell.get_stat('damage')

        def on_applied(self, owner):

            owner.cur_hp += self.spell.get_stat('hp_bonus')
            owner.max_hp += self.spell.get_stat('hp_bonus')

            for spell in owner.spells:
                if isinstance(spell, BreathWeapon):
                    spell.cool_down -= 1
                    spell.cool_down = max(0, spell.cool_down)

        def on_unapplied(self):

            self.owner.max_hp -= self.spell.get_stat('hp_bonus')
            self.owner.cur_hp = min(self.owner.max_hp, self.owner.cur_hp)

            for spell in self.owner.spells:
                if isinstance(spell, BreathWeapon):
                    spell.cool_down += 1
                    spell.cool_down = max(0, spell.cool_down)

    if cls is HungerLifeLeechSpell:

        def cast(self, x, y):
            target = Point(x, y)

            for point in Bolt(self.caster.level, self.caster, target):
                # TODO- make a flash using something other than deal_damage
                self.caster.level.show_effect(point.x, point.y, Tags.Dark)
                yield

            damage_dealt = self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Dark, self)
            self.caster.deal_damage(-damage_dealt, Tags.Heal, self)

    if cls is BloodlustBuff:

        def on_init(self):
            self.buffed_spells = []

        def modify_spell(self, spell):
            if self.qualifies(spell):
                if spell.statholder and spell.statholder is not spell.caster:
                    return
                self.buffed_spells.append(spell)
                spell.damage += self.extra_damage

        def unmodify_spell(self, spell):
            if spell in self.buffed_spells:
                spell.damage -= self.extra_damage

    if cls is OrbControlSpell:

        def cast_instant(self, x, y, channel_cast=False):

            for u in self.caster.level.units:
                if u.team != self.caster.team:
                    continue
                buff = u.get_buff(OrbBuff)
                if buff:
                    path = self.caster.level.get_points_in_line(u, Point(x, y))[1:]
                    u.turns_to_death = len(path)
                    buff.dest = Point(x, y)

    if cls is SimpleBurst:

        def cast(self, x, y):
            damage = self.get_stat("damage")
            for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius'), ignore_walls=self.ignore_walls):
                for p in stage:
                    if p.x == self.caster.x and p.y == self.caster.y:
                        continue
                    dtype = random.choice(self.damage_type) if isinstance(self.damage_type, list) else self.damage_type
                    self.caster.level.deal_damage(p.x, p.y, damage, dtype, self)
                    if self.onhit:
                        unit = self.caster.level.get_unit_at(p.x, p.y)
                        if unit:
                            self.onhit(self.caster, unit)
                yield

        def can_threaten(self, x, y):
            if distance(self.caster, Point(x, y)) > self.get_stat("radius"):
                return False

            # Potential optimization- only make the aoe once per frame
            return Point(x, y) in list(self.get_impacted_tiles(self.caster.x, self.caster.y))

    if cls is PullAttack:

        def cast_instant(self, x, y):

            path = self.caster.level.get_points_in_line(self.caster, Point(x, y))
            for p in path[1:-1]:
                self.caster.level.flash(p.x, p.y, self.color)

            target_unit = self.caster.level.get_unit_at(x, y)

            if target_unit:
                pull(target_unit, self.caster, self.pull_squares)

                target_unit.deal_damage(self.get_stat("damage"), self.damage_type, self)

    if cls is LeapAttack:

        def cast(self, x, y):

            # Projectile

            leap_dest = self.get_leap_dest(x, y)
            if not leap_dest:
                return
            self.caster.invisible = True
            path = self.caster.level.get_points_in_line(Point(self.caster.x, self.caster.y), Point(leap_dest.x, leap_dest.y), find_clear=not self.is_ghost)
            self.caster.level.act_move(self.caster, leap_dest.x, leap_dest.y, teleport=True)
            for point in path:
                dtype = random.choice(self.damage_type) if isinstance(self.damage_type, list) else self.damage_type
                self.caster.level.leap_effect(point.x, point.y, dtype.color, self.caster)
                yield
            self.caster.invisible = False
            charge_bonus = self.charge_bonus * (len(path) - 2)
            self.caster.level.deal_damage(x, y, self.get_stat("damage") + charge_bonus, random.choice(self.damage_type) if isinstance(self.damage_type, list) else self.damage_type, self)

    if cls is MonsterVoidBeam:

        def cast_instant(self, x, y):
            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:]:
                self.caster.level.deal_damage(p.x, p.y, self.get_stat("damage"), Tags.Arcane, self)
                
                if not self.caster.level.tiles[p.x][p.y].can_see:
                    self.caster.level.make_floor(p.x, p.y)

    if cls is ButterflyLightning:

        def cast_instant(self, x, y):

            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y)):
                self.caster.level.deal_damage(p.x, p.y, self.get_stat("damage"), self.damage_type, self)

    if cls is FiendStormBolt:

        def cast_instant(self, x, y):
            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:]:
                self.caster.level.deal_damage(p.x, p.y, self.get_stat("damage"), self.damage_type, self)
                self.caster.level.add_obj(StormCloud(self.caster, self.damage), p.x, p.y)

    if cls is LifeDrain:

        def cast(self, x, y):
            damage = self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Dark, self)
            yield

            start = Point(self.caster.x, self.caster.y)
            target = Point(x, y)

            for point in Bolt(self.caster.level, target, start):
                # TODO- make a flash using something other than deal_damag, selfe
                self.caster.level.deal_damage(point.x, point.y, 0, Tags.Dark, self)
                yield

            self.caster.level.deal_damage(self.caster.x, self.caster.y, -damage, Tags.Heal, self)
            yield

    if cls is WizardLightningFlash:

        def cast(self, x, y):
            randomly_teleport(self.caster, self.get_stat("range"), flash=True, requires_los=False)
            yield

            points = [p for p in self.caster.level.get_points_in_los(self.caster) if not (p.x == self.caster.x and p.y == self.caster.y)]

            random.shuffle(points)
            points.sort(key = lambda u: distance(self.caster, u))

            for p in points:
                unit = self.caster.level.get_unit_at(p.x, p.y)
        
                if unit:                
                    self.caster.level.deal_damage(p.x, p.y, self.get_stat("damage"), Tags.Lightning, self)
                    unit.apply_buff(BlindBuff(), 1)
                    yield
                elif random.random() < .05:
                    self.caster.level.show_effect(p.x, p.y, Tags.Lightning)
                    yield		

    if cls is TideOfSin:

        def cast(self, x, y):
            for u in self.caster.level.get_units_in_los(self.caster):
                if not are_hostile(self.caster, u):
                    continue
                self.caster.level.show_path_effect(self.caster, u, Tags.Holy, minor=True)
                u.deal_damage(self.get_stat("damage"), Tags.Holy, self)
                if u.is_player_controlled:
                    drain_spell_charges(self.caster, u)
                yield

    if cls is WailOfPain:

        def on_init(self):
            self.name = "Cacophony"
            self.range = 0
            self.radius = 6
            self.damage = 22
            self.cool_down = 7
            self.damage_type = Tags.Dark

        def get_description(self):
            return "Deals %d damage to all enemies within %d tiles." % (self.get_stat("damage"), self.get_stat("radius"))

        def get_impacted_tiles(self, x, y):
            return list(self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, self.get_stat("radius")))

        def cast_instant(self, x, y):
            for p in self.get_impacted_tiles(x, y):
                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit and not are_hostile(self.caster, unit):
                    continue

                if not self.caster.level.tiles[p.x][p.y].can_see:
                    continue

                self.caster.level.deal_damage(p.x, p.y, self.get_stat("damage"), Tags.Dark, self)

        def get_ai_target(self):
            for p in self.get_impacted_tiles(self.caster.x, self.caster.y):
                u = self.caster.level.get_unit_at(p.x, p.y)
                if u and are_hostile(u, self.caster):
                    return self.caster
            return None

        def can_threaten(self, x, y):
            return distance(self.caster, Point(x, y)) <= self.get_stat("radius")

    if cls is HagSwap:

        def can_threaten(self, x, y):
            return distance(self.caster, Point(x, y)) <= self.get_stat("range") and (not self.get_stat("requires_los") or self.caster.level.can_see(self.caster.x, self.caster.y, x, y))

    if cls is Approach:

        def can_cast(self, x, y):
            path = self.caster.level.find_path(self.caster, Point(x, y), self.caster, pythonize=True)
            if not path:
                return False
            if len(path) > self.get_stat("range"):
                return False
            return Spell.can_cast(self, x, y)

    if cls is MonsterTeleport:

        def cast_instant(self, x, y):
            randomly_teleport(self.caster, self.get_stat("range"), flash=True, requires_los=self.self.get_stat("requires_los"))

    if cls is SimpleRangedAttack:

        def get_ai_target(self):

            if self.radius:
                return self.get_corner_target(self.get_stat("radius"))
            else:
                return Spell.get_ai_target(self)

        def can_threaten(self, x, y):
            if self.radius:
                return self.can_threaten_corner(x, y, self.get_stat("radius"))
            else:
                return Spell.can_threaten(self, x, y)

        def hit(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            dtype = self.damage_type
            if isinstance(dtype, list):
                dtype = random.choice(dtype)
            dealt = self.caster.level.deal_damage(x, y, self.get_stat('damage'), dtype, self)
            if unit and self.onhit:
                self.onhit(self.caster, unit)
            if unit and self.buff:
                unit.apply_buff(self.buff(), self.get_stat("duration", base=self.buff_duration) if self.buff_duration > 0 else 0)
            if dealt and self.drain:
                self.caster.deal_damage(-dealt, Tags.Heal, self)

        def get_description(self):
            
            desc = self.description + '\n'
            if self.beam:
                desc += "Beam attack\n"
            
            if self.melt:
                desc += "Melts through walls\n"
            elif not self.requires_los:
                desc += "Ignores walls\n"

            #if isinstance(self.damage_type, list):
            #	desc += "Randomly deals %s damage\n" % ' or '.join(t.name for t in self.damage_type)
            
            if self.cast_after_channel:
                desc += "Cast Time: %d turns\n" % self.max_channel
            elif self.max_channel:
                desc += "Can be channeled for up to %d turns\n" % self.max_channel

            if self.buff:
                if self.buff_duration > 0:
                    desc += "Applies %s for %d turns\n" % (self.buff_name, self.get_stat("duration", base=self.buff_duration))
                else:
                    desc += "Applies %s\n" % (self.buff_name)

            if self.siege:
                desc += "Must be at full HP to fire.\nLoses half max HP on firing."

            if self.drain:
                desc += "Heals caster for damage dealt"

            if self.suicide:
                desc += "Kills the caster"

            # Remove trailing \n
            desc = desc.strip()
            return desc

    if cls is WizardNightmare:

        def get_ai_target(self):
            for u in self.caster.level.get_units_in_ball(self.caster, radius=self.get_stat("radius")):
                if are_hostile(u, self.caster):
                    return self.caster
            return None

    if cls is WizardHealAura:

        def get_ai_target(self):
            for u in self.caster.level.get_units_in_ball(self.caster, radius=self.get_stat("radius")):
                if not are_hostile(u, self.caster) and u.cur_hp < u.max_hp:
                    return self.caster
            return None

    if cls is WizardBloodlust:

        def get_description(self):
            return "Increases damage by %d for all allied units within %d tiles for %d turns" % (self.bonus, self.get_stat("radius"), self.get_stat("duration"))

        def cast_instant(self, x, y):
            for p in self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, self.get_stat("radius")):
                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit and not are_hostile(unit, self.caster):
                    bloodlust = BloodrageBuff(self.bonus)
                    unit.apply_buff(bloodlust, self.get_stat("duration"))

    if cls is WizardBlizzard:

        def get_ai_target(self):
            return self.get_corner_target(self.get_stat("radius"))

    if cls is SpiritShield:

        def get_ai_target(self):
            # Cast only if there is atleast 1 unshielded undead ally in los
            units = self.caster.level.get_units_in_ball(self.caster, self.get_stat("radius"))
            for u in units:
                if are_hostile(self.caster, u):
                    continue
                if Tags.Undead in u.tags and u.shields < 1:
                    return self.caster
            return None
            
        def on_init(self):
            self.shields = 1
            self.name = "Spirit Shield"
            self.radius = 6
            self.description = "Grant all undead allies within %i tiles 1 shield, to a max of %d" % (self.get_stat("radius"), self.shields)
            self.range = 0

        def cast_instant(self, x, y):
            units = [u for u in self.caster.level.get_units_in_ball(Point(x, y), self.get_stat("radius")) if not self.caster.level.are_hostile(u, self.caster)]
            for unit in units:
                if Tags.Undead in unit.tags and unit.shields < self.shields:
                    unit.add_shields(1)

    if cls is WizardThunderStrike:

        def get_ai_target(self):
            # Try to hit something directly but settle for stunning something
            return Spell.get_ai_target(self) or self.get_corner_target(self.get_stat("radius"))

    if cls is SimpleCurse:

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                buff = self.buff()
                buff.caster = self.caster
                unit.apply_buff(buff, self.get_stat("duration") if self.duration else 0)
                if self.effect:
                    for p in self.caster.level.get_points_in_line(self.caster, Point(x, y)):
                        self.caster.level.show_effect(p.x, p.y, self.effect)

    if cls is SimpleSummon:

        def cast(self, x, y, channel_cast=False):
            if self.global_summon:
                ex = self.spawn_func()
                targets = [t for t in self.caster.level.iter_tiles() if self.caster.level.can_stand(t.x, t.y, ex)]
                if targets:
                    target = random.choice(targets)
                    x = target.x
                    y = target.y

            if self.max_channel and not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)), self.max_channel)
                return

            duration = self.get_stat("duration")
            for _ in range(self.num_summons):
                unit = self.spawn_func()
                if self.duration:
                    unit.turns_to_death = duration
                apply_minion_bonuses(self.caster.source, unit)
                unit.source = self.caster.source
                self.summon(unit, Point(x, y), sort_dist=False)
                if self.path_effect:
                    self.owner.level.show_path_effect(self.owner, unit, self.path_effect, minor=True)
                yield

    if cls is GlassyGaze:

        def cast(self, x, y):
            start = Point(self.caster.x, self.caster.y)
            target = Point(x, y)

            for point in Bolt(self.caster.level, start, target):
                self.caster.level.flash(point.x, point.y, Tags.Glassification.color)
                yield

            unit = self.caster.level.get_unit_at(x, y)
            unit.apply_buff(GlassPetrifyBuff(), self.get_stat("duration"))
            yield

        def get_description(self):
            return "Turns victim to glass for %d turns" % self.get_stat("duration")

    if cls is GhostFreeze:

        def get_description(self):
            return "Sacrifices an adjacent friendly ghost to freeze one target for %d turns" % self.get_stat("duration")

    if cls is SmokeBomb:

        def cast(self, x, y):
            target = Point(x, y)

            for stage in Burst(self.caster.level, target, self.get_stat('radius')):
                for point in stage:
                    damage = self.get_stat('damage')
                    self.caster.level.deal_damage(point.x, point.y, 0, self.damage_type, self)
                    unit = self.caster.level.get_unit_at(point.x, point.y)
                    if unit and unit != self.caster:
                        unit.apply_buff(BlindBuff(), self.get_stat("duration"))
                yield

            tp_targets = [t for t in self.caster.level.iter_tiles() if t.can_walk and 6 < distance(self.caster, t) < 10 and not t.unit]
            if tp_targets:
                tp_target = random.choice(tp_targets)
                self.caster.level.act_move(self.caster, tp_target.x, tp_target.y, teleport=True)
                self.caster.level.show_effect(self.caster.x, self.caster.y, Tags.Dark)
            self.caster.apply_buff(CowardBuff(), self.cool_down)
            return

    if cls is WizardBloodboil:

        def cast(self, x, y):

            for unit in self.caster.level.get_units_in_los(self.caster):
                if not self.caster.level.are_hostile(self.caster, unit) and unit != self.caster:
                    buff = Spells.BloodlustBuff(self)
                    buff.extra_damage = 4
                    unit.apply_buff(buff, self.get_stat("duration"))

                    # For the graphic
                    unit.deal_damage(0, Tags.Fire, self)
                    yield

    if cls is CloudGeneratorBuff:

        def __init__(self, cloud_func, radius, chance):
            Buff.__init__(self)
            self.cloud_func = cloud_func
            self.radius = radius
            self.chance = chance
            name = cloud_func(None).name
            self.description = "Spawns %ss up to %d tiles away" % (name, radius)
            if name == "Blizzard":
                self.color = Tags.Ice.color
            elif name == "Storm Cloud":
                self.color = Tags.Lightning.color

    if cls is TrollRegenBuff:

        def get_tooltip_color(self):
            return Tags.Heal.color

    if cls is DamageAuraBuff:

        def __init__(self, damage, damage_type, radius, friendly_fire=False, melt_walls=False):
            Buff.__init__(self)
            self.damage = damage
            self.damage_type = damage_type
            self.radius = radius
            self.friendly_fire = friendly_fire
            self.source = None
            if isinstance(self.damage_type, Tag):
                self.name = "%s Aura" % self.damage_type.name
                self.color = self.damage_type.color
            else:
                self.name = "Damage Aura" 

            # Not used in base class, used in inherited classes
            self.damage_dealt = 0

            self.melt_walls = melt_walls

    if cls is CommonContent.ElementalEyeBuff:

        def __init__(self, damage_type, damage, freq):
            Buff.__init__(self)
            self.damage_type = damage_type
            self.damage = damage
            self.freq = freq
            self.cooldown = freq
            self.name = "Elemental Eye"
            self.color = self.damage_type.color

    if cls is RegenBuff:

        def __init__(self, heal):
            Buff.__init__(self)
            self.heal = heal
            self.stack_type = STACK_INTENSITY
            self.name = "Regeneration %d" % heal
            self.description = "Regenerates %d HP per turn" % self.heal
            self.buff_type = BUFF_TYPE_BLESS
            self.asset = ['status', 'heal']
            self.color = Tags.Heal.color

    if cls is ShieldRegenBuff:

        def __init__(self, shield_max, shield_freq):
            Buff.__init__(self)
            self.shield_max = shield_max
            self.shield_freq = shield_freq
            self.turns = 0
            self.buff_type = BUFF_TYPE_BLESS
            self.color = Tags.Shield.color

    if cls is DeathExplosion:

        def __init__(self, damage, radius, damage_type):
            Buff.__init__(self)
            self.description = "On death, deals %d %s damage to all tiles in a radius of %d" % (damage, damage_type.name, radius)
            self.damage = damage
            self.damage_type = damage_type
            self.radius = radius
            self.name = "Death Explosion"
            self.color = self.damage_type.color

    if cls is VolcanoTurtleBuff:

        def on_applied(self, owner):
            self.color = Tags.Fire.color

    if cls is SpiritBuff:

        def __init__(self, tag):
            Buff.__init__(self)
            self.tag = tag
            self.color = self.tag.color

    if cls is NecromancyBuff:

        def on_applied(self, owner):
            self.global_triggers[EventOnDeath] = self.on_death
            self.radius = 10
            self.color = Tags.Undead.color

    if cls is SporeBeastBuff:

        def on_init(self):
            self.name = "Spores"
            self.healing = 8
            self.radius = 2
            self.owner_triggers[EventOnDamaged] = self.on_damage_taken
            self.color = Tags.Heal.color

    if cls is SpikeBeastBuff:

        def on_init(self):
            self.name = "Spikebeast Spikes"
            self.damage = 8
            self.radius = 2
            self.owner_triggers[EventOnDamaged] = self.on_damage_taken
            self.color = Tags.Physical.color

    if cls is BlizzardBeastBuff:

        def on_init(self):
            self.name = "Ice Spores"
            self.radius = 2
            self.owner_triggers[EventOnDamaged] = self.on_damaged
            self.description = "When damaged, creates 2 blizzards up to %d tiles away" % self.radius
            self.color = Tags.Ice.color

    if cls is FireBomberBuff:

        def on_init(self):
            self.name = "Suicide Explosion"
            self.radius = 2
            self.damage = 12
            self.clusters = 0
            self.color = Tags.Fire.color

    if cls is SpiderBuff:

        def on_init(self):
            self.color = Tags.Spider.color

    if cls is MushboomBuff:

        def on_init(self):
            self.owner_triggers[EventOnDeath] = self.on_death
            example = self.buff()
            self.buff_name = example.name
            self.name = "Mushboom Burst"
            self.color = example.color

        def get_tooltip(self):
            return "On death, applies %d turns of %s to adjacent units" % (self.apply_duration, self.buff_name)

    if cls is RedMushboomBuff:

        def on_init(self):
            self.name = "Fire Spores"
            self.damage = 9
            self.owner_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Fire.color
        
        def get_tooltip(self):
            return "On death, deals %i fire damage to adjacent units" % self.damage

        def explode(self):
            for p in self.owner.level.get_adjacent_points(self.owner):
                self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Fire, self)
            yield

    if cls is ThornQueenThornBuff:

        def on_init(self):
            self.radius = 6
            self.color = Tags.Nature.color

    if cls is LesserCultistAlterBuff:

        def on_init(self):
            self.description = "Whenever a cultist dies, randomly spawns 3 fire or spark imps"
            self.global_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Demon.color

    if cls is GreaterCultistAlterBuff:

        def on_init(self):

            self.charges = 0
            self.global_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Demon.color

    if cls is CultNecromancyBuff:

        def on_applied(self, owner):
            self.global_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Undead.color

    if cls is MagmaShellBuff:

        def on_init(self):
            self.resists[Tags.Physical] = 50
            self.resists[Tags.Fire] = 50
            self.buff_type = BUFF_TYPE_BLESS
            self.name = "Magma Shell"
            self.asset = ['status', 'magma_shell']
            self.color = Tags.Fire.color

    if cls is ToxicGazeBuff:

        def on_init(self):
            self.name = "Toxic Gaze"
            self.global_triggers[EventOnDamaged] = self.on_damaged
            self.description = "Whenever an enemy unit in line of sight takes poison damage, redeal that damage as dark damage."
            self.color = Tags.Dark.color

    if cls is ConstructShards:

        def on_init(self):
            self.name = "Necromechanomancery"
            self.global_triggers[EventOnDeath] = self.on_death
            self.description = "Whenever a friendly construct dies, deal 6 fire or physical damage to up to 3 enemies in a 4 tiles burst"
            self.color = Tags.Construct.color

    if cls is IronShell:

        def on_init(self):
            self.resists[Tags.Physical] = 50
            self.resists[Tags.Fire] = 50
            self.buff_type = BUFF_TYPE_BLESS
            self.name = "Iron Plating"
            self.color = Tags.Metallic.color

    if cls is ArcanePhoenixBuff:

        def on_init(self):
            self.color = Tags.Arcane.color
            self.owner_triggers[EventOnDeath] = self.on_death
            self.name = "Phoenix Starfire"

    if cls is IdolOfSlimeBuff:

        def on_init(self):

            self.description = "Whenever a non slime ally dies, summons a slime where that ally died."
            self.global_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Slime.color

    if cls is CrucibleOfPainBuff:

        def on_init(self):

            self.global_triggers[EventOnDamaged] = self.on_damage
            self.counter = 0
            self.counter_max = 300
            self.description = "Spawn a furnace hound for every 300 damage dealt to any unit."
            self.color = Tags.Demon.color

    if cls is FieryVengeanceBuff:

        def on_init(self):
            self.global_triggers[EventOnDeath] = self.on_death
            self.description = "Whenever an ally dies, deals 9 fire damage to a random enemy unit up to 3 tiles away."
            self.name = "Idol of Fiery Vengeance"
            self.color = Tags.Fire.color

    if cls is ConcussiveIdolBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.description = "Whenever an enemy takes damage, it is stunned for 1 turn."
            self.name = "Concussive Idol"
            self.color = Stun().color

    if cls is VampirismIdolBuff:

        def on_init(self):
            self.name = "Idol of Vampirism"
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.description = "Whenever an ally deals damage, it heals for half that much HP."
            self.color = Tags.Dark.color

    if cls is TeleportyBuff:

        def get_tooltip_color(self):
            return Tags.Translocation.color

    if cls is LifeIdolBuff:

        def on_init(self):
            self.name = "Aura of Life"
            self.description = "Each turn all friendly living units are healed for 3"
            self.color = Tags.Living.color

    if cls is PrinceOfRuin:

        def trigger(self, evt):
            candidates = [u for u in self.owner.level.get_units_in_ball(evt.unit, self.get_stat("radius")) if are_hostile(self.owner, u)]
            candidates = [u for u in candidates if self.owner.level.can_see(evt.unit.x, evt.unit.y, u.x, u.y)]

            if candidates:
                target = random.choice(candidates)
                for p in self.owner.level.get_points_in_line(evt.unit, target, find_clear=True)[1:-1]:
                    self.owner.level.show_effect(p.x, p.y, evt.damage_event.damage_type)
                target.deal_damage(self.get_stat("damage"), evt.damage_event.damage_type, self)
            yield

    if cls is StormCaller:

        def on_damage(self, evt):
            if not are_hostile(self.owner, evt.unit):
                return

            if evt.damage_type not in [Tags.Ice, Tags.Lightning]:
                return

            cloud = random.choice([BlizzardCloud(self.owner), StormCloud(self.owner)])
            cloud.damage += self.get_stat('damage') # Apply damage bonuses
            cloud.duration = self.get_stat("duration")

            if not self.owner.level.tiles[evt.unit.x][evt.unit.y].cloud:
                self.owner.level.add_obj(cloud, evt.unit.x, evt.unit.y)
            else:
                possible_points = self.owner.level.get_points_in_ball(evt.unit.x, evt.unit.y, 1, diag=True)
                def can_cloud(p):
                    tile = self.owner.level.tiles[p.x][p.y]
                    if tile.cloud:
                        return False
                    if tile.is_wall():
                        return False
                    return True

                possible_points = [p for p in possible_points if can_cloud(p)]
                if possible_points:
                    point = random.choice(possible_points)
                    self.owner.level.add_obj(cloud, point.x, point.y)

    if cls is Horror:

        def on_init(self):
            self.name = "Horror"
            self.tags = [Tags.Dark]
            self.level = 5
            self.global_triggers[EventOnDeath] = self.on_death
            self.duration = 5
            self.num_targets = 3

        def get_description(self):
            return ("Whenever an enemy dies to [dark] damage, up to [{num_targets}:num_targets] random enemies in line of sight of that enemy are [stunned] for [{duration}_turns:duration]").format(**self.fmt_dict())

        def on_death(self, evt):
            if evt.damage_event is not None and evt.damage_event.damage_type == Tags.Dark and self.owner.level.are_hostile(evt.unit, self.owner):
                def eligible(u):
                    if u == evt.unit:
                        return False
                    if not self.owner.level.are_hostile(u, self.owner):
                        return False
                    if not self.owner.level.can_see(evt.unit.x, evt.unit.y, u.x, u.y):
                        return False
                    return True

                candidates = [u for u in self.owner.level.units if eligible(u)]
                random.shuffle(candidates)
                for c in candidates[:self.get_stat("num_targets")]:
                    c.apply_buff(Stun(), self.get_stat('duration'))

    if cls is FrozenSouls:

        def on_init(self):
            self.name = "Icy Vengeance"
            self.tags = [Tags.Ice, Tags.Dark]
            self.level = 6
            self.global_triggers[EventOnDeath] = self.on_death
            self.radius = 5
            self.num_targets = 3

        def get_description(self):
            return ("Whenever one of your minions dies, up to [{num_targets}:num_targets] random enemies in a [{radius}_tile:radius] radius take [ice] damage equal to half the dead minion's max HP.").format(**self.fmt_dict())

        def on_death(self, evt):
            if are_hostile(evt.unit, self.owner):
                return
            self.owner.level.queue_spell(self.do_damage(evt))

        def do_damage(self, evt):
            units = self.owner.level.get_units_in_ball(evt.unit, self.get_stat('radius'))
            units = [u for u in units if are_hostile(self.owner, u)]
            random.shuffle(units)
            for unit in units[:self.get_stat("num_targets")]:
                for p in self.owner.level.get_points_in_line(evt.unit, unit)[1:-1]:
                    self.owner.level.show_effect(p.x, p.y, Tags.Ice)
                unit.deal_damage(evt.unit.max_hp // 2, Tags.Ice, self)
                yield

    if cls is ShrapnelBlast:

        def on_init(self):
            self.name = "Shrapnel Blast"

            self.tags = [Tags.Fire, Tags.Metallic, Tags.Sorcery]
            self.level = 3
            self.max_charges = 6
            self.radius = 4
            self.range = 7
            self.damage = 12
            self.requires_los = False
            self.num_targets = 16

            self.upgrades['num_targets'] = (12, 3, "More Shrapnel", "12 more shrapnel shards are shot")
            self.upgrades['puncture'] = (1, 2, "Puncturing Blast", "The shrapnel now target all tiles in the affected radius, rather than only tiles in line of sight of the destroyed wall.")
            self.upgrades['homing'] = (1, 7, "Magnetized Shards", "The shrapnel shards always target enemies if possible.")

        def get_description(self):
            return ("Detonate target wall tile.\n" 
                    "Enemies adjacent to the wall tile take [{damage}_fire:fire] damage.\n"
                    "The explosion fires [{num_targets}_shards:num_targets] at random tiles in a [{radius}_tile:radius] radius. Only tiles in line of sight of the destroyed wall are targeted.\n"
                    "Each shard deals [{damage}_physical:physical] damage.").format(**self.fmt_dict())

    if cls is ShieldSightSpell:

        def can_cast(self, x, y):
            units = [u for u in self.caster.level.get_units_in_los(Point(x, y)) if not are_hostile(u, self.caster)]
            if all(unit.shields >= self.shields for unit in units):
                return False
            return Spell.can_cast(self, x, y)

    if cls is GlobalAttrBonus:

        def __init__(self, attr, bonus):
            Buff.__init__(self)
            self.attr = attr
            self.bonus = bonus
            self.global_bonuses[attr] = bonus
            if attr in attr_colors.keys():
                self.color = attr_colors[attr]

    if cls is FaeThorns:

        def on_init(self):
            self.name = "Thorn Garden"

            self.tags = [Tags.Arcane, Tags.Nature]
            self.level = 5
            
            self.minion_health = 10
            self.minion_damage = 4
            self.minion_duration = 6
            self.num_summons = 2

            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast

        def get_description(self):
            return ("Whenever you cast an [arcane] or [nature] spell, summon [{num_summons}:num_summons] fae thorns near the target.\n"
                    "Fae Thorns have [{minion_health}_HP:minion_health], and cannot move.\n"
                    "Fae Thorns have a melee attack which deals [{minion_damage}_physical:physical] damage.\n"
                    "The thorns vanish after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

        def do_summons(self, evt):
            for _ in range(self.get_stat("num_summons")):
                thorn = FaeThorn()

                thorn.max_hp = self.get_stat('minion_health')
                thorn.spells[0].damage = self.get_stat('minion_damage')

                thorn.turns_to_death = self.get_stat('minion_duration')

                self.summon(thorn, evt, radius=2, sort_dist=False)
            yield

    if cls is Teleblink:

        def on_init(self):
            self.tags = [Tags.Arcane, Tags.Translocation]
            self.level = 5
            self.name = "Glittering Dance"
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.casts = 0

            self.minion_damage = 4
            self.heal = 5

            self.minion_range = 4
            self.minion_duration = 10
            self.minion_health = 9
            self.shields = 1
            self.num_summons = 2
            self.cast_last = False

        def get_description(self):
            return ("When you cast three [arcane] spells in a row, regain a charge of a random [translocation] spell and summon [{num_summons}:num_summons] faeries.\n"
                    "The faeries fly, and have [{minion_health}_HP:minion_health], [{shields}_SH:shields], [75_arcane:arcane] resistance, and a passive blink.\n"
                    "The faeries can heal allies for [{heal}_HP:heal], with a range of [{minion_range}_tiles:minion_range].\n"
                    "The faeries have a [{minion_damage}_arcane:arcane] damage attack, with a range of [{minion_range}_tiles:minion_range].\n"
                    "The faeries vanish after [{minion_duration}_turns:minion_duration].\n").format(**self.fmt_dict())

        def on_spell_cast(self, evt):
            if Tags.Arcane in evt.spell.tags:
                if self.casts < 2:
                    self.casts += 1
                    self.cast_last = True
                else:
                    self.casts = 0
                    self.cast_last = False
                    candidates = [s for s in self.owner.spells if Tags.Translocation in s.tags and s.cur_charges < s.get_stat('max_charges')]
                    if candidates:
                        candidate = random.choice(candidates)
                        candidate.cur_charges += 1

                    for _ in range(self.get_stat("num_summons")):
                        p = self.owner.level.get_summon_point(self.owner.x, self.owner.y, sort_dist=False, flying=True, radius_limit=4)
                        if not p:
                            continue

                        unit = Unit()
                        unit.sprite.char = 'f'
                        unit.sprite.color = Color(252, 141, 249)
                        unit.name = "Good Faery"
                        unit.description = "A capricious creature who delights in providing comfort to wizards"
                        unit.max_hp = self.minion_health
                        unit.shields = self.get_stat('shields')
                        unit.buffs.append(TeleportyBuff(chance=.5))
                        unit.spells.append(HealAlly(heal=self.get_stat('heal'), range=self.get_stat('minion_range') + 2))
                        unit.spells.append(SimpleRangedAttack(damage=self.get_stat('minion_damage'), range=self.get_stat('minion_range'), damage_type=Tags.Arcane))
                        unit.turns_to_death = self.get_stat('minion_duration')
                        unit.tags = [Tags.Nature, Tags.Arcane, Tags.Living]
                        unit.resists[Tags.Arcane] = 75
                        self.summon(unit, target=p)

    if cls is AfterlifeShrineBuff:

        def on_summon(self, unit):
            existing = unit.get_buff(ReincarnationBuff)
            if existing:
                existing.lives += 1
            buff = ReincarnationBuff(1)
            buff.buff_type = BUFF_TYPE_PASSIVE
            unit.apply_buff(buff)

    if cls is FrozenSkullShrineBuff:

        def on_init(self):
            OnKillShrineBuff.on_init(self)
            self.duration = 2
            self.num_targets = 4

        def on_kill(self, unit):
            targets = self.owner.level.get_units_in_los(unit)
            targets = [t for t in targets if are_hostile(self.owner, t)]
            if not targets:
                return
            random.shuffle(targets)
            duration = self.get_stat("duration")
            for u in targets[:self.get_stat("num_targets")]:
                u.apply_buff(FrozenBuff(), duration)

        def get_description(self):
            return ("On kill, [freeze] up to [{num_targets}:num_targets] enemies in line of sight of the slain unit for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is WhiteCandleShrineBuff:

        def on_init(self):
            ShrineSummonBuff.on_init(self)
            self.minion_range = 4

        def on_summon(self, unit):
            dtype = random.choice([Tags.Holy, Tags.Fire])
            damage = unit.source.get_stat('minion_damage')
            damage = max(1, damage)
            bolt = SimpleRangedAttack(damage=damage, damage_type=dtype, range=self.get_stat("minion_range"))
            bolt.name = "Candle Bolt"
            bolt.cool_down = 2
            unit.add_spell(bolt, prepend=True)

        def get_description(self):
            return ("The chosen spell's summoned minions randomly gain a [holy] or [fire] bolt attack.\nThe attack deals damage equal to the spell's [minion_damage:minion_damage] stat, has a [2_turn:cooldown] cooldown and has a range of [{minion_range}_tiles:range].").format(**self.fmt_dict())

    if cls is FaeShrineBuff:

        def on_init(self):
            ShrineSummonBuff.on_init(self)
            self.minion_range = 4

        def on_summon(self, unit):

            phasing = TeleportyBuff()
            unit.apply_buff(phasing)

            heal = FaeShrineHeal(2 + self.spell_level, range=self.get_stat("minion_range"))
            heal.name = "Fae Heal"
            heal.cool_down = 3
            unit.add_spell(heal, prepend=True)

        def get_description(self):
            return ("Summoned minions gain a healing spell and passive short range teleportation.\nThe healing spell heals 2 plus the spell's level HP, and has a [{minion_range}_tile:range] range.").format(**self.fmt_dict())

    if cls is FrozenShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.duration = 2

        def on_damage(self, evt):
            if not evt.source:
                return

            sources = [evt.source]
            if evt.source.owner and evt.source.owner.source:
                sources.append(evt.source.owner.source)

            if not any(isinstance(source, self.spell_class) and source.owner is self.owner for source in sources):
                return

            if evt.damage_type != Tags.Ice:
                return

            evt.unit.apply_buff(FrozenBuff(), self.get_stat("duration"))

        def get_description(self):
            return ("[Ice] damage from this spell or minions summoned by this spell causes [{duration}_turns:duration] of [freeze].").format(**self.fmt_dict())

    if cls is CharredBoneShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDeath] = self.on_death
            self.radius = 4
            self.num_targets = 4

        def do_damage(self, evt):
            units = self.owner.level.get_units_in_ball(evt.unit, self.get_stat("radius"))
            units = [u for u in units if are_hostile(self.owner, u)]
            random.shuffle(units)
            for unit in units[:self.get_stat("num_targets")]:
                for p in self.owner.level.get_points_in_line(evt.unit, unit)[1:-1]:
                    self.owner.level.show_effect(p.x, p.y, Tags.Fire)
                unit.deal_damage(evt.unit.max_hp // 2, Tags.Fire, self)
                yield

        def get_description(self):
            return ("Whenever a minion summoned by this spell dies, it deals half its HP as [fire] damage to up to [{num_targets}:num_targets] random enemy units up to [{radius}_tiles:radius] away.").format(**self.fmt_dict())

    if cls is SoulpowerShrineBuff:

        def on_init(self):
            OnKillShrineBuff.on_init(self)
            self.duration = 10

        def on_kill(self, unit):
            if Tags.Living in unit.tags or Tags.Demon in unit.tags:
                self.owner.apply_buff(SoulpowerBuff(), self.get_stat("duration"))

        def get_description(self):
            return ("Whenever you kill a [living] or [demon] unit with this spell, all your spells gain [4_damage:damage] for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is BrightShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.duration = 3

        def on_damage(self, evt):
            if not evt.source:
                return
            if not isinstance(evt.source, self.spell_class):
                return
            if not evt.source.owner == self.owner:
                return
            evt.unit.apply_buff(BlindBuff(), self.get_stat("duration"))

        def get_description(self):
            return ("Damaged targets are [blinded] for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is GreyBoneShrineBuff:

        def on_init(self):
            ShrineSummonBuff.on_init(self)
            self.num_summons = 2

        def on_summon(self, unit):
            hp = max(1, unit.max_hp // 4)
            spawn = lambda : BoneShambler(hp)
            buff = SpawnOnDeath(spawn, self.get_stat("num_summons"))
            buff.apply_bonuses = False
            buff.buff_type = BUFF_TYPE_PASSIVE
            unit.apply_buff(buff)

        def get_description(self):
            return ("Summoned minions split into [{num_summons}:num_summons] bone shamblers on death.\nEach bone shambler has 1/4th the HP of the original summon.").format(**self.fmt_dict())

    if cls is StoningShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDeath] = self.on_death
            self.num_targets = 2
            self.duration = 3

        def on_death(self, evt):
            if not are_hostile(evt.unit, self.owner):
                return
            if not evt.damage_event or not self.is_enhanced_spell(evt.damage_event.source, allow_minion=True):
                return

            enemies = [u for u in self.owner.level.get_units_in_los(evt.unit) if are_hostile(u, self.owner) and u is not evt.unit]
            random.shuffle(enemies)
            duration = self.get_stat("duration")
            for e in enemies[:self.get_stat("num_targets")]:
                e.apply_buff(PetrifyBuff(), duration)

        def get_description(self):
            return ("Whenever this spell or a minion it summons kills an enemy unit, [{num_targets}:num_targets] random enemies in line of sight are [petrified] for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is EntropyShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.duration = 10

        def on_damage(self, evt):
            if not evt.source:
                return
            if not isinstance(evt.source, self.spell_class):
                return
            if not evt.source.owner is self.owner:
                return
            if not are_hostile(evt.unit, self.owner):
                return

            evt.unit.apply_buff(EntropyBuff(), self.get_stat("duration"))

        def get_description(self):
            return ("Damaged enemies gain a non-stacking -25 [dark] and [arcane] resist for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is EnervationShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.duration = 10

        def on_damage(self, evt):
            if not evt.source:
                return
            if not isinstance(evt.source, self.spell_class):
                return
            if not evt.source.owner is self.owner:
                return
            if not are_hostile(evt.unit, self.owner):
                return

            evt.unit.apply_buff(EnervationBuff(), self.get_stat("duration"))

        def get_description(self):
            return ("Damaged enemies gain a non stacking -25 [fire], [lightning], and [ice] resist for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is WyrmEggShrineBuff:

        def get_wyrm(self, unit):
            unit.max_hp = self.get_stat("minion_health", base=unit.max_hp)
            for s in unit.spells:
                if hasattr(s, 'damage'):
                    if isinstance(s, BreathWeapon):
                        s.damage = self.get_stat("breath_damage", base=s.damage)
                    else:
                        s.damage = self.get_stat('minion_damage', base=s.damage)
                if hasattr(s, 'range') and s.range >= 2:
                    s.range = self.get_stat('minion_range', base=s.range)
            return unit

        def do_summon(self, evt):
            if evt.spell.cur_charges != 0:
                return
            flip = random.choice([True, False])
            if flip:
                egg = FireWyrmEgg()
            else:
                egg = IceWyrmEgg()
            apply_minion_bonuses(self, egg)
            egg.buffs[0].spawner = lambda: get_wyrm(self, FireWyrm() if flip else IceWyrm())
            self.summon(egg, target=evt)
            yield

    if cls is ToxicAgonyBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damaged
            self.radius = 5
            self.num_targets = 4

        def on_damaged(self, evt):
            if not are_hostile(evt.unit, self.owner):
                return
            if not evt.source:
                return

            if not evt.unit.has_buff(Poison):
                return

            sources = [evt.source]
            
            # For passive buffs or spells, potentially append the spell that summoned the minion with the passive or spell
            if evt.source.owner and evt.source.owner.source:
                sources.append(evt.source.owner.source)

            if not any(isinstance(source, self.spell_class) and source.owner == self.owner for source in sources):
                return

            targets = self.owner.level.get_units_in_ball(evt.unit, self.get_stat("radius"))
            targets = [t for t in targets if are_hostile(t, self.owner) and t != evt.unit and self.owner.level.can_see(t.x, t.y, evt.unit.x, evt.unit.y)]
            random.shuffle(targets)

            for t in targets[:self.get_stat("num_targets")]:
                self.owner.level.queue_spell(self.bolt(evt.damage, evt.unit, t))

        def get_description(self):
            return ("Whenever this spell or a minion it summoned deals damage to a [poisoned] enemy, deal that much [lightning] damage to up to [{num_targets}:num_targets] enemy units in a [{radius}_tile:radius] burst.").format(**self.fmt_dict())

    if cls is BoneSplinterBuff:

        def on_init(self):
            OnKillShrineBuff.on_init(self)
            self.radius = 3

        def burst(self, unit):
            damage = unit.max_hp // 2
            for stage in Burst(unit.level, unit, self.get_stat("radius")):
                for point in stage:
                    self.owner.level.deal_damage(point.x, point.y, damage, Tags.Physical, self)
                yield

        def get_description(self):
            return ("When this spell kills a [living] or [undead] unit, deal [physical] damage equal to half that unit's max HP in a [{radius}_tile:radius] burst.").format(**self.fmt_dict())

    if cls is HauntingShrineBuff:

        def trigger(self, target):
            unit = Ghost()
            apply_minion_bonuses(self, unit)
            self.summon(unit, target, sort_dist=False)
            yield

    if cls is ButterflyWingBuff:

        def trigger(self, target):
            unit = ButterflyDemon()
            apply_minion_bonuses(self, unit)
            self.summon(unit, target)
            yield

    if cls is GoldSkullBuff:

        def do_summon(self, evt):
            if evt.spell.cur_charges == 0:
                unit = GoldSkull()
                apply_minion_bonuses(self, unit)
                self.summon(unit, target=evt)
                yield

    if cls is FurnaceShrineBuff:

        def trigger(self, target):
            unit = FurnaceHound()
            apply_minion_bonuses(self, unit)
            self.summon(unit, target, sort_dist=False)
            yield

    if cls is HeavenstrikeBuff:

        def on_init(self):
            OnKillShrineBuff.on_init(self)
            self.damage = 18

        def do_damage(self, unit):
            units = [u for u in self.owner.level.get_units_in_los(unit) if are_hostile(self.owner, u)]
            random.shuffle(units)
            units.sort(key=lambda u: distance(unit, u))
            damage = self.get_stat("damage")
            if units:
                target = units[0]
                for p in self.owner.level.get_points_in_line(unit, target, find_clear=True):
                    self.owner.level.show_effect(p.x, p.y, Tags.Holy, minor=True)
                    yield
                target.deal_damage(damage, Tags.Holy, self)

        def get_description(self):
            return ("Whenever this spell kills an enemy unit, deal [{damage}_holy:holy] damage to the closest enemy in line of sight.").format(**self.fmt_dict())

    if cls is StormchargeBuff:

        def on_init(self):
            self.counter_max = 15
            self.damage = 9

        def trigger(self, target):
            enemies = [u for u in self.owner.level.units if are_hostile(u, self.owner)]
            damage = self.get_stat("damage")
            if enemies:
                e = random.choice(enemies)
                dtype = random.choice([Tags.Lightning, Tags.Ice])
                e.deal_damage(damage, dtype, self)
                yield

        def get_description(self):
            return ("For each 15 damage dealt by this spell or a minion it summons, deal [{damage}_ice:ice] or [{damage}_lightning:lightning] damage to a random enemy unit.").format(**self.fmt_dict())

    if cls is WarpedBuff:

        def on_init(self):
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.radius = 4
            self.damage = 11

        def do_damage(self):
            enemies = [u for u in self.owner.level.get_units_in_ball(self.owner, self.get_stat("radius")) if are_hostile(u, self.owner)]
            random.shuffle(enemies)
            damage = self.get_stat("damage")
            for e in enemies:
                e.deal_damage(damage, Tags.Arcane, self)

        def get_description(self):
            return ("Whenever you cast this spell and then also after it is resolved, deal [{damage}_arcane:arcane] damage to all enemies within [{radius}_tiles:radius] of the caster.").format(**self.fmt_dict())

    if cls is TroublerShrineBuff:

        def on_init(self):
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.minion_duration = 7

        def make_troubler(self, point):
            for _ in range(self.spell_level):
                troubler = Troubler()
                apply_minion_bonuses(self, troubler)
                self.summon(troubler, target=point)
                yield

        def get_description(self):
            return ("Whenever you cast this spell, summon several troublers near the location it was cast from for [{minion_duration}_turns:minion_duration].\nThe number of troublers summoned is equal to the spell's level.").format(**self.fmt_dict())

    if cls is FaewitchShrineBuff:

        def do_summon(self, target):
            unit = WitchFae()
            apply_minion_bonuses(self, unit)
            self.summon(unit, target, sort_dist=False)
            yield

        def get_description(self):
            return ("Whenever this spell kills a unit, if that unit had at least one debuff, summon a faewitch for [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is VoidBomberBuff:

        def on_init(self):
            self.radius = 1
            self.clusters = 0
            self.damage = 12
            self.name = "Suicide Explosion"
            self.color = Tags.Arcane.color

        def explode(self, level, x, y):
            for p in level.get_points_in_rect(x - self.radius, y - self.radius, x + self.radius, y + self.radius):
                level.deal_damage(p.x, p.y, self.damage, Tags.Arcane, self)

                # Demolish the tile
                cur_tile = level.tiles[p.x][p.y]
                if not cur_tile.is_chasm:
                    level.make_floor(p.x, p.y)

            for i in range(self.clusters):
                p = self.owner.level.get_summon_point(self.owner.x, self.owner.y, sort_dist=False, radius_limit=2)
                if p:
                    for q in self.owner.level.get_points_in_line(self.owner, p)[1:-1]:
                        self.owner.level.deal_damage(q.x, q.y, 0, Tags.Arcane, self)
                    bomb = VoidBomber()
                    bomb.team = self.owner.team
                    self.owner.level.add_obj(bomb, p.x, p.y)

            yield

    if cls is VoidBomberSuicide:

        def get_stat(self, attr, base=None):
            buff = None
            if self.caster:
                buff = self.caster.get_buff(FireBomberBuff)
            if buff and attr == "range":
                return self.get_stat("radius", base=buff.radius)
            return Spell.get_stat(self, attr, base)

        def cast(self, x, y):
            buff = self.caster.get_buff(VoidBomberBuff)
            if not buff:
                return
            buff.damage = self.get_stat("damage")
            buff.radius = self.get_stat("radius", base=buff.radius)
            self.caster.kill()
            yield

    if cls is FireBomberSuicide:

        def get_stat(self, attr, base=None):
            buff = None
            if self.caster:
                buff = self.caster.get_buff(FireBomberBuff)
            if buff and attr == "range":
                return self.get_stat("radius", base=buff.radius)
            return Spell.get_stat(self, attr, base)

        def cast(self, x, y):
            buff = self.caster.get_buff(FireBomberBuff)
            if not buff:
                return
            buff.damage = self.get_stat("damage")
            buff.radius = self.get_stat("radius", base=buff.radius)
            self.caster.kill()
            yield

    if cls is BomberShrineBuff:

        def do_summon(self, target):
            unit = random.choice([FireBomber, VoidBomber])()
            apply_minion_bonuses(self, unit)
            self.summon(unit, target)
            yield

    if cls is SorceryShieldShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.duration = 3

        def on_damage(self, evt):
            
            if type(evt.source) != self.spell_class:
                return
            if evt.source.owner != self.owner:
                return

            shield_buff = SorceryShieldStack(evt.damage_type)
            self.owner.apply_buff(shield_buff, self.get_stat("duration"))
        
        def get_description(self):
            return ("Whenever this spell deals damage, you gain 100 resistance to that type of damage for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is FrostfaeShrineBuff:

        def trigger(self, target):
            unit = FairyIce()
            apply_minion_bonuses(self, unit)
            self.summon(unit, target)
            yield

    if cls is ChaosConductanceShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDamaged] = self.on_damaged
            self.radius = 4

        def do_damage(self, target, damage, dtype):
            for unit in self.owner.level.get_units_in_ball(target, radius=self.get_stat("radius")):
                if target != unit and are_hostile(self.owner, unit):
                    unit.deal_damage(damage, dtype, self)
                yield

        def get_description(self):
            return ("Whenever this spell or a minion it summoned deals damage to an allied unit, redeal that damage to all enemy units in a [{radius}_tile:radius] radius.").format(**self.fmt_dict())

    if cls is IceSprigganShrineBuff:

        def get_bush(self, unit):
            apply_minion_bonuses(self, unit)
            return unit

        def do_summon(self, evt):
            unit = IcySpriggan()
            unit.buffs[0].spawner = lambda: get_bush(self, IcySprigganBush())
            apply_minion_bonuses(self, unit)
            self.summon(unit, target=evt)
            yield

    if cls is ChaosQuillShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnDeath] = self.on_death
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.minion_duration = 36

        def do_summon(self, evt):
            if evt.spell.cur_charges == 0:
                unit = ChaosQuill()
                unit.spells[0].num_summons = self.get_stat("num_summons")
                apply_minion_bonuses(self, unit)
                self.summon(unit, target=evt)
                yield

        def get_description(self):
            return ("Whenever this spell kills a [lightning] or [fire] unit, summon a living scroll of fire or lightning at that unit's location.\n"
					"Whenever you cast the last charge of this spell, summon a Chaos Quill for [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is FireflyShrineBuff:

        def on_init(self):
            OnKillShrineBuff.on_init(self)
            self.minion_duration = 20

        def on_kill(self, unit):
            for i in range(2):
                flyswarm = FireFlies()
                apply_minion_bonuses(self, flyswarm)
                self.summon(flyswarm, self.owner, sort_dist=False)

        def get_description(self):
            return ("Whenever this spell kills a unit, summon 2 firefly swarms near the caster for [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is DeathchillChimeraShrineBuff:

        def get_unit(self, unit):
            apply_minion_bonuses(self, unit)
            return unit

        def trigger(self, target):
            u = DeathchillChimera()
            u.buffs[0].spawner = lambda: get_unit(self, IceLion())
            u.buffs[1].spawner = lambda: get_unit(self, DeathSnake())
            apply_minion_bonuses(self, u)
            self.summon(u, target)
            yield

    if cls is BloodrageShrineBuff:

        def on_init(self):
            OnKillShrineBuff.on_init(self)
            self.duration = 5

        def on_kill(self, unit):
            duration = self.get_stat("duration")
            for u in self.owner.level.get_units_in_los(unit):
                if are_hostile(u, self.owner) or u == self.owner:
                    continue
                u.apply_buff(BloodrageBuff(3), duration)

        def get_description(self):
            return ("Whenever this spell kills a unit, all allied minions in line of sight gain +3 damage for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is RazorShrineBuff:

        def on_init(self):
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.damage = 27

        def do_razors(self, evt):
            damage = self.get_stat("damage")
            targets = [u for u in self.owner.level.get_units_in_los(evt) if are_hostile(self.owner, u)]
            random.shuffle(targets)

            for t in targets[:evt.spell.level]:
                for p in self.owner.level.get_points_in_line(evt, t)[1:-1]:
                    self.owner.level.show_effect(p.x, p.y, Tags.Physical, minor=True)

                t.deal_damage(damage, Tags.Physical, self)
                yield

    if cls is ShatterShards:

        def get_description(self):
            return "Whenever a unit is unfrozen or a [frozen] unit is killed, up to [{num_targets}_enemies:num_targets] in a [{radius}_tile:radius] burst take [{damage}_ice:ice] and [{damage}_physical:physical] damage.".format(**self.fmt_dict())	

    if cls is ShockAndAwe:

        def get_description(self):
            return ("Whenever an enemy dies to [lightning] damage, another random enemy in line of sight of that enemy goes [berserk] for [{duration}_turns:duration].\n"
                    + text.berserk_desc).format(**self.fmt_dict())

        def on_death(self, evt):
            if evt.damage_event is not None and evt.damage_event.damage_type == Tags.Lightning and self.owner.level.are_hostile(evt.unit, self.owner):
                def eligible(u):
                    if u is evt.unit:
                        return False
                    if not self.owner.level.are_hostile(u, self.owner):
                        return False
                    if not self.owner.level.can_see(evt.unit.x, evt.unit.y, u.x, u.y):
                        return False
                    return True

                candidates = [u for u in self.owner.level.units if eligible(u)]
                if candidates:
                    candidate = random.choice(candidates)
                    candidate.apply_buff(BerserkBuff(), self.get_stat('duration'))

    if cls is SteamAnima:

        def get_description(self):
            return ("Whenever a unit is unfrozen by fire damage, spawn [{num_summons}:num_summons] steam elementals nearby.\n"
                    "Steam elementals have [{minion_health}_HP:minion_health], [100_physical:physical] resist, [100_ice:ice] resist, and [100_fire:fire] resist.\n"
                    "Steam elementals have a ranged attack which deals [{minion_damage}_fire:fire] damage, with a range of [{minion_range}_tiles:minion_range].\n"
                    "The elementals vanish after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is Teleport:

        def cast(self, x, y):
            start_loc = Point(self.caster.x, self.caster.y)

            self.caster.level.show_effect(self.caster.x, self.caster.y, Tags.Translocation)
            p = self.caster.level.get_summon_point(x, y)
            if p:
                yield self.caster.level.act_move(self.caster, p.x, p.y, teleport=True)
                self.caster.level.show_effect(self.caster.x, self.caster.y, Tags.Translocation)

            if self.get_stat('void_teleport'):
                for unit in self.owner.level.get_units_in_los(self.caster):
                    if are_hostile(self.owner, unit):
                        unit.deal_damage(self.get_stat('max_charges'), Tags.Arcane, self)

            if self.get_stat('lightning_blink') or self.get_stat('dark_blink'):
                dtype = Tags.Lightning if self.get_stat('lightning_blink') else Tags.Dark
                damage = math.ceil(2*distance(start_loc, Point(x, y)))
                for stage in Burst(self.caster.level, Point(x, y), self.get_stat("radius", base=3)):
                    for point in stage:
                        if point == Point(x, y):
                            continue
                        self.caster.level.deal_damage(point.x, point.y, damage, dtype, self)
                    yield

    if cls is DeathBolt:

        def try_raise(self, caster, unit):
            if unit and unit.cur_hp <= 0 and not self.caster.level.get_unit_at(unit.x, unit.y):
                skeleton = curr_module.raise_skeleton(caster, unit, source=self, summon=False)
                if not skeleton:
                    return
                skeleton.spells[0].damage = self.get_stat('minion_damage')
                self.summon(skeleton, target=unit, radius=0)
                yield

    if cls is SummonIceDrakeSpell:

        def get_description(self):
            return ("Summon an Ice Drake at target square.\n"		
                    "Ice Drakes have [{minion_health}_HP:minion_health], fly, and have [100_ice:ice] resist.\n"
                    "Ice Drakes have a breath weapon which deals [{breath_damage}_ice:ice] damage and [freezes] units.\n"
                    "Ice Drakes have a melee attack which deals [{minion_damage}_physical:physical] damage.").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            drake = IceDrake()

            drake.max_hp = self.get_stat('minion_health')
            drake.spells[0].damage = self.get_stat('breath_damage')
            drake.spells[0].range = self.get_stat('minion_range')
            drake.spells[0].duration = self.get_stat('duration')
            drake.spells[1].damage = self.get_stat('minion_damage')

            if self.get_stat('dragon_mage'):
                dchill = DeathChill()
                dchill.statholder = self.caster
                dchill.max_charges = 0
                dchill.cur_charges = 0
                dchill.cool_down = 8
                drake.spells.insert(1, dchill)

            self.summon(drake, Point(x, y))

    if cls is ChannelBuff:

        def on_applied(self, owner):
            self.should_repeat = False
            self.channel_turns = 0
            self.max_channel = self.turns_left

            buffs = [b for b in owner.buffs if isinstance(b, ChannelBuff)]
            for b in buffs:
                if b.spell != self.spell:
                    owner.remove_buff(b)

            if not self.cast_after_channel:
                self.owner.level.queue_spell(self.spell(self.spell_target.x, self.spell_target.y, channel_cast=True), prepend=True)

        def on_pre_advance(self):
            self.should_repeat = True

        def on_advance(self):

            self.channel_turns += 1

            if not self.passed:
                self.owner.remove_buff(self)
                return

            if self.channel_check:
                if not self.channel_check(self.spell_target):
                    self.owner.remove_buff(self)
                    return

            cast = False
            if not self.cast_after_channel and self.should_repeat:
                cast = True
                self.owner.level.queue_spell(self.spell(self.spell_target.x, self.spell_target.y, channel_cast=True), prepend=True)

            if self.cast_after_channel and self.channel_turns == self.max_channel:
                cast = True
                self.owner.level.queue_spell(self.spell(self.spell_target.x, self.spell_target.y, channel_cast=True), prepend=True)

            if cast and self.owner.is_player_controlled:
                self.owner.level.show_effect(0, 0, Tags.Sound_Effect, 'sorcery_ally')

            self.passed = False

    if cls is DeathCleaveBuff:

        def on_advance(self):
            for buff in self.owner.buffs:
                if not isinstance(buff, ChannelBuff):
                    continue
                target = self.owner.level.get_unit_at(buff.spell_target.x, buff.spell_target.y)
                if not target:
                    continue
                self.cur_target = target
                spell = buff.spell.__self__
                self.owner.level.queue_spell(self.effect(EventOnSpellCast(spell, spell.caster, target.x, target.y)))

    if cls is CauterizingShrineBuff:

        def burn_hp(self, evt):
            drain_max_hp(evt.unit, evt.damage)
            self.owner.level.show_effect(evt.unit.x, evt.unit.y, Tags.Dark, minor=True)
            yield

    if cls is Tile:

        def __init__(self, char='*', color=Color(255, 0, 125), can_walk=True, x=0, y=0, level=None):
            self.sprite_override = None
            self.can_walk = can_walk
            self.can_see = True
            self.can_fly = True
            self.unit = None
            self.prop = None
            self.cloud = None
            self.x = x
            self.y = y
            self.is_chasm = False
            self.level = level
            self.sprites = None
            self.star = None

    if cls is SummonSiegeGolemsSpell:

        def get_impacted_tiles(self, x, y):
            return [Point(x, y)]

        def get_description(self):
            return ("Summons a crew of [{num_summons}:num_summons] siege golems.\n"
                    "The siege golems will assemble an inferno cannon, or operate one if it is adjacent.\n"
                    "The inferno cannon deals [{minion_damage}_fire:fire] damage to units in a [{radius}_tile:radius] radius.\n"
                    "The cannon will explode when destroyed, dealing [{minion_damage}_fire:fire] damage to units in a [{radius}_tile:radius] radius.\n".format(**self.fmt_dict()))

        def cannon(self):
            unit = Unit()
            unit.tags = [Tags.Construct, Tags.Metallic, Tags.Fire]
            unit.max_hp = 24
            unit.name = "Inferno Cannon"
            unit.stationary = True

            unit.resists[Tags.Physical] = 50
            unit.resists[Tags.Fire] = -100

            cannonball = SimpleRangedAttack(damage=self.get_stat('minion_damage'), range=self.get_stat('minion_range'), radius=self.get_stat('radius'), damage_type=Tags.Fire)
            cannonball.name = "Fire Blast"
            unit.spells = [cannonball]

            unit.buffs.append(DeathExplosion(damage=self.get_stat('minion_damage'), damage_type=Tags.Fire, radius=self.get_stat('radius')))

            unit.max_hp = 18
            unit.source = self
            return unit

        def golem(self):
            golem = SiegeOperator(self.cannon)
            golem.spells[2].range = 3
            golem.spells[1].heal = 2
            golem.spells[1].description = "Repair %d damage to a %s" % (golem.spells[1].heal, golem.spells[1].siege_name)
            golem.name = "Golem Siege Mechanic"
            golem.asset_name = "golem_siege"
            golem.max_hp = 25
            golem.tags = [Tags.Metallic, Tags.Construct]
            apply_minion_bonuses(self, golem)

            return golem

    if cls is Approach:

        def can_cast(self, x, y):
            if not Spell.can_cast(self, x, y):
                return False
            return bool(self.caster.level.find_path(self.caster, Point(x, y), self.caster, pythonize=True))

        def cast_instant(self, x, y):
            path = self.caster.level.find_path(self.caster, Point(x, y), self.caster, pythonize=True)
            if not path:
                return

            p = path[0]
            if self.caster.level.can_move(self.caster, p.x, p.y):
                self.caster.level.act_move(self.caster, p.x, p.y)

    if cls is Crystallographer:

        def buff(self):
            amt = 0
            for u in self.owner.level.units:
                if u.has_buff(FrozenBuff) or u.has_buff(GlassPetrifyBuff):
                    amt += 2
            if amt:
                self.owner.apply_buff(CrystallographerActiveBuff(amt), 1)
            yield

        def on_pre_advance(self):
            self.owner.level.queue_spell(buff(self))

    if cls is CrystallographerActiveBuff:

        def __init__(self, amt):
            self.amt = amt
            Buff.__init__(self)
            self.buff_type = BUFF_TYPE_PASSIVE

    if cls is Necrostatics:

        def buff(self):
            num_undead_allies = len([u for u in self.owner.level.units if not are_hostile(u, self.owner) and Tags.Undead in u.tags])
            if num_undead_allies:
                self.owner.apply_buff(NecrostaticStack(num_undead_allies), 1)
            yield

        def on_pre_advance(self):
            self.owner.level.queue_spell(buff(self))

    if cls is NecrostaticStack:

        def __init__(self, strength):
            self.strength = strength
            Buff.__init__(self)
            self.buff_type = BUFF_TYPE_PASSIVE

    if cls is HeavenlyIdol:

        def on_init(self):

            self.name = "Heavenly Idol"
            
            self.level = 5
            self.tags = [Tags.Holy, Tags.Lightning, Tags.Conjuration]
            self.max_charges = 4

            self.minion_health = 35
            self.shields = 2
            self.heal = 1
            self.minion_duration = 15

            self.upgrades['shields'] = (5, 3)
            self.upgrades['fire_gaze'] = (1, 4, "Fire Gaze", "The Idol gains a beam attack with [{minion_range}_range:minion_range] that deals [{minion_damage}_fire:fire] damage.")
            self.upgrades['heal'] = (1, 3)
            self.upgrades['minion_duration'] = (15, 1)

            self.must_target_walkable = True
            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_damage"] = self.get_stat("minion_damage", base=8)
            stats["minion_range"] = self.get_stat("minion_range", base=10)
            return stats

        def cast_instant(self, x, y):

            idol = Unit()
            idol.name = "Idol of Beauty"
            idol.asset_name = "heavenly_idol"

            idol.max_hp = self.get_stat('minion_health')
            idol.shields = self.get_stat('shields')
            idol.stationary = True

            idol.resists[Tags.Physical] = 75
            
            idol.tags = [Tags.Construct, Tags.Holy]

            idol.buffs.append(BeautyIdolBuff(self))
            idol.turns_to_death = self.get_stat('minion_duration')

            if self.get_stat("fire_gaze"):
                gaze = SimpleRangedAttack(damage=self.get_stat("minion_damage", base=8), range=self.get_stat("minion_range", base=10), beam=True, damage_type=Tags.Fire)
                gaze.name = "Fiery Gaze"
                idol.spells.append(gaze)

            self.summon(idol, Point(x, y))

        def get_description(self):
            return ("Summon an Idol of Beauty.\n"
                    "The idol has [{minion_health}_HP:minion_health], [{shields}_SH:shields], and is stationary.\n"
                    "The idol has a passive aura which affects all units in line of sight of the idol each turn.\n"
                    "Affected allies are healed for [{heal}_HP:heal]. The Wizard cannot be healed in this way.\n"
                    "Affected enemies take [1_holy:holy] damage.\n"
                    "Affected [undead] and [demon] enemies take an additional [1_lightning:lightning] damage.\n"
                    "This damage is fixed, and cannot be increased using shrines, skills, or buffs.\n"
                    "The idol vanishes after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is RingOfSpiders:

        def get_impacted_tiles(self, x, y):
            points = self.caster.level.get_points_in_rect(x-2, y-2, x+2, y+2)
            return [p for p in points if not self.caster.level.tiles[p.x][p.y].is_wall()]

        def cast(self, x, y):

            for p in self.get_impacted_tiles(x, y):
                unit = self.caster.level.get_unit_at(p.x, p.y)

                rank = max(abs(p.x - x), abs(p.y - y))

                if rank == 0:
                    if self.get_stat('damage'):
                        self.caster.level.deal_damage(x, y, self.get_stat('damage'), Tags.Poison, self)
                elif rank == 1:
                    if not unit and self.caster.level.tiles[p.x][p.y].can_walk:
                        if self.get_stat('aether_spiders'):
                            spider = PhaseSpider()
                        else:
                            spider = GiantSpider()
                        spider.team = self.caster.team
                        
                        spider.spells[0].damage = self.get_stat('minion_damage')
                        spider.max_hp = self.get_stat('minion_health')

                        self.summon(spider, p)
                    if unit:
                        unit.apply_buff(Poison(), self.get_stat('duration'))
                else:
                    if not unit and not self.caster.level.tiles[p.x][p.y].is_wall():
                        cloud = SpiderWeb()
                        cloud.owner = self.caster
                        self.caster.level.add_obj(cloud, *p)
                    if unit:
                        unit.apply_buff(Stun(), 1)
                yield

    if cls is UnholyAlliance:

        def on_unit_add(self, evt):

            if are_hostile(evt.unit, self.owner):
                return

            if Tags.Holy in evt.unit.tags:
                if any((Tags.Undead in u.tags or Tags.Demon in u.tags) and not are_hostile(u, evt.unit) for u in self.owner.level.units):
                    buff = GlobalAttrBonus("damage", 7)
                    buff.buff_type = BUFF_TYPE_PASSIVE
                    evt.unit.apply_buff(buff)
                    return

            if Tags.Undead in evt.unit.tags or Tags.Demon in evt.unit.tags:
                if any(Tags.Holy in u.tags and not are_hostile(u, evt.unit) for u in self.owner.level.units):
                    buff = GlobalAttrBonus("damage", 7)
                    buff.buff_type = BUFF_TYPE_PASSIVE
                    evt.unit.apply_buff(buff)
                    return

    if cls is TurtleDefenseBonus:

        def on_init(self):
            Stun.on_init(self)
            self.buff_type = BUFF_TYPE_BLESS
            self.resists[Tags.Physical] = 50
            self.resists[Tags.Fire] = 50
            self.resists[Tags.Lightning] = 50
            self.color = Tags.Nature.color
            self.name = "Inside Shell"

    if cls is TurtleBuff:

        def on_init(self):
            self.color = Tags.Nature.color

    if cls is NaturalVigor:

        def on_unit_added(self, evt):
            if evt.unit.is_player_controlled:
                return
                
            if not self.owner.level.are_hostile(self.owner, evt.unit):
                evt.unit.apply_buff(NaturalVigorBuff())

    if cls is OakenShrineBuff:

        def on_summon(self, unit):
            unit.apply_buff(OakenBuff())

    if cls is TundraShrineBuff:

        def on_summon(self, unit):
            unit.apply_buff(TundraBuff())
            icebolt = SimpleRangedAttack(damage=unit.source.get_stat('minion_damage'), range=self.spell_level + 1, damage_type=Tags.Ice)
            icebolt.name = "Tundra Bolt"
            icebolt.cool_down = 4
            unit.add_spell(icebolt, prepend=True)

    if cls is SwampShrineBuff:

        def on_summon(self, unit):
            unit.apply_buff(SwampBuff())
            aura = DamageAuraBuff(damage=2, damage_type=Tags.Poison, radius=1+self.spell_level)
            aura.buff_type = BUFF_TYPE_PASSIVE
            aura.name = "Swamp Aura"
            unit.apply_buff(aura)

    if cls is SandStoneShrineBuff:

        def on_summon(self, unit):
            unit.apply_buff(SandstoneBuff())

    if cls is BlueSkyShrineBuff:

        def on_summon(self, unit):
            unit.apply_buff(BlueSkyBuff())
            unit.flying = True
            regen = RegenBuff(2)
            regen.buff_type = BUFF_TYPE_PASSIVE
            unit.apply_buff(regen)

    if cls is MatureInto:

        def __init__(self, spawner, duration, apply_bonuses=True):
            Buff.__init__(self)
            self.spawner = spawner
            self.spawn_name = None
            self.mature_duration = duration
            self.max_duration = duration
            self.apply_bonuses = apply_bonuses

        def on_advance(self):
            self.mature_duration -= 1
            if self.mature_duration <= 0:
                # In case the past self of this unit is somehow brought back after it has matured into a different unit.
                self.mature_duration = self.max_duration
                self.owner.kill(trigger_death_event=False)
                new_unit = self.spawner()
                new_unit.team = self.owner.team
                new_unit.source = self.owner.source
                if self.apply_bonuses:
                    apply_minion_bonuses(self.owner.source, new_unit)
                p = self.owner.level.get_summon_point(self.owner.x, self.owner.y, radius_limit=8, flying=new_unit.flying)
                if p:
                    self.owner.level.add_obj(new_unit, p.x, p.y)

    if cls is SummonWolfSpell:

        def on_init(self):
            self.max_charges = 12
            self.name = "Wolf"
            self.minion_health = 11
            self.minion_damage = 5
            self.upgrades['leap_range'] = (1, 3, "Pounce", "Summoned wolves gain a leap attack with [{minion_range}_range:minion_range].")
            self.upgrades['minion_damage'] = 4
            self.upgrades['minion_health'] = (12, 3)

            self.upgrades['blood_hound'] = (1, 3, "Blood Hound", "Summon blood hounds instead of wolves.", "hound")
            self.upgrades['ice_hound'] = (1, 3, "Ice Hound", "Summon ice hounds instead of wolves.", "hound")
            self.upgrades['clay_hound'] = (1, 6, "Clay Hound", "Summon clay hounds instead of wolves.", "hound")
            self.upgrades['wolf_pack'] = (1, 8, "Wolf Pack", "Each cast of wolf consumes 2 charges and summons 4 wolves.")


            self.tags = [Tags.Nature, Tags.Conjuration]
            self.level = 1

            self.must_target_walkable = True
            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_range"] = self.get_stat('minion_range', base=4)
            return stats

        def make_wolf(self):
            wolf = Unit()
            wolf.max_hp = self.get_stat('minion_health')
            
            wolf.sprite.char = 'w'
            wolf.sprite.color = Color(102, 77, 51)
            wolf.name = "Wolf"
            wolf.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))
            wolf.tags = [Tags.Living, Tags.Nature]

            if self.get_stat('leap_range'):
                wolf.spells.append(LeapAttack(damage=self.get_stat('minion_damage'), damage_type=Tags.Physical, range=self.get_stat('minion_range', base=4)))

            if self.get_stat('blood_hound'):
                wolf.name = "Blood Hound"
                wolf.asset_name = "blood_wolf"
                melee = wolf.spells[0]
                melee.onhit = lambda caster, target: caster.apply_buff(BloodrageBuff(2), caster.get_stat(self.get_stat("duration", base=10), melee, "duration"))
                melee.name = "Frenzy Bite"
                melee.description = ""
                melee.get_description = lambda: "Gain +2 damage for %i turns with each attack" % wolf.get_stat(self.get_stat("duration", base=10), melee, "duration")
                
                wolf.tags = [Tags.Demon, Tags.Nature]
                wolf.resists[Tags.Dark] = 75

            elif self.get_stat('ice_hound'):
                for s in wolf.spells:
                    s.damage_type = Tags.Ice
                wolf.resists[Tags.Ice] = 100
                wolf.resists[Tags.Fire] = -50
                wolf.resists[Tags.Dark] = 50
                wolf.name = "Ice Hound"
                wolf.tags = [Tags.Demon, Tags.Ice]
                wolf.buffs.append(Thorns(4, Tags.Ice))

            elif self.get_stat('clay_hound'):
                wolf.name = "Clay Hound"
                wolf.asset_name = "earth_hound"

                wolf.resists[Tags.Physical] = 50
                wolf.resists[Tags.Fire] = 50
                wolf.resists[Tags.Lightning] = 50
                wolf.buffs.append(RegenBuff(3))
                

            wolf.team = self.caster.team

            return wolf

    if cls is AnnihilateSpell:

        def on_init(self):
            self.range = 6
            self.name = "Annihilate"
            self.max_charges = 8
            self.damage = 16
            self.tags = [Tags.Chaos, Tags.Sorcery]
            self.level = 2

            self.upgrades['cascade'] =  (1, 3, 'Cascade', 'Hits from Annihilate will jump to targets up to [4_tiles:cascade_range] away if the main target is killed or if targeting an empty tile.\nThis ignores line of sight and benefits from bonuses to [cascade_range:cascade_range].')
            self.upgrades['dark'] =  (1, 1, 'Dark Annihilation', 'Annihilate deals an additional dark damage hit')
            self.upgrades['arcane'] =  (1, 1, 'Arcane Annihilation', 'Annihilate deals an additional arcane damage hit')
            self.upgrades['max_charges'] = (4, 2)

        def cast(self, x, y):
            
            cur_target = Point(x, y)
            dtypes = [Tags.Fire, Tags.Lightning, Tags.Physical]
            if self.get_stat('arcane'):
                dtypes.append(Tags.Arcane)
            if self.get_stat('dark'):
                dtypes.append(Tags.Dark)
            
            damage = self.get_stat('damage')
            cascade = self.get_stat("cascade")
            cascade_range = self.get_stat("cascade_range", base=4)
            for dtype in dtypes:
                if cascade and not self.caster.level.get_unit_at(cur_target.x, cur_target.y):
                    other_targets = self.caster.level.get_units_in_ball(cur_target, cascade_range)
                    other_targets = [t for t in other_targets if self.caster.level.are_hostile(t, self.caster)]
                    if other_targets:
                        cur_target = random.choice(other_targets)

                self.caster.level.deal_damage(cur_target.x, cur_target.y, damage, dtype, self)
                for i in range(9):
                    yield

    if cls is MegaAnnihilateSpell:

        def on_init(self):
            self.damage = 99
            self.max_charges = 3
            self.name = "Mega Annihilate"
            
            self.tags = [Tags.Chaos, Tags.Sorcery]
            self.level = 5

            self.upgrades['cascade'] =  (1, 3, 'Cascade', 'Hits from Annihilate will jump to targets up to [4_tiles:cascade_range] away if the main target is killed or if targeting an empty tile.\nThis ignores line of sight and benefits from bonuses to [cascade_range:cascade_range].')
            self.upgrades['dark'] =  (1, 2, 'Dark Annihilation', 'Annihilate deals an additional dark damage hit')
            self.upgrades['arcane'] =  (1, 2, 'Arcane Annihilation', 'Annihilate deals an additional arcane damage hit')
            self.upgrades['damage'] = (99, 4)

    if cls is MeltBuff:

        def __init__(self, spell):
            self.spell = spell
            Buff.__init__(self)
            self.asset = ["Bugfixes", "Statuses", "amplified_physical"]

    if cls is CollectedAgony:

        def do_damage(self, target, damage):
            self.owner.level.show_path_effect(self.owner, target, Tags.Dark)
            yield
            target.deal_damage(damage, Tags.Dark, self)

    if cls is MeteorShower:

        def on_init(self):
            self.name = "Meteor Shower"

            self.damage = 23
            self.num_targets = 7
            self.storm_radius = 7
            self.stats.append('storm_radius')
            self.radius = 2
            self.range = RANGE_GLOBAL
            self.requires_los = False
            self.duration = 2

            self.max_charges = 1

            self.tags = [Tags.Fire, Tags.Sorcery]
            self.level = 7

            self.max_channel = 5

            self.upgrades['num_targets'] = (3, 4)
            self.upgrades['duration'] = (3, 2, "Stun Duration")
            self.upgrades['rock_size'] = (1, 2, "Meteor Size", "Increase the physical damage and stun radius from 0 to 1")
            self.upgrades['max_channel'] = (5, 2)

        def get_description(self):
            return ("Rains [{num_targets}_meteors:num_targets] down on random tiles in a [{storm_radius}_tile:radius] radius each turn.\n"
                    "Meteors deal [{damage}_physical:physical] damage, destroy walls, and inflict stun for [{duration}_turns:duration].\n"
                    "Meteors also deal [{damage}_fire:fire] damage in a [{radius}_tile:radius] radius.\n"
                    "This spell can be channeled for up to [{max_channel}_turns:duration].  The effect is repeated each turn the spell is channeled.").format(**self.fmt_dict())

        def cast(self, x, y, channel_cast=False):

            if not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)), self.get_stat('max_channel'))
                return

            points_in_ball = list(self.caster.level.get_points_in_ball(x, y, self.get_stat('storm_radius')))

            rock_size = self.get_stat('rock_size')
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')
            radius = self.get_stat('radius')

            for _ in range(self.get_stat('num_targets')):
                target = random.choice(points_in_ball)

                for stage in Burst(self.caster.level, target, rock_size, ignore_walls=True):
                    for point in stage:
                        self.caster.level.make_floor(point.x, point.y)
                        self.caster.level.deal_damage(point.x, point.y, damage, Tags.Physical, self)
                        unit = self.caster.level.get_unit_at(point.x, point.y)
                        if unit:
                            unit.apply_buff(Stun(), duration)
                    yield

                self.caster.level.show_effect(0, 0, Tags.Sound_Effect, 'hit_enemy')
                yield

                for stage in Burst(self.caster.level, target, radius):
                    for point in stage:
                        self.caster.level.deal_damage(point.x, point.y, damage, Tags.Fire, self)
                    yield
                yield

    if cls is WizardQuakeport:

        def cast(self, x, y):
            randomly_teleport(self.caster, radius=self.get_stat("range"))
            yield

            points = list(self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, 4))
            random.shuffle(points)

            for p in points:
                if random.random() < .65:
                    self.caster.level.deal_damage(p.x, p.y, self.get_stat('damage'), Tags.Physical, self)
                    if random.random() < .7:
                        self.caster.level.make_floor(p.x, p.y)
                if random.random() < .25:
                    yield

    if cls is PurityBuff:

        def on_applied(self, owner):
            self.originally_undebuffable = self.owner.debuff_immune
            self.owner.debuff_immune = True

        def on_unapplied(self):
            self.owner.debuff_immune = self.originally_undebuffable

    if cls is SummonGiantBear:

        def cast(self, x, y):

            bear = Unit()
            bear.max_hp = self.get_stat('minion_health')
            
            bear.name = "Giant Bear"
            bear.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))

            bear.tags = [Tags.Living, Tags.Nature]

            if self.get_stat('venom'):
                bear.name = "Venom Beast"
                bear.asset_name = "giant_bear_venom"
                bear.resists[Tags.Poison] = 100
                bear.tags = [Tags.Living, Tags.Poison, Tags.Nature]

                bite = SimpleMeleeAttack(damage=self.get_stat('minion_damage'), buff=Poison, buff_duration=self.get_stat("duration", base=5))
                bite.name = "Poison Bite"
                bear.spells = [bite]

                bear.buffs = [VenomBeastHealing()]

            elif self.get_stat('armored'):
                bear.max_hp += 14
                bear.name = "Armored Bear"
                bear.asset_name = "giant_bear_armored"
                bear.resists[Tags.Physical] = 50
                bear.resists[Tags.Lightning] = -50

            elif self.get_stat('blood'):
                bear = BloodBear()
                melee = bear.spells[0]
                melee.onhit = lambda caster, target: caster.apply_buff(BloodrageBuff(3), caster.get_stat(self.get_stat("duration", base=10), melee, "duration"))
                melee.name = "Frenzy Bite"
                melee.description = ""
                melee.get_description = lambda: "Gain +3 damage for %i turns with each attack.%s" % (bear.get_stat(self.get_stat("duration", base=10), melee, "duration"), (" Attacks %i times." % melee.attacks) if melee.attacks > 1 else "")
                apply_minion_bonuses(self, bear)
            
            bear.spells[0].attacks = self.get_stat('minion_attacks')
            
            self.summon(bear, Point(x, y))
            yield

    if cls is SimpleMeleeAttack:

        def cast_instant(self, x, y):

            duration = self.get_stat("duration", base=self.buff_duration) if self.buff_duration > 0 else 0

            for _ in range(self.attacks):
                unit = self.caster.level.get_unit_at(x, y)

                if self.attacks > 1 and not unit:
                    possible_targets = self.caster.level.get_units_in_ball(self.caster, 1.5)
                    possible_targets = [t for t in possible_targets if self.caster.level.are_hostile(self.caster, t)]
                    if possible_targets:
                        target = random.choice(possible_targets)
                        x = target.x
                        y = target.y

                dealt = self.caster.level.deal_damage(x, y, self.get_stat('damage'), random.choice(self.damage_type) if isinstance(self.damage_type, list) else self.damage_type, self)
                if self.drain:
                    self.caster.deal_damage(-dealt, Tags.Heal, self)

                if unit and unit.is_alive():
                    if self.buff:		
                        unit.apply_buff(self.buff(), duration)
                    if self.trample:
                        
                        trample_points = [p for p in self.caster.level.get_adjacent_points(Point(x, y ), check_unit=True, filter_walkable=True)] + [None]
                        p = random.choice(trample_points)
                        if p:
                            self.caster.level.act_move(unit, p.x, p.y)
                        
                        if self.caster.level.can_move(self.caster, x, y, force_swap=True):
                            self.caster.level.act_move(self.caster, x, y, force_swap=True)
                        
                if self.onhit and unit:
                    self.onhit(self.caster, unit)

        def get_description(self):
            if self.description:
                return self.description

            desc = ""
            if self.buff_name:
                if self.buff_duration > 0:
                    desc += "Applies %s for %d turns.  " % (self.buff_name, self.get_stat("duration", base=self.buff_duration))
                else:
                    desc += "Applies %s.  " % self.buff_name
            if self.attacks > 1:
                desc += "Attacks %d times.  " % self.attacks
            if self.trample:
                desc += "Trample attack"
            if self.drain:
                desc += "Heals attacker for damage dealt"

            return desc

    if cls is ThornQueenThornBuff:

        def on_advance(self):
            valid_summon_points = [t for t in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.radius) if self.is_target_valid(t)]
            if valid_summon_points:
                p = random.choice(valid_summon_points)
                thorn = FaeThorn()
                if hasattr(self.owner.source, "get_stat"):
                    apply_minion_bonuses(self.owner.source, thorn)
                    thorn.turns_to_death = self.owner.source.get_stat("minion_duration", base=6)
                thorn.team = self.owner.team
                thorn.source = self.owner.source
                self.owner.level.add_obj(thorn, p.x, p.y)

    if cls is FaeCourt:

        def get_faery(self, unit):
            unit.spells[1].damage = self.minion_damage
            unit.spells[0].heal = self.get_stat("heal")
            unit.shields = self.get_stat("shields")
            return unit

        def cast(self, x, y):

            if self.get_stat('summon_queen'):	
                unit = ThornQueen()
                unit.shields += self.get_stat("shields") - self.shields
                unit.spells[0] = SimpleSummon(lambda: get_faery(self, EvilFairy()), num_summons=4, cool_down=10, duration=15)
                unit.spells[0].name = "Fae Queen's Guard"
                apply_minion_bonuses(self, unit)
                self.summon(unit, sort_dist=False, radius=4)

            glass = self.get_stat("glass_fae")
            for _ in range(self.get_stat('num_summons')):
                if glass:
                    unit = get_faery(self, FairyGlass())
                else:
                    unit = get_faery(self, EvilFairy())
                apply_minion_bonuses(self, unit)
                self.summon(unit, sort_dist=False, radius=4)
                yield

        def get_description(self):
            return ("Summons a group of [{num_summons}:num_summons] faeries near the caster.\n"
                    "The faeries fly, and have [{minion_health}_HP:minion_health], [{shields}_SH:shields], [50_arcane:arcane] resistance, and a passive blink.\n"
                    "The faeries have a [{minion_damage}_arcane:arcane] damage attack, with a range of [{minion_range}_tiles:minion_range].\n"
                    "The faeries can heal allies for [{heal}_HP:heal], with 2 more range than their attack.\n"
                    "The faeries vanish after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is GhostfireUpgrade:

        def do_summon(self, x, y):
            unit = GhostFire()
            apply_minion_bonuses(self, unit)
            self.summon(unit, target=Point(x, y))
            yield

        def get_description(self):
            return ("Whenever an enemy takes [dark] damage and [fire] damage in the same turn, summon a fire ghost near that enemy.\n"
                    "Fire ghosts fly, have [100_fire:fire] resist and [50_dark:dark] resist, and passively blink.\n"
                    "Fire ghosts have a ranged attack which deals [{minion_damage}_fire:fire] damage with a [{minion_range}_tile:minion_range] range.\n"
                    "The ghosts vanish after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is SplittingBuff:

        def on_death(self, evt):
            for _ in range(self.children):
                unit = self.spawner()
                if unit.max_hp == 0:
                    return
                # Don't overwrite source on enemy units, else it breaks enemy HP multiplier trials.
                if self.owner.team == TEAM_PLAYER:
                    unit.source = self.owner.source
                self.summon(unit)

    if cls is GeneratorBuff:

        def __init__(self, spawn_func, spawn_chance, sort_dist=True, radius=3):
            Buff.__init__(self)
            self.spawn_func = spawn_func
            self.spawn_chance = spawn_chance
            self.example_monster = self.spawn_func()
            self.sort_dist = sort_dist
            self.radius = radius

        def on_advance(self):
            if random.random() < self.spawn_chance:
                new_monster = self.spawn_func()
                new_monster.team = self.owner.team
                new_monster.source = self.owner.source
                apply_minion_bonuses(self.owner.source, new_monster)
                self.summon(new_monster, sort_dist=self.sort_dist, radius=self.radius)

        def get_tooltip(self):
            return "Has a %d%% chance each turn to spawn a %s%s" % (int(100 * self.spawn_chance), self.example_monster.name, "" if self.sort_dist else (" up to %i tiles away" % self.radius))

    if cls is RespawnAs:

        def __init__(self, spawner, apply_bonuses=True):
            Buff.__init__(self)
            self.spawner = spawner
            self.spawn_name = None
            self.get_tooltip() # populate name
            self.name = "Respawn As %s" % self.spawn_name
            self.apply_bonuses = apply_bonuses

        def respawn(self):
            new_unit = self.spawner()
            new_unit.team = self.owner.team
            new_unit.source = self.owner.source
            new_unit.parent = self.owner
            if self.apply_bonuses:
                apply_minion_bonuses(self.owner.source, new_unit)
            p = self.owner.level.get_summon_point(self.owner.x, self.owner.y, radius_limit=8, flying=new_unit.flying)
            if p:
                self.owner.level.add_obj(new_unit, p.x, p.y)

    if cls is EventHandler:

        def raise_event(self, event, entity=None):
            event_type = type(event)
            if event_type == EventOnPreDamagedPenetration:
                event_type = EventOnPreDamaged
            elif event_type == EventOnDamagedPenetration:
                event_type = EventOnDamaged
            # Record state of list once to ignore changes to the list caused by subscriptions
            if entity:
                for handler in list(self._handlers[event_type][entity]):
                    handler(event)
            global_handlers = list(self._handlers[event_type][None])
            for handler in global_handlers:
                handler(event)

    if cls is SummonFloatingEye:

        def cast_instant(self, x, y):
            eye = FloatingEye()
            eye.spells = []
            eye.team = TEAM_PLAYER
            eye.max_hp += self.get_stat('minion_health')
            eye.turns_to_death = self.get_stat('minion_duration')

            p = self.caster.level.get_summon_point(x, y, flying=True)
            if p:
                # Ensure point exists before having the eye cast eye spells
                self.summon(eye, p)

                for spell in self.caster.spells:
                    if Tags.Eye in spell.tags and spell.range == 0:
                        # Temporarily change caster of spell
                        spell = type(spell)()
                        spell.caster = eye
                        spell.owner = eye
                        spell.statholder = self.caster
                        self.caster.level.act_cast(eye, spell, eye.x, eye.y, pay_costs=False)

        def get_description(self):
            return ("Summon a floating eye.\n"
                    "Floating eyes have [{minion_health}_HP:minion_health], [{shields}_SH:shields], float in place, and passively blink.\n"
                    "Floating eyes have no attacks of their own, but will cast any self-targeted [eye] spells you know upon being summoned.\n"
                    "Floating eyes vanish after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is SlimeBuff:

        def on_advance(self):
            if random.random() < .5:
                return

            if self.owner.cur_hp == self.owner.max_hp:
                self.owner.max_hp += self.growth
            self.owner.deal_damage(-self.growth, Tags.Heal, self)
            if self.owner.cur_hp >= self.to_split:

                p = self.owner.level.get_summon_point(self.owner.x, self.owner.y)
                if p:
                    self.owner.max_hp //= 2
                    self.owner.cur_hp //= 2
                    unit = self.spawner()
                    unit.team = self.owner.team
                    unit.source = self.owner.source
                    self.owner.level.add_obj(unit, p.x, p.y)

    if cls is Bolt:

        def __init__(self, level, start, end, two_pass=True, find_clear=True):
            self.start = start
            self.end = end
            self.level = level
            self.two_pass = True
            self.find_clear = False

    if cls is Spell:

        def get_stat(self, attr, base=None):
            statholder = self.statholder or self.caster
            
            if base is None:
                base = getattr(self, attr, 0)

            if not statholder:
                return base

            return statholder.get_stat(base, self, attr)

        def get_corner_target(self, radius, requires_los=True):
            # Find targets possibly around corners
            # Returns the first randomly found target which will hit atleast one enemy with a splash of the given radius

            dtypes = []
            if hasattr(self, 'damage_type'):
                if isinstance(self.damage_type, Tag):
                    dtypes = [self.damage_type]
                else:
                    dtypes = self.damage_type
            
            def is_target(v):
                if not are_hostile(self.caster, v):
                    return False
                # if no damage type is specified, take any hostile target
                if not dtypes:
                    return True
                for dtype in dtypes:
                    if v.resists[dtype] < 100:
                        return True

            nearby_enemies = self.caster.level.get_units_in_ball(self.caster, self.get_stat("range") + radius)
            nearby_enemies = [u for u in nearby_enemies if is_target(u)]

            possible_cast_points = list(self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, self.get_stat("range")))

            # Filter points that are not close to any enemies
            potentials = []
            for p in possible_cast_points:
                for e in nearby_enemies:
                    if distance(p, e, diag=False, euclidean=False) < radius:
                        potentials.append(p)
                        break

            possible_cast_points = potentials

            # Filter points that the spell cannot target
            potentials = []
            for p in possible_cast_points:
                if self.can_cast(p.x, p.y):
                    potentials.append(p)

            possible_cast_points = potentials
            random.shuffle(possible_cast_points)

            def can_hit(p, u):
                return distance(p, u, diag=False, euclidean=False) <= radius and (not self.get_stat("requires_los") or self.caster.level.can_see(p.x, p.y, u.x, u.y))

            for p in possible_cast_points:
                if not any(is_target(u) and can_hit(p, u) for u in self.owner.level.get_units_in_ball(p, radius)):
                    continue
                return p
            return None

    if cls is Icicle:

        def on_init(self):

            self.name = "Icicle"

            self.tags = [Tags.Ice, Tags.Sorcery]

            self.radius = 1
            self.damage = 6
            self.level = 1

            self.range = 9

            self.max_charges = 22

            self.upgrades['freezing'] = (1, 2, "Freezing", "[Freeze] the main target for [{duration}_turns:duration].")
            self.upgrades['radius'] = (1, 2)
            self.upgrades['damage'] = (9, 3)
            self.add_upgrade(IcicleHarvest())

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["duration"] = self.get_stat('duration', base=2)
            return stats

        def cast(self, x, y):

            for p in Bolt(self.caster.level, self.caster, Point(x, y)):
                self.caster.level.show_effect(p.x, p.y, Tags.Physical, minor=True)
                yield

            self.caster.level.deal_damage(x, y, self.get_stat('damage'), Tags.Physical, self)
            unit = self.caster.level.get_unit_at(x, y)
            if unit and self.get_stat('freezing'):
                unit.apply_buff(FrozenBuff(), self.get_stat('duration', base=2))

            yield

            for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')):
                for p in stage:
                    self.caster.level.deal_damage(p.x, p.y, self.get_stat('damage'), Tags.Ice, self)
                yield

    if cls is PoisonSting:

        def cast(self, x, y):

            for p in Bolt(self.caster.level, self.caster, Point(x, y), find_clear=False):
                self.caster.level.show_effect(p.x, p.y, Tags.Poison, minor=True)
                yield
            
            damage = self.caster.level.deal_damage(x, y, self.get_stat('damage'), Tags.Physical, self)

            unit = self.caster.level.get_unit_at(x, y)
            if unit and damage and self.get_stat('antigen'):
                unit.apply_buff(Acidified())
            if unit and unit.resists[Tags.Poison] < 100:
                unit.apply_buff(Poison(), self.get_stat('duration'))

    if cls is ArchonLightning:

        def cast_instant(self, x, y):
            damage = self.get_stat('damage')
            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:]:
                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit and not are_hostile(unit, self.caster):
                    unit.add_shields(1)
                else:
                    self.caster.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)

    if cls is PyrostaticPulse:

        def get_impacted_tiles(self, x, y):
            center_beam = self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:]
            side_beam = []
            for p in center_beam:
                for q in self.caster.level.get_points_in_ball(p.x, p.y, 1.5):
                    if q.x == self.caster.x and q.y == self.caster.y:
                        continue
                    if q not in center_beam and q not in side_beam:
                        side_beam.append(q)
            return center_beam + side_beam

        def cast_instant(self, x, y):

            center_beam = self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:]
            side_beam = []
            for p in center_beam:
                for q in self.caster.level.get_points_in_ball(p.x, p.y, 1.5):
                    if q.x == self.caster.x and q.y == self.caster.y:
                        continue
                    if q not in center_beam and q not in side_beam:
                        side_beam.append(q)

            damage = self.get_stat('damage')
            for p in center_beam:
                self.caster.level.deal_damage(p.x, p.y, damage, Tags.Fire, self)
            for p in side_beam:
                self.caster.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)

    if cls is BombToss:

        def cast(self, x, y):

            blocker = self.caster.level.get_unit_at(x, y)
            if blocker:
                return

            for q in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:-1]:
                self.caster.level.deal_damage(q.x, q.y, 0, Tags.Arcane, self)
                yield

            bomb = self.spawn()
            self.summon(bomb, target=Point(x, y))

    if cls is GhostFreeze:

        def cast(self, x, y):

            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y)):
                self.caster.level.show_effect(p.x, p.y, Tags.Ice)
                yield

            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.apply_buff(FrozenBuff(), self.get_stat('duration'))

    if cls is CyclopsAllyBat:

        def cast(self, x, y):
            
            target = self.caster.level.get_unit_at(x, y)
            if not target:
                return

            chump = self.get_chump(target.x, target.y)
            if not chump:
                return

            dest = self.caster.level.get_summon_point(x, y, radius_limit=1, diag=True)
            if not dest:
                return

            chump.invisible = True
            self.caster.level.act_move(chump, dest.x, dest.y, teleport=True)
            for p in self.caster.level.get_points_in_line(chump, dest):
                self.caster.level.leap_effect(p.x, p.y, Tags.Physical.color, chump)
                yield
            chump.invisible = False
            
            target.deal_damage(self.get_stat('damage'), Tags.Physical, self)
            chump.deal_damage(self.get_stat('damage'), Tags.Physical, self)

    if cls is CyclopsEnemyBat:

        def cast(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return
            # If the level is totally full, just whack the guy and call it a day
            unit.deal_damage(self.get_stat('damage'), Tags.Physical, self)
            target = self.get_destination(unit)
            if not target:
                return

            unit.invisible = True
            self.caster.level.act_move(unit, target.x, target.y, teleport=True)
            for p in self.caster.level.get_points_in_line(unit, target):
                self.caster.level.leap_effect(p.x, p.y, Tags.Physical.color, unit)
                yield
            unit.invisible = False

    if cls is JarAlly:

        def cast(self, x, y):

            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:-1]:
                self.caster.level.deal_damage(p.x, p.y, 0, Tags.Dark, self)
                yield

            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return

            unit.max_hp -= 10
            unit.max_hp = max(1, unit.max_hp)
            unit.cur_hp = min(unit.cur_hp, unit.max_hp)

            buff = Soulbound(self.caster)
            unit.apply_buff(buff)

    if cls is WizardIcicle:

        def cast(self, x, y):
            i = 0
            for point in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:-1]:
                i += 1
                i = i % 2
                dtype = self.damage_type[i]
                self.caster.level.flash(point.x, point.y, dtype.color)
                yield

            for dtype in self.damage_type:
                self.caster.level.deal_damage(x, y, self.get_stat('damage'), dtype, self)
                for i in range(7):
                    yield

    if cls is WizardIgnitePoison:

        def cast(self, x, y):

            i = 0
            dtypes = [Tags.Fire, Tags.Poison]
            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:-1]:
                i += 1
                i %= 2
                self.caster.level.deal_damage(p.x, p.y, 0, dtypes[i], self)
                yield True

            # Why would we ever not have the buff?  Some krazy buff triggers probably
            target = self.caster.level.get_unit_at(x, y)
            assert(target)

            buff = target.get_buff(Poison)
            if buff:
                target.deal_damage(buff.turns_left, Tags.Fire, self)
                target.remove_buff(buff)

            yield False

    if cls is SpellUpgrade:

        def get_description(self):
            return self.description.format(**self.prereq.fmt_dict()) if self.description else None

    if cls is BlinkSpell:

        def on_init(self):
            self.range = 5
            self.requires_los = True
            self.name = "Blink"
            self.max_charges = 6
            self.tags = [Tags.Arcane, Tags.Sorcery, Tags.Translocation]
            self.level = 3

            self.upgrades['requires_los'] = (-1, 2, "Blindcasting", "Blink can be cast without line of sight")
            self.upgrades['range'] = (3, 3)
            self.upgrades['max_charges'] = (5, 2)
            self.upgrades['lightning_blink'] = (1, 4, "Lightning Blink", "Blink deals lightning damage in a [{radius}_tile:radius] burst upon arrival.\nThe damage is equal to twice the distance travelled, rounded up.", 'damage')
            self.upgrades['dark_blink'] = (1, 4, "Dark Blink", "Blink deals dark damage in a [{radius}_tile:radius] burst upon arrival.\nThe damage is equal to twice the distance travelled, rounded up.", 'damage')

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["radius"] = self.get_stat("radius", base=3)
            return stats

    if cls is ThunderStrike:

        def get_description(self):
            return ("Deal [{damage}_lightning:lightning] damage to the target.\n"
                    "[Stun] all enemies in a [{radius}_tile:radius] burst around the target for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is StoneAuraSpell:

        def get_description(self):
            return ("Each turn, inflict [petrify] on up to [{num_targets}:num_targets] unpetrified enemy units in a [{radius}_tile:radius] radius for [{petrify_duration}_turns:duration].\n" +
                    text.petrify_desc + '\n'
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is FrozenOrbSpell:

        def on_init(self):
            self.name = "Ice Orb"

            self.minion_damage = 7
            self.radius = 3
            self.range = 9
            self.minion_health = 40
            self.level = 4

            self.max_charges = 5

            self.tags = [Tags.Orb, Tags.Conjuration, Tags.Ice]

            self.freeze_chance = 0
            self.upgrades['freeze_chance'] = (50, 3, "Freeze Chance", "The orb has a 50% chance to [freeze] damaged targets for [{duration}_turns:duration].")
            self.upgrades['radius'] = (2, 2)
            self.upgrades['minion_damage'] = (5, 3)

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["duration"] = self.get_stat("duration")
            return stats

    if cls is WheelOfFate:

        def on_init(self):
            self.name = "Wheel of Death"
            self.damage = 200
            self.range = 0
            self.tags = [Tags.Dark, Tags.Sorcery]
            self.element = Tags.Dark
            self.level = 4
            self.max_charges = 5

            self.upgrades['max_charges'] = (3, 4)
            self.upgrades['cascade'] = (1, 7, "Death Roulette", "On kill, gain a Roulette stack for [{duration}_turns:duration].\nWheel of death hits an additional enemy for each Roulette stack you have at cast time.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["duration"] = self.get_stat("duration", base=10)
            return stats

    if cls is SummonBlueLion:

        def on_init(self):
            self.name = "Blue Lion"
            self.tags = [Tags.Nature, Tags.Holy, Tags.Conjuration, Tags.Arcane]
            self.max_charges = 2
            self.level = 5
            self.minion_health = 28
            self.minion_damage = 7
            self.shield_max = 2
            self.shield_cooldown = 3

            self.upgrades['shield_max'] = (2, 4)
            self.upgrades['shield_cooldown'] = (-1, 2)
            self.upgrades['minion_damage'] = (9, 2)
            self.upgrades['holy_bolt'] = (1, 4, "Holy Bolt", "The Blue Lion's melee attack is replaced by a [{minion_range}_range:minion_range] [holy] bolt attack.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_range"] = self.get_stat("minion_range", base=6)
            return stats

    if cls is HolyFlame:

        def get_description(self):
            return ("Deal [{damage}_fire:fire] damage in a vertical line and [{damage}_holy:holy] damage in a horizontal line.\n"
                    "[Stun] [demon] and [undead] units in the affected area for [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is HeavensWrath:

        def on_init(self):

            self.name = "Heaven's Wrath"

            self.num_targets = 3

            self.damage = 22

            self.level = 6
            self.max_charges = 4

            self.upgrades['culling'] = (1, 3, "Culling" ,"Heaven's Wrath also damages the units with the lowest current HP.")
            self.upgrades['damage'] = (11, 3)
            self.upgrades['stun'] = (1, 3, "Stun", "Targets will also be [stunned] for [{duration}_turns:duration].")

            self.tags = [Tags.Holy, Tags.Lightning, Tags.Sorcery]
            self.range = 0

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["duration"] = self.get_stat("duration", base=3)
            return stats

        def cast(self, x, y):

            orders = [-1]
            if self.get_stat('culling'):
                orders.append(1)

            stun = self.get_stat("stun")
            for order in orders:
                units = [u for u in self.caster.level.units if are_hostile(u, self.caster) and not u.is_lair]
                random.shuffle(units)
                units = sorted(units,  key=lambda u: order * u.cur_hp)
                units = units[:self.get_stat('num_targets')]

                for unit in units:
                    unit.deal_damage(self.get_stat('damage'), Tags.Lightning, self)
                    for i in range(3):
                        yield
                    unit.deal_damage(self.get_stat('damage'), Tags.Holy, self)
                    for i in range(3):
                        yield
                    if stun:
                        unit.apply_buff(Stun(), self.get_stat("duration", base=3))

    if cls is FlockOfEaglesSpell:

        def on_init(self):

            self.name = "Flock of Eagles"

            self.minion_health = 18
            self.minion_damage = 6
            self.minion_range = 5
            self.num_summons = 4
            self.shields = 0

            self.max_charges = 2

            self.upgrades['dive_attack'] = (1, 4, "Dive Attack", "Grants the eagles a dive attack with [{minion_range}_range:minion_range].")
            self.upgrades['num_summons'] = (2, 3)
            self.upgrades['shields'] = (2, 4)
            self.upgrades['thunderbirds'] = 1, 4, "Thunderbirds", "Summon thunderbirds instead of eagles.  Thunderbirds deal and resist [lightning] damage."

            self.range = 0

            self.level = 5
            self.tags = [Tags.Conjuration, Tags.Nature, Tags.Holy]

    if cls is SummonSeraphim:

        def on_init(self):
            self.name = "Call Seraph"
            self.range = 4
            self.max_charges = 4
            self.tags = [Tags.Holy, Tags.Fire, Tags.Conjuration]

            self.minion_health = 33
            self.shields = 3
            self.minion_damage = 14

            self.minion_duration = 14
            self.heal = 0

            self.upgrades['minion_damage'] = (10, 4)
            self.upgrades['minion_duration'] = (14, 2)
            self.upgrades['moonblade'] = (1, 3, "Moonblade", "The Seraph also deals arcane damage with its cleave attack.")
            self.upgrades['essence'] = (1, 5, "Essence Aura", "The Seraph increases the duration of all temporary allies within [{radius}_tiles:radius] by 1 each turn.", "aura")
            self.upgrades['heal'] = (1, 2, "Heal Aura", "The Seraph heals all your other minions within [{radius}_tiles:radius] for 5 HP each turn.", "aura")
            self.upgrades['holy_fire'] = (1, 5, "Holy Fire Aura", "The Seraph gains a damage aura, randomly dealing either [2_fire:fire] or [2_holy:holy] damage to enemies within [{radius}_tiles:radius] each turn.", "aura")
            self.level = 4

            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["radius"] = self.get_stat("radius", base=5)
            return stats

        def cast_instant(self, x, y):

            angel = Unit()
            angel.name = "Seraph"
            angel.asset_name = "seraphim"
            angel.tags = [Tags.Holy]

            angel.max_hp = self.get_stat('minion_health')
            angel.shields = self.get_stat('shields')

            angel.resists[Tags.Holy] = 100
            angel.resists[Tags.Dark] = 75
            angel.resists[Tags.Fire] = 75

            sword = SeraphimSwordSwing()
            sword.damage = self.get_stat('minion_damage')
            sword.all_damage_types = True
            if self.get_stat('moonblade'):
                sword.damage_type.append(Tags.Arcane)
            angel.spells.append(sword)
            angel.flying = True
            if self.get_stat('heal'):
                angel.buffs.append(HealAuraBuff(5, self.get_stat("radius", base=5)))

            if self.get_stat('essence'):
                aura = EssenceAuraBuff()
                aura.radius = self.get_stat("radius", base=5)
                angel.buffs.append(aura)

            if self.get_stat('holy_fire'):
                aura = DamageAuraBuff(damage=2, damage_type=[Tags.Fire, Tags.Holy], radius=self.get_stat("radius", base=5))
                angel.buffs.append(aura)

            angel.turns_to_death = self.get_stat('minion_duration')

            self.summon(angel, Point(x, y))

    if cls is EssenceAuraBuff:

        def on_init(self):
            self.radius = 5
            self.color = Tags.Conjuration.color

        def get_tooltip(self):
            return "Each turn, increase the remaining duration of temporary allies within %i tiles by 1 turn." % self.radius

    if cls is ConductanceSpell:

        def get_description(self):
            return ("Curse an enemy with the essence of conductivity.\n"
                    "That enemy loses [50_lightning:lightning] resist.\n"
                    "Whenever you cast a [lightning] spell targeting that enemy, copy that spell [{copies}:lightning] times.\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is PlagueOfFilth:

        def on_init(self):

            self.tags = [Tags.Nature, Tags.Dark, Tags.Conjuration]
            self.name = "Plague of Filth"
            self.minion_health = 12
            self.minion_damage = 2
            self.minion_range = 4

            self.minion_duration = 7
            self.num_summons = 2
            self.radius = 2
            self.minion_range = 4

            self.max_channel = 15

            self.level = 3
            self.max_charges = 5

            self.upgrades['num_summons'] = (2, 4)
            self.upgrades['minion_duration'] = (4, 3)
            self.upgrades['minion_damage'] = (3, 3)
            self.upgrades['max_channel'] = (25, 1)
            self.upgrades['snakes'] = (1, 2, "Serpent Plague", "Plague of Filth has a 50% chance of summoning a snake instead of a fly swarm or frog.\nSnakes have 3/4 the health of toads and deal 1 more damage.\nSnakes apply [{duration}_turns:duration] of [poison] on hit.")

        def fmt_dict(self):
            d = Spell.fmt_dict(self)
            d['fly_health'] = d['minion_health'] // 2
            d['fly_damage'] = d['minion_damage'] // 2
            d["duration"] = self.get_stat("duration", base=5)
            return d

        def get_description(self):
            return ("Summon a group of [{num_summons}:num_summons] toads and fly swarms.\n"
                    "Toads have [{minion_health}_HP:minion_health].\n"
                    "Toads have a tongue attack with [{minion_range}_range:range] which deals [{minion_damage}_physical:physical] damage and pulls enemies towards it.\n"
                    "Toads can hop up to [4_tiles:range] away.\n"
                    "Fly swarms have [{fly_health}_HP:minion_health], [75_dark:dark] resist, [75_physical:physical] resist, [-50_ice:ice] resist, and can fly.\n"
                    "Fly swarms have a melee attack which deals [{fly_damage}_physical:physical] damage.\n"
                    "The summons vanish after [{minion_duration}_turns:minion_duration].\n"
                    "This spell can be channeled for up to [{max_channel}_turns:duration].").format(**self.fmt_dict())

        def cast(self, x, y, channel_cast=False):

            if not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)), self.get_stat('max_channel'))
                return

            for i in range(self.get_stat('num_summons')):

                if self.get_stat('snakes') and random.random() < .5:
                    unit = Snake()
                    unit.max_hp = (self.get_stat('minion_health') * 3) // 4
                    unit.spells[0].damage = self.get_stat('minion_damage') + 1
                    unit.spells[0].buff_duration = self.get_stat("duration", base=5)

                elif random.random() < .5:
                    unit = HornedToad()
                    unit.max_hp = self.get_stat('minion_health')
                    for s in unit.spells:
                        if hasattr(s, 'damage'):
                            s.damage = self.get_stat('minion_damage')
                    unit.spells[2].range = self.get_stat("minion_range")
                else:
                    unit = FlyCloud()
                    unit.max_hp = self.get_stat('minion_health') // 2
                    unit.spells[0].damage = self.get_stat('minion_damage') // 2
                
                unit.turns_to_death = self.get_stat('minion_duration')
                self.summon(unit, Point(x, y), radius=self.get_stat('radius'), sort_dist=False)
                yield

    if cls is ToxicSpore:

        def on_init(self):
            self.name = "Toxic Spores"

            self.level = 2
            self.tags = [Tags.Conjuration, Tags.Nature]
            self.range = 8
            self.max_charges = 16	

            example = GreenMushboom()
            self.minion_health = example.max_hp
            self.minion_damage = example.spells[0].damage

            self.num_summons = 2
            self.minion_range = 2
            self.upgrades['num_summons'] = (2, 3)
            self.upgrades['grey_mushboom'] = (1, 2, "Grey Mushbooms", "Summon grey mushbooms instead, which which do not apply [poison] but apply [stun] for [{glass_attack_duration}_turns:duration] on attack and [{glass_boom_duration}_turns:duration] when exploding.", "color")
            self.upgrades['red_mushboom'] = (1, 5, "Red Mushbooms", "Summon red mushbooms instead, which do not apply [poison] but deal [{red_attack_damage}_fire:fire] damage on attack and [{red_boom_damage}_fire:fire] damage when exploding.", "color")
            self.upgrades['glass_mushboom'] = (1, 6, "Glass Mushbooms", "Summon glass mushbooms instead, which which do not apply [poison] but apply [glassify] for [{glass_attack_duration}_turns:duration] on attack and [{glass_boom_duration}_turns:duration] when exploding.", "color")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["green_attack_duration"] = self.get_stat("duration", base=4)
            stats["green_boom_duration"] = self.get_stat("duration", base=12)
            stats["red_attack_damage"] = self.get_stat("minion_damage", base=5)
            stats["red_boom_damage"] = self.get_stat("minion_damage", base=9)
            stats["glass_attack_duration"] = self.get_stat("duration", base=2)
            stats["glass_boom_duration"] = self.get_stat("duration", base=3)
            return stats

        def get_description(self):
            return ("Summons [{num_summons}:num_summons] Mushbooms.\n"
                    "Mushbooms have [{minion_health}_HP:minion_health].\n"
                    "Mushbooms have a ranged attack dealing [{minion_damage}_poison:poison] damage and inflicting [{green_attack_duration}_turns:duration] of [poison].\n"
                    "Mushbooms inflict [{green_boom_duration}_turns:duration] of [poison] on units in melee range when they die.").format(**self.fmt_dict())

        def cast(self, x, y):
            green = 0
            grey = self.get_stat('grey_mushboom')
            red = self.get_stat('red_mushboom')
            glass = self.get_stat('glass_mushboom')
            for _ in range(self.get_stat('num_summons')):
                if red:
                    mushboom = RedMushboom()
                elif grey:
                    mushboom = GreyMushboom()
                    duration = self.get_stat("duration", base=2)
                    spell = mushboom.spells[0]
                    spell.onhit = None
                    spell.buff = Stun
                    spell.buff_duration = duration
                    spell.buff_name = "Stunned"
                    spell.description = ""
                elif glass:
                    mushboom = GlassMushboom()
                    duration = self.get_stat("duration", base=2)
                    spell = mushboom.spells[0]
                    spell.onhit = None
                    spell.buff = GlassPetrifyBuff
                    spell.buff_duration = duration
                    spell.buff_name = "Glassed"
                    spell.description = ""
                else:
                    mushboom = GreenMushboom()
                    green = 1
                    duration = self.get_stat("duration", base=4)
                    spell = mushboom.spells[0]
                    spell.onhit = None
                    spell.buff = Poison
                    spell.buff_duration = duration
                    spell.buff_name = "Poison"
                    spell.description = ""
                if green or grey or glass:
                    mushboom.buffs[0].apply_duration = self.get_stat("duration", base=mushboom.buffs[0].apply_duration)
                else:
                    mushboom.buffs[0].damage = self.get_stat("minion_damage", base=9)
                apply_minion_bonuses(self, mushboom)
                self.summon(mushboom, target=Point(x, y))
                yield

    if cls is PyrostaticHexSpell:

        def on_init(self):
            self.name = "Pyrostatic Curse"

            self.tags = [Tags.Fire, Tags.Lightning, Tags.Enchantment]
            self.level = 5
            self.max_charges = 7

            self.radius = 4
            self.range = 9
            self.duration = 4
            self.num_targets = 2

            self.upgrades['radius'] = (3, 2)
            self.upgrades['duration'] = (6, 3)
            self.upgrades['beam'] = (1, 5, "Linear Conductance", "Redealt [lightning] damage is dealt along a beam instead of just to one target.")

        def get_description(self):
            return ("Curses targets in a [{radius}_tile:radius] radius for [{duration}_turns:duration].\n"
                    "Whenever a cursed target takes [fire] damage, [{num_targets}:num_targets] random enemy units in line of sight of that unit are dealt half that much [lightning] damage.").format(**self.fmt_dict())

    if cls is PyroStaticHexBuff:

        def __init__(self, spell):
            self.spell = spell
            Buff.__init__(self)

        def on_init(self):
            self.name = "Pyrostatic Hex"
            self.beam = self.spell.get_stat("beam")
            self.buff_type = BUFF_TYPE_CURSE
            self.stack_type = STACK_REPLACE
            self.color = Tags.Fire.color
            self.owner_triggers[EventOnDamaged] = self.on_damage
            self.asset = ['status', 'pyrostatic_hex']

        def deal_damage(self, evt):

            redeal_targets = [u for u in self.owner.level.get_units_in_los(self.owner) if are_hostile(u, self.spell.owner) and u != self.owner]
            random.shuffle(redeal_targets)

            for t in redeal_targets[:self.spell.get_stat("num_targets")]:
                for p in self.owner.level.get_points_in_line(self.owner, t)[1:-1]:
                    self.owner.level.deal_damage(p.x, p.y, evt.damage//2 if self.beam else 0, Tags.Lightning, self.spell)
                t.deal_damage(evt.damage//2, Tags.Lightning, self.spell)
            yield

    if cls is MercurizeSpell:

        def on_init(self):
            self.name = "Mercurize"

            self.level = 3
            self.tags = [Tags.Dark, Tags.Metallic, Tags.Enchantment, Tags.Conjuration]

            self.damage = 2

            self.max_charges = 6
            self.duration = 6

            self.range = 8

            self.minion_damage = 10

            self.upgrades['damage'] = (4, 4)
            self.upgrades['duration'] = (10, 3)
            self.upgrades['dark'] = (1, 2, "Morbidity", "Mercurized targets also take dark damage")
            self.upgrades['corrosion'] = (1, 2, "Corrosion", "Mercurized targets lose 25 physical resist")
            self.upgrades['noxious_aura'] = (1, 5, "Toxic Fumes", "Quicksilver Geists have a noxious aura that deals 1 poison damage to enemy units within [{radius}_tiles:radius] each turn.")
            self.upgrades['vengeance'] = (1, 5, "Mercurial Vengeance", "When a Quicksilver Geist is killed, its killer is affliected with Mercurize.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["radius"] = self.get_stat("radius", base=2)
            return stats

    if cls is SummonVoidDrakeSpell:

        def get_description(self):
            return ("Summon a Void Drake at target square.\n"		
                    "Void Drakes have [{minion_health}_HP:minion_health], fly, and have [100_arcane:arcane] resist.\n"
                    "Void Drakes have a breath weapon which deals [{breath_damage}_arcane:arcane] damage and melts walls.\n"
                    "Void Drakes have a melee attack which deals [{minion_damage}_physical:physical] damage.").format(**self.fmt_dict())

    if cls is Megavenom:

        def on_advance(self):
            damage = self.get_stat('damage')
            for u in list(self.owner.level.units):
                if not are_hostile(u, self.owner):
                    continue
                if u.has_buff(Poison):
                    u.deal_damage(damage, Tags.Poison, self)

    if cls is GeminiCloneSpell:

        def cast_instant(self, x, y):
            clone = Gemini()
            self.summon(clone)
            clone.cur_hp = self.caster.cur_hp

    if cls is Spells.ElementalEyeBuff:

        def on_init(self):
            self.stack_type = STACK_REPLACE

    if cls is SeraphimSwordSwing:

        def get_description(self):
            return "Deals damage to enemies in an arc."

        def cast(self, x, y):
            damage = self.get_stat('damage')
            for p in self.get_impacted_tiles(x, y):
                for dtype in self.damage_type:
                    # Never hit friendly units, is angel
                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if not unit or not are_hostile(self.caster, unit):
                        self.caster.level.show_effect(p.x, p.y, dtype)
                    else:
                        unit.deal_damage(damage, dtype, self)
                    yield

    if cls is StunImmune:

        def on_applied(self, owner):
            buffs = list(self.owner.buffs)
            for buff in buffs:
                if isinstance(buff, Stun):
                    self.owner.remove_buff(buff)

    if cls is BlindBuff:
        def on_init(self):
            self.name = "Blind"
            self.buff_type = BUFF_TYPE_CURSE
            self.asset = ['status', 'blind']
            self.color = Tags.Holy.color
            self.description = "All spells reduced to melee range"

    if cls is WriteChaosScrolls:

        def on_init(self):
            self.name = "Scribe Chaos Scrolls"
            self.num_summons = 0
            self.range = 0
            self.cool_down = 6

        def get_description(self):
            bonus = self.get_stat("num_summons")
            return "Summon %i-%i living fireball or lightning scrolls" % (2 + bonus, 4 + bonus)

        def cast(self, x, y):

            num_summons = self.get_stat("num_summons") + random.randint(2, 4)
            for _ in range(num_summons):
                unit = random.choice([LivingFireballScroll(), LivingLightningScroll()])
                apply_minion_bonuses(self.caster.source, unit)
                unit.turns_to_death = None
                self.summon(unit, sort_dist=False)
                yield

    if cls is DispersalSpell:

        def cast(self, x, y):
            for p in self.caster.level.get_units_in_ball(Point(x, y), self.get_stat('radius')):
                target = self.caster.level.get_unit_at(p.x, p.y)

                if target == self.caster:
                    continue
                
                possible_points = []
                for i in range(len(self.caster.level.tiles)):
                    for j in range(len(self.caster.level.tiles[i])):
                        if self.caster.level.can_stand(i, j, target):
                            possible_points.append(Point(i, j))

                if not possible_points:
                    return

                target_point = random.choice(possible_points)

                self.caster.level.show_effect(target.x, target.y, Tags.Translocation)
                self.caster.level.act_move(target, target_point.x, target_point.y, teleport=True)
                self.caster.level.show_effect(target.x, target.y, Tags.Translocation)

                yield

    if cls is LastWord:

        def on_init(self):
            self.name = "Last Word"

            self.description = "The turn after you finish a level, gain a charge of each of your [word] spells."
            self.tags = [Tags.Word]
            self.level = 5
            self.triggered = False
            self.owner_triggers[EventOnUnitAdded] = lambda evt: on_unit_added(self, evt)

        def on_advance(self):
            if self.triggered:
                return
            if not all(u.team == TEAM_PLAYER for u in self.owner.level.units):
                return
            self.triggered = True
            refill(self)

        def on_unit_added(self, evt):
            # Just in case the player is standing on a portal when the level ends, and immediately goes to the next level.
            if not self.triggered:
                refill(self)
            self.triggered = False

        def refill(self):
            words = [s for s in self.owner.spells if Tags.Word in s.tags and s.cur_charges < s.get_stat('max_charges')]
            for word in words:
                word.cur_charges += 1
            self.triggered = True

    if cls is BerserkShrineBuff:

        def on_damage(self, evt):
            if not evt.source:
                return
            if not isinstance(evt.source, self.spell_class):
                return
            if evt.source.owner is not self.owner:
                return
            if not are_hostile(evt.unit, self.owner):
                return

            evt.unit.apply_buff(BerserkBuff(), 1)

    if cls is StormCloudShrineBuff:

        def on_damage(self, evt):
            if not evt.source:
                return
            if not isinstance(evt.source, self.spell_class):
                return
            if not evt.source.owner == self.owner:
                return
            if not are_hostile(evt.unit, self.owner):
                return

            if type(self.owner.level.tiles[evt.unit.x][evt.unit.y].cloud) in [StormCloud, BlizzardCloud]:
                self.owner.level.queue_spell(self.deal_damage(evt))

    if cls is CruelShrineBuff:

        def on_damage(self, evt):
            if not are_hostile(evt.unit, self.owner):
                return
            if self.is_enhanced_spell(evt.source, allow_minion=True):
                evt.unit.apply_buff(Poison(), evt.damage)

    if cls is ThunderShrineBuff:

        def on_spell_cast(self, evt):
            if not isinstance(evt.source, self.spell_class):
                return
            if not evt.damage_type == Tags.Lightning:
                return
            if not evt.source.owner == self.owner:
                return
            if not are_hostile(evt.unit, self.owner):
                return

            for p in self.owner.level.get_points_in_ball(evt.unit.x, evt.unit.y, 1, diag=True):
                unit = self.owner.level.get_unit_at(p.x, p.y)	
                if unit and are_hostile(self.owner, unit):
                    if unit.has_buff(Stun):
                        continue
                    unit.apply_buff(Stun(), 1)

    for func_name, func in [(key, value) for key, value in locals().items() if callable(value)]:
        if hasattr(cls, func_name):
            setattr(cls, func_name, func)

for cls in [Frostbite, MercurialVengeance, ThunderStrike, HealAlly, AetherDaggerSpell, OrbBuff, PyGameView, HibernationBuff, Hibernation, MulticastBuff, MulticastSpell, TouchOfDeath, BestowImmortality, Enlarge, LightningHaloBuff, LightningHaloSpell, ClarityIdolBuff, Unit, Buff, HallowFlesh, DarknessBuff, VenomSpit, VenomSpitSpell, Hunger, EyeOfRageSpell, Level, ReincarnationBuff, MagicMissile, InvokeSavagerySpell, ConductanceSpell, StormNova, SummonIcePhoenix, IcePhoenixBuff, RingOfSpiders, SlimeformBuff, LightningFrenzy, ArcaneCombustion, LightningWarp, NightmareBuff, HolyBlast, FalseProphetHolyBlast, Burst, RestlessDeadBuff, FlameGateBuff, StoneAuraBuff, IronSkinBuff, HolyShieldBuff, DispersionFieldBuff, SearingSealBuff, MercurizeBuff, MagnetizeBuff, BurningBuff, BurningShrineBuff, EntropyBuff, EnervationBuff, OrbSpell, StormBreath, FireBreath, IceBreath, VoidBreath, HolyBreath, DarkBreath, GreyGorgonBreath, BatBreath, DragonRoarBuff, HungerLifeLeechSpell, BloodlustBuff, OrbControlSpell, SimpleBurst, PullAttack, LeapAttack, MonsterVoidBeam, ButterflyLightning, FiendStormBolt, LifeDrain, WizardLightningFlash, TideOfSin, WailOfPain, HagSwap, Approach, SimpleRangedAttack, WizardNightmare, WizardHealAura, SpiritShield, SimpleCurse, SimpleSummon, GlassyGaze, GhostFreeze, WizardBloodboil, CloudGeneratorBuff, TrollRegenBuff, DamageAuraBuff, CommonContent.ElementalEyeBuff, RegenBuff, ShieldRegenBuff, DeathExplosion, VolcanoTurtleBuff, SpiritBuff, NecromancyBuff, SporeBeastBuff, SpikeBeastBuff, BlizzardBeastBuff, VoidBomberBuff, FireBomberBuff, SpiderBuff, MushboomBuff, RedMushboomBuff, ThornQueenThornBuff, LesserCultistAlterBuff, GreaterCultistAlterBuff, CultNecromancyBuff, MagmaShellBuff, ToxicGazeBuff, ConstructShards, IronShell, ArcanePhoenixBuff, IdolOfSlimeBuff, CrucibleOfPainBuff, FieryVengeanceBuff, ConcussiveIdolBuff, VampirismIdolBuff, TeleportyBuff, LifeIdolBuff, PrinceOfRuin, StormCaller, Horror, FrozenSouls, ShrapnelBlast, ShieldSightSpell, GlobalAttrBonus, FaeThorns, Teleblink, AfterlifeShrineBuff, FrozenSkullShrineBuff, WhiteCandleShrineBuff, FaeShrineBuff, FrozenShrineBuff, CharredBoneShrineBuff, SoulpowerShrineBuff, BrightShrineBuff, GreyBoneShrineBuff, EntropyShrineBuff, EnervationShrineBuff, WyrmEggShrineBuff, ToxicAgonyBuff, BoneSplinterBuff, HauntingShrineBuff, ButterflyWingBuff, GoldSkullBuff, FurnaceShrineBuff, HeavenstrikeBuff, StormchargeBuff, WarpedBuff, TroublerShrineBuff, FaewitchShrineBuff, VoidBomberBuff, VoidBomberSuicide, FireBomberSuicide, BomberShrineBuff, SorceryShieldShrineBuff, FrostfaeShrineBuff, ChaosConductanceShrineBuff, IceSprigganShrineBuff, ChaosQuillShrineBuff, FireflyShrineBuff, DeathchillChimeraShrineBuff, BloodrageShrineBuff, RazorShrineBuff, ShatterShards, ShockAndAwe, SteamAnima, Teleport, DeathBolt, SummonIceDrakeSpell, ChannelBuff, DeathCleaveBuff, CauterizingShrineBuff, Tile, SummonSiegeGolemsSpell, Approach, Crystallographer, CrystallographerActiveBuff, Necrostatics, NecrostaticStack, HeavenlyIdol, RingOfSpiders, UnholyAlliance, TurtleDefenseBonus, TurtleBuff, NaturalVigor, OakenShrineBuff, TundraShrineBuff, SwampShrineBuff, SandStoneShrineBuff, BlueSkyShrineBuff, MatureInto, SummonWolfSpell, AnnihilateSpell, MegaAnnihilateSpell, MeltBuff, CollectedAgony, MeteorShower, WizardQuakeport, PurityBuff, SummonGiantBear, SimpleMeleeAttack, ThornQueenThornBuff, FaeCourt, GhostfireUpgrade, SplittingBuff, GeneratorBuff, RespawnAs, EventHandler, SummonFloatingEye, SlimeBuff, Bolt, Spell, Icicle, PoisonSting, ArchonLightning, PyrostaticPulse, BombToss, GhostFreeze, CyclopsAllyBat, CyclopsEnemyBat, WizardIcicle, WizardIgnitePoison, SpellUpgrade, BlinkSpell, ThunderStrike, StoneAuraSpell, FrozenOrbSpell, WheelOfFate, SummonBlueLion, HolyFlame, HeavensWrath, FlockOfEaglesSpell, SummonSeraphim, EssenceAuraBuff, ConductanceSpell, PlagueOfFilth, ToxicSpore, PyrostaticHexSpell, PyroStaticHexBuff, MercurizeSpell, SummonVoidDrakeSpell, Megavenom, GeminiCloneSpell, Spells.ElementalEyeBuff, SeraphimSwordSwing, StunImmune, BlindBuff, WriteChaosScrolls, DispersalSpell, LastWord, BerserkShrineBuff, StormCloudShrineBuff, CruelShrineBuff, ThunderShrineBuff]:
    curr_module.modify_class(cls)