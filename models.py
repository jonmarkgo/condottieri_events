## Copyright (c) 2010 by Jose Antonio Martin <jantonio.martin AT gmail DOT com>
## This program is free software: you can redistribute it and/or modify it
## under the terms of the GNU Affero General Public License as published by the
## Free Software Foundation, either version 3 of the License, or (at your option
## any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
## FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
## for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/agpl.txt>.
##
## This license is also included in the file COPYING
##
## AUTHOR: Jose Antonio Martin <jantonio.martin AT gmail DOT com>

""" This application manages the log of events during a Condottieri game.

"""

## django
from django.db import models
from condottieri_common.translation_compat import ugettext_lazy as _
from django.template.defaultfilters import capfirst
from django.contrib.auth.models import User
from django.conf import settings

## machiavelli - lazy import to avoid circular dependencies
_machiavelli_models = None

def get_machiavelli_models():
	global _machiavelli_models
	if _machiavelli_models is None:
		import machiavelli.models as _machiavelli_models
	return _machiavelli_models

import condottieri_scenarios.models as scenarios

UNIT_EVENTS = (
	(0, _('cannot carry out its support order.')),
	(1, _('must retreat.')),
	(2, _('surrenders.')),
	(3, _('starts a siege.')),
	(4, _('changes country.')),
	(5, _('becomes autonomous.')),
)

COUNTRY_EVENTS = (
	(0, _('has been overthrown.')),
	(1, _('has been conquered.')),
	(2, _('has been excommunicated.')),
	(3, _('has been eliminated.')),
	(4, _('has been assassinated.')),
	(5, _('has been forgiven.')),
	(6, _('has suffered an assassination attempt.')),
)

DISASTER_EVENTS = (
	(0, _('Famine')),
	(1, _('Plague')),
	(2, _('Rebellion')),
	(3, _('Storm')),
)

SEASONS = (
	(1, _('Spring')),
	(2, _('Summer')),
	(3, _('Fall')),
)

GAME_PHASES = (
	(0, _('Inactive game')),
	(1, _('Military adjustments')),
	(2, _('Order writing')),
	(3, _('Retreats')),
	(4, _('Strategic movement')),
)

UNIT_TYPES = (
	('A', _('Army')),
	('F', _('Fleet')),
	('G', _('Garrison')),
)

ORDER_CODES = (
	('H', _('Hold')),
	('B', _('Besiege')),
	('-', _('Advance')),
	('=', _('Conversion')),
	('C', _('Convoy')),
	('S', _('Support')),
)

ORDER_SUBCODES = (
	('H', _('Hold')),
	('-', _('Advance')),
	('=', _('Conversion')),
)

EXPENSE_TYPES = (
	(0, _("Famine relief")),
	(1, _("Pacify rebellion")),
	(2, _("Conquered province to rebel")),
	(3, _("Home province to rebel")),
	(4, _("Counter bribe")),
	(5, _("Disband autonomous garrison")),
	(6, _("Buy autonomous garrison")),
	(7, _("Convert garrison unit")),
	(8, _("Disband enemy unit")),
	(9, _("Buy enemy unit")),
	(10, _("Hire a diplomat in own area")),
	(11, _("Hire a diplomat in foreign area")),
)

class BaseEvent(models.Model):
	"""
BaseEvent is the parent class for all kind of game events.
	"""
	game = models.ForeignKey('machiavelli.Game', on_delete=models.CASCADE)
	year = models.PositiveIntegerField()
	season = models.PositiveIntegerField(choices=SEASONS)
	phase = models.PositiveIntegerField(choices=GAME_PHASES)
	classname = models.CharField(max_length=32, editable=False)
	
	def __str__(self):
		return self.event_class().event_text()
	
	def event_class(self):
		""" Returns the appropriate event class for this event. """
		from . import events
		return getattr(events, self.classname)

class NewUnitEvent(BaseEvent):
	""" Event triggered when a new unit is created. """
	country = models.ForeignKey(scenarios.Country, on_delete=models.CASCADE)
	type = models.CharField(max_length=1, choices=UNIT_TYPES)
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	
	def event_class(self):
		return NewUnitEvent

def log_new_unit(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(NewUnitEvent, sender.player.game,
					classname="NewUnitEvent",
					country=sender.player.country,
					type=sender.type,
					area=sender.area.board_area)

class DisbandEvent(BaseEvent):
	""" Event triggered when a unit is disbanded. """
	country = models.ForeignKey(scenarios.Country, blank=True, null=True, on_delete=models.CASCADE)
	type = models.CharField(max_length=1, choices=UNIT_TYPES)
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	
	def event_class(self):
		return DisbandEvent

def log_disband(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(DisbandEvent, sender.player.game,
					classname="DisbandEvent",
					country=sender.player.country,
					type=sender.type,
					area=sender.area.board_area)

class OrderEvent(BaseEvent):
	""" Event triggered when an order is confirmed. """
	country = models.ForeignKey(scenarios.Country, on_delete=models.CASCADE)
	type = models.CharField(max_length=1, choices=UNIT_TYPES)
	origin = models.ForeignKey(scenarios.Area, related_name='event_origin', on_delete=models.CASCADE)
	code = models.CharField(max_length=1, choices=ORDER_CODES)
	destination = models.ForeignKey(scenarios.Area, blank=True, null=True, related_name='event_destination', on_delete=models.CASCADE)
	conversion = models.CharField(max_length=1, choices=UNIT_TYPES, blank=True, null=True)
	subtype = models.CharField(max_length=1, choices=UNIT_TYPES, blank=True, null=True)
	suborigin = models.ForeignKey(scenarios.Area, related_name='event_suborigin', blank=True, null=True, on_delete=models.CASCADE)
	subcode = models.CharField(max_length=1, choices=ORDER_SUBCODES, blank=True, null=True)
	subdestination = models.ForeignKey(scenarios.Area, blank=True, null=True, related_name='event_subdestination', on_delete=models.CASCADE)
	subconversion = models.CharField(max_length=1, choices=UNIT_TYPES, blank=True, null=True)
	
	def event_class(self):
		return OrderEvent

def log_order(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Order), "sender must be an Order"
	try:
		destination = sender.destination.board_area
	except:
		destination = None
	if isinstance(sender.subunit, get_machiavelli_models().Unit):
		subtype = sender.subunit.type
		suborigin = sender.subunit.area.board_area
	else:
		subtype = None
		suborigin = None
	try:
		subdestination = sender.subdestination.board_area
	except:
		subdestination = None
	log_event(OrderEvent, sender.unit.player.game,
					classname="OrderEvent",
					country=sender.unit.player.country,
					type=sender.unit.type,
					origin=sender.unit.area.board_area,
					code=sender.code,
					destination=destination,
					conversion=sender.conversion,
					subtype=subtype,
					suborigin=suborigin,
					subcode=sender.subcode,
					subdestination=subdestination,
					subconversion=sender.subconversion)

class StandoffEvent(BaseEvent):
	""" Event triggered when a standoff occurs. """
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	
	def event_class(self):
		return StandoffEvent

def log_standoff(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().GameArea), "sender must be a GameArea"
	log_event(StandoffEvent, sender.game,
					classname="StandoffEvent",
					area=sender.board_area)

class ConversionEvent(BaseEvent):
	""" Event triggered when a unit is converted. """
	country = models.ForeignKey(scenarios.Country, null=True, blank=True, on_delete=models.CASCADE)
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	before = models.CharField(max_length=1, choices=UNIT_TYPES)
	after = models.CharField(max_length=1, choices=UNIT_TYPES)
	
	def event_class(self):
		return ConversionEvent

def log_conversion(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(ConversionEvent, sender.player.game,
					classname="ConversionEvent",
					country=sender.player.country,
					area=sender.area.board_area,
					before=sender.type,
					after=sender.conversion)

class ControlEvent(BaseEvent):
	""" Event triggered when control of an area changes. """
	country = models.ForeignKey(scenarios.Country, null=True, blank=True, on_delete=models.CASCADE)
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	
	def event_class(self):
		return ControlEvent

def log_control(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().GameArea), "sender must be a GameArea"
	log_event(ControlEvent, sender.player.game,
					classname="ControlEvent",
					country=sender.player.country,
					area=sender.board_area)

class MovementEvent(BaseEvent):
	""" Event triggered when a unit moves. """
	country = models.ForeignKey(scenarios.Country, null=True, blank=True, on_delete=models.CASCADE)
	type = models.CharField(max_length=1, choices=UNIT_TYPES)
	origin = models.ForeignKey(scenarios.Area, related_name="movement_origin", on_delete=models.CASCADE)
	destination = models.ForeignKey(scenarios.Area, related_name="movement_destination", on_delete=models.CASCADE)
	
	def event_class(self):
		return MovementEvent

def log_movement(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(MovementEvent, sender.player.game,
					classname="MovementEvent",
					country=sender.player.country,
					type=sender.type,
					origin=sender.area.board_area,
					destination=sender.destination.board_area)

class RetreatEvent(BaseEvent):
	""" Event triggered when a unit retreats. """
	country = models.ForeignKey(scenarios.Country, null=True, blank=True, on_delete=models.CASCADE)
	type = models.CharField(max_length=1, choices=UNIT_TYPES)
	origin = models.ForeignKey(scenarios.Area, related_name="retreat_origin", on_delete=models.CASCADE)
	destination = models.ForeignKey(scenarios.Area, related_name="retreat_destination", on_delete=models.CASCADE)
	
	def event_class(self):
		return RetreatEvent

def log_retreat(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(RetreatEvent, sender.player.game,
					classname="RetreatEvent",
					country=sender.player.country,
					type=sender.type,
					origin=sender.area.board_area,
					destination=sender.destination.board_area)

class UnitEvent(BaseEvent):
	""" Event triggered when a unit is affected by a special event. """
	country = models.ForeignKey(scenarios.Country, null=True, blank=True, on_delete=models.CASCADE)
	type = models.CharField(max_length=1, choices=UNIT_TYPES)
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	message = models.PositiveIntegerField(choices=UNIT_EVENTS)
	
	def event_class(self):
		return UnitEvent

def log_broken_support(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(UnitEvent, sender.player.game,
					classname="UnitEvent",
					country=sender.player.country,
					type=sender.type,
					area=sender.area.board_area,
					message=UNIT_EVENTS[0][1])

def log_forced_retreat(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(UnitEvent, sender.player.game,
				classname="UnitEvent",
				country=sender.player.country,
				type=sender.type,
				area=sender.area.board_area,
				message=UNIT_EVENTS[1][1])

def log_unit_surrender(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(UnitEvent, sender.player.game,
				classname="UnitEvent",
				country=sender.player.country,
				type=sender.type,
				area=sender.area.board_area,
				message=UNIT_EVENTS[2][1])

def log_siege_start(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(UnitEvent, sender.player.game,
				classname="UnitEvent",
				country=sender.player.country,
				type=sender.type,
				area=sender.area.board_area,
				message=UNIT_EVENTS[3][1])

def log_change_country(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(UnitEvent, sender.player.game,
				classname="UnitEvent",
				country=sender.player.country,
				type=sender.type,
				area=sender.area.board_area,
				message=UNIT_EVENTS[4][1])

def log_to_autonomous(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Unit), "sender must be a Unit"
	log_event(UnitEvent, sender.player.game,
				classname="UnitEvent",
				country=sender.player.country,
				type=sender.type,
				area=sender.area.board_area,
				message=UNIT_EVENTS[5][1])

def log_overthrow(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Revolution), "sender must be a Revolution"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country)

def log_conquering(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Player), "sender must be a Player"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country)

def log_excommunication(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Player), "sender must be a Player"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country)

def log_elimination(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Player), "sender must be a Player"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country)

def log_assassination(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Player), "sender must be a Player"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country)

def log_lifted_excommunication(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Player), "sender must be a Player"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country)

def log_assassination_attempt(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Player), "sender must be a Player"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country)

def log_famine_marker(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().GameArea), "sender must be a GameArea"
	log_event(DisasterEvent, sender.game,
					classname="DisasterEvent",
					area=sender.board_area)

def log_plague(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().GameArea), "sender must be a GameArea"
	log_event(DisasterEvent, sender.game,
					classname="DisasterEvent",
					area=sender.board_area)

def log_rebellion(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().GameArea), "sender must be a GameArea"
	log_event(DisasterEvent, sender.game,
					classname="DisasterEvent",
					area=sender.board_area)

def log_storm_marker(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().GameArea), "sender must be a GameArea"
	log_event(DisasterEvent, sender.game,
					classname="DisasterEvent",
					area=sender.board_area)

def log_income(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Player), "sender must be a Player"
	log_event(IncomeEvent, sender.game,
					classname="IncomeEvent",
					country=sender.country)

class ExpenseEvent(BaseEvent):
	""" Event triggered when a country spends ducats. """
	country = models.ForeignKey(scenarios.Country, on_delete=models.CASCADE)
	ducats = models.PositiveIntegerField(default=0)
	type = models.PositiveIntegerField(choices=EXPENSE_TYPES)
	area = models.ForeignKey(scenarios.Area, null=True, blank=True, on_delete=models.CASCADE)
	unit_type = models.CharField(max_length=1, choices=UNIT_TYPES, null=True, blank=True)
	
	def event_class(self):
		return ExpenseEvent

def log_expense(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Expense), "sender must be an Expense"
	if sender.unit:
		_area = sender.unit.area.board_area
		_unit_type = sender.unit.type
	else:
		_area = None
		_unit_type = None
	log_event(ExpenseEvent, sender.player.game,
					classname="ExpenseEvent",
					country=sender.player.country,
					ducats=sender.ducats,
					type=sender.type,
					area=_area,
					unit_type=_unit_type)

class UncoverEvent(BaseEvent):
	""" Event triggered when a diplomat uncovers a unit. """
	country = models.ForeignKey(scenarios.Country, on_delete=models.CASCADE)
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	
	def event_class(self):
		return UncoverEvent

def log_uncover(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().Diplomat), "sender must be a Diplomat"
	log_event(UncoverEvent, sender.player.game,
					classname="UncoverEvent",
					country=sender.player.country,
					area=sender.area.board_area)

class CountryEvent(BaseEvent):
	""" Event triggered when a country is subject to some conditions.

	Currently, the conditions are:
	
	* A new player (not playing) takes the control of the country.
	
	* The country has been conquered.
	
	* The country has been excommunicated.

	* The country has been eliminated.

	* The leader has been assassinated.

	* An excommunication has been lifted.

	* An assassination has been attempted.
	
	Each condition must have its own signal.
	"""
	country = models.ForeignKey(scenarios.Country, on_delete=models.CASCADE)
	message = models.PositiveIntegerField(choices=COUNTRY_EVENTS)

	def event_class(self):
		return CountryEvent

def log_country_event(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().CountryEvent), "sender must be a CountryEvent"
	log_event(CountryEvent, sender.game,
					classname="CountryEvent",
					country=sender.country,
					message=sender.message)

class DisasterEvent(BaseEvent):
	""" Event triggered when a province is affected by a disaster.

	Currently, the conditions are:
	
	* The province is affected by famine.
	
	* The province is affected by plague.

	* The province is affected by a rebellion.

	* The sea is affected by a storm
	
	Each condition must have its own signal.
	"""
	area = models.ForeignKey(scenarios.Area, on_delete=models.CASCADE)
	message = models.PositiveIntegerField(choices=DISASTER_EVENTS)

	def event_class(self):
		return DisasterEvent

def log_disaster(sender, **kwargs):
	assert isinstance(sender, get_machiavelli_models().DisasterEvent), "sender must be a DisasterEvent"
	log_event(DisasterEvent, sender.game,
					classname="DisasterEvent",
					area=sender.area.board_area,
					message=sender.message)

class IncomeEvent(BaseEvent):
	""" Event triggered when a country receives income """
	country = models.ForeignKey(scenarios.Country, on_delete=models.CASCADE)
	ducats = models.PositiveIntegerField()

	def event_class(self):
		return IncomeEvent

def log_event(event_class, game, **kwargs):
	""" Creates a new event of the specified class. """
	event = event_class(game=game, **kwargs)
	event.save()
	return event

