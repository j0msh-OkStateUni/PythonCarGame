"""
OOP GARAGE CHAMPIONSHIP
=======================

A self-contained terminal game designed as an applied reference for the main
object-oriented programming concepts in Python.

Run it:
    python oop_garage_game.py

Useful learning modes:
    python oop_garage_game.py --concepts   # Print the OOP concept map
    python oop_garage_game.py --demo       # Run a short non-interactive race
    python oop_garage_game.py --self-test  # Check the main game systems

While reading, search for comments beginning with ``# OOP:``. Each one marks
an example of a specific object-oriented concept.

This project demonstrates:
    * classes and objects
    * instance and class attributes
    * instance, class, and static methods
    * encapsulation and properties
    * inheritance and ``super()``
    * abstract base classes
    * method overriding
    * polymorphism
    * composition and aggregation
    * protocols (interface-like typing)
    * dataclasses and enums
    * custom exceptions
    * dunder methods
    * the Strategy and Factory design patterns
    * JSON serialization and object reconstruction

It intentionally uses only Python's standard library.
"""

from __future__ import annotations

import argparse
import json
import random
import tempfile
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterator, Protocol


SAVE_FILE = Path("oop_garage_save.json")


# ---------------------------------------------------------------------------
# OOP: CUSTOM EXCEPTIONS
# ---------------------------------------------------------------------------


class GarageGameError(Exception):
    """Base exception for errors that the game knows how to explain."""


class NotEnoughCreditsError(GarageGameError):
    """Raised when a player tries to spend more credits than they own."""


class GarageFullError(GarageGameError):
    """Raised when there is no room for another spare part."""


class InvalidPartError(GarageGameError):
    """Raised when an unknown or incompatible part is used."""


class SaveDataError(GarageGameError):
    """Raised when saved data cannot be reconstructed safely."""


# ---------------------------------------------------------------------------
# OOP: ENUMS AND DATACLASSES
# ---------------------------------------------------------------------------


class Surface(Enum):
    """A fixed set of valid track surfaces."""

    ASPHALT = "Asphalt"
    DIRT = "Dirt"
    WET = "Wet"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Track:
    """A small immutable data object describing a race track."""

    name: str
    surface: Surface
    difficulty: int
    length: int
    prize: int

    def __post_init__(self) -> None:
        if not 1 <= self.difficulty <= 10:
            raise ValueError("Track difficulty must be from 1 to 10.")
        if self.length <= 0:
            raise ValueError("Track length must be positive.")


TRACKS: tuple[Track, ...] = (
    Track("Harbor Sprint", Surface.ASPHALT, difficulty=2, length=3, prize=500),
    Track("Dust Bowl Rally", Surface.DIRT, difficulty=4, length=5, prize=800),
    Track("Storm Circuit", Surface.WET, difficulty=5, length=6, prize=1_100),
    Track("Mountain Gauntlet", Surface.ASPHALT, difficulty=7, length=8, prize=1_600),
)


# ---------------------------------------------------------------------------
# OOP: PROTOCOL (AN INTERFACE-LIKE CONTRACT)
# ---------------------------------------------------------------------------


class Purchasable(Protocol):
    """Anything with these properties can be passed to Player.buy()."""

    @property
    def name(self) -> str: ...

    @property
    def price(self) -> int: ...


# ---------------------------------------------------------------------------
# OOP: ABSTRACTION, ENCAPSULATION, PROPERTIES, AND INHERITANCE
# ---------------------------------------------------------------------------


class CarPart(ABC):
    """Abstract parent class shared by every type of car part."""

    category: ClassVar[str] = "Part"
    total_parts_created: ClassVar[int] = 0  # Shared by the whole class family.

    def __init__(
        self,
        code: str,
        name: str,
        price: int,
        performance: int,
        reliability: int,
        weight: int,
    ) -> None:
        self._validate_rating(performance, "performance")
        self._validate_rating(reliability, "reliability")
        if price < 0 or weight <= 0:
            raise ValueError("Price cannot be negative and weight must be positive.")

        # A leading underscore marks attributes as protected implementation
        # details. Outside code reads them through properties instead.
        self._code = code
        self._name = name
        self._price = price
        self._performance = performance
        self._reliability = reliability
        self._weight = weight
        self._durability = 100.0
        CarPart.total_parts_created += 1

    # OOP: Properties provide controlled, read-only access to internal state.
    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def price(self) -> int:
        return self._price

    @property
    def performance(self) -> int:
        return self._performance

    @property
    def reliability(self) -> int:
        return self._reliability

    @property
    def weight(self) -> int:
        return self._weight

    @property
    def durability(self) -> float:
        return self._durability

    @property
    def condition_factor(self) -> float:
        """Damaged parts still work, but never below 35% effectiveness."""

        return max(0.35, self._durability / 100)

    @property
    def repair_quote(self) -> int:
        missing_condition = 100 - self._durability
        return round(self._price * (missing_condition / 100) * 0.35)

    # OOP: A static method belongs conceptually to this class but needs no
    # particular object (self) or class (cls) to do its job.
    @staticmethod
    def _validate_rating(value: int, label: str) -> None:
        if not 1 <= value <= 100:
            raise ValueError(f"{label.title()} must be from 1 to 100.")

    def degrade(self, amount: float) -> None:
        """Change durability while protecting its valid range."""

        if amount < 0:
            raise ValueError("Wear amount cannot be negative.")
        self._durability = max(0.0, self._durability - amount)

    def repair(self) -> None:
        self._durability = 100.0

    def restore_durability(self, value: float) -> None:
        """Controlled entry point used when reconstructing a saved object."""

        if not 0 <= value <= 100:
            raise SaveDataError("Saved part durability must be from 0 to 100.")
        self._durability = float(value)

    # OOP: Every subclass must supply its own version of this method.
    @abstractmethod
    def track_bonus(self, track: Track) -> float:
        """Return this part's contribution to a race score."""

    def describe(self) -> str:
        return (
            f"{self.category}: {self.name} | Performance {self.performance} | "
            f"Reliability {self.reliability} | Condition {self.durability:.0f}%"
        )

    def to_save_data(self) -> dict[str, object]:
        return {"code": self.code, "durability": round(self.durability, 2)}

    # OOP: Dunder methods let objects cooperate with built-in Python features.
    def __str__(self) -> str:
        return f"{self.name} ({self.category}, {self.durability:.0f}% condition)"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, name={self.name!r})"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CarPart):
            return NotImplemented
        return self.price < other.price


class Engine(CarPart):
    """A concrete CarPart that emphasizes speed and power."""

    category = "Engine"

    def __init__(
        self,
        code: str,
        name: str,
        price: int,
        performance: int,
        reliability: int,
        weight: int,
        horsepower: int,
        efficiency: int,
    ) -> None:
        # OOP: super() runs the parent portion of object initialization.
        super().__init__(code, name, price, performance, reliability, weight)
        self.horsepower = horsepower
        self.efficiency = efficiency

    # OOP: Method overriding gives Engine its own track_bonus behavior.
    def track_bonus(self, track: Track) -> float:
        raw_power = self.performance * 0.65 + self.horsepower * 0.08
        long_race_bonus = self.efficiency * track.length * 0.18
        return (raw_power + long_race_bonus) * self.condition_factor

    def describe(self) -> str:
        # super() can also reuse a normal parent method.
        return f"{super().describe()} | {self.horsepower} hp | Efficiency {self.efficiency}"


class Tires(CarPart):
    """A concrete CarPart whose behavior changes with the track surface."""

    category = "Tires"

    def __init__(
        self,
        code: str,
        name: str,
        price: int,
        performance: int,
        reliability: int,
        weight: int,
        grip: int,
        preferred_surface: Surface | None,
    ) -> None:
        super().__init__(code, name, price, performance, reliability, weight)
        self._validate_rating(grip, "grip")
        self.grip = grip
        self.preferred_surface = preferred_surface

    def track_bonus(self, track: Track) -> float:
        if self.preferred_surface is None:
            surface_multiplier = 1.0
        elif self.preferred_surface is track.surface:
            surface_multiplier = 1.22
        else:
            surface_multiplier = 0.78
        return (
            (self.performance * 0.3 + self.grip * 0.7)
            * surface_multiplier
            * self.condition_factor
        )

    def describe(self) -> str:
        specialty = self.preferred_surface or "All surfaces"
        return f"{super().describe()} | Grip {self.grip} | Best on {specialty}"


class Brakes(CarPart):
    """A concrete CarPart that becomes more important on difficult tracks."""

    category = "Brakes"

    def __init__(
        self,
        code: str,
        name: str,
        price: int,
        performance: int,
        reliability: int,
        weight: int,
        stopping_power: int,
    ) -> None:
        super().__init__(code, name, price, performance, reliability, weight)
        self._validate_rating(stopping_power, "stopping power")
        self.stopping_power = stopping_power

    def track_bonus(self, track: Track) -> float:
        technical_multiplier = 1 + track.difficulty * 0.025
        return (
            (self.performance * 0.35 + self.stopping_power * 0.65)
            * technical_multiplier
            * self.condition_factor
        )

    def describe(self) -> str:
        return f"{super().describe()} | Stopping power {self.stopping_power}"


# ---------------------------------------------------------------------------
# OOP: FACTORY PATTERN
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartBlueprint:
    code: str
    category: str
    name: str
    price: int
    summary: str


class PartFactory:
    """Centralizes the rules for constructing every available part."""

    _BLUEPRINTS: ClassVar[tuple[PartBlueprint, ...]] = (
        PartBlueprint("ECO-3", "Engine", "Eco I3", 500, "Reliable 140 hp starter engine"),
        PartBlueprint("V6-S", "Engine", "Sport V6", 900, "Balanced 260 hp engine"),
        PartBlueprint("TRB-X", "Engine", "Turbo X", 1_500, "Powerful but fragile 380 hp engine"),
        PartBlueprint("EV-P", "Engine", "Pulse EV", 1_800, "Efficient and reliable 340 hp motor"),
        PartBlueprint("STR-T", "Tires", "Street Tires", 350, "Reliable all-surface tires"),
        PartBlueprint("RAL-T", "Tires", "Rally Tires", 700, "High grip on dirt"),
        PartBlueprint("RAN-T", "Tires", "Rain Tires", 650, "High grip on wet tracks"),
        PartBlueprint("SLK-T", "Tires", "Racing Slicks", 1_100, "Extreme asphalt grip"),
        PartBlueprint("STD-B", "Brakes", "Standard Brakes", 300, "Simple and dependable brakes"),
        PartBlueprint("SPT-B", "Brakes", "Sport Brakes", 750, "Strong all-around braking"),
        PartBlueprint("CER-B", "Brakes", "Ceramic Brakes", 1_300, "Maximum stopping power"),
    )

    @classmethod
    def blueprints(cls) -> tuple[PartBlueprint, ...]:
        """Class method: work with the class-wide catalog, not one factory."""

        return cls._BLUEPRINTS

    @classmethod
    def create(cls, code: str) -> CarPart:
        """Build a fresh object from a short code."""

        builders = {
            "ECO-3": lambda: Engine("ECO-3", "Eco I3", 500, 48, 92, 130, 140, 9),
            "V6-S": lambda: Engine("V6-S", "Sport V6", 900, 68, 82, 165, 260, 7),
            "TRB-X": lambda: Engine("TRB-X", "Turbo X", 1_500, 88, 65, 175, 380, 5),
            "EV-P": lambda: Engine("EV-P", "Pulse EV", 1_800, 90, 89, 195, 340, 10),
            "STR-T": lambda: Tires("STR-T", "Street Tires", 350, 50, 90, 42, 55, None),
            "RAL-T": lambda: Tires("RAL-T", "Rally Tires", 700, 72, 78, 50, 80, Surface.DIRT),
            "RAN-T": lambda: Tires("RAN-T", "Rain Tires", 650, 68, 84, 47, 76, Surface.WET),
            "SLK-T": lambda: Tires("SLK-T", "Racing Slicks", 1_100, 92, 65, 45, 96, Surface.ASPHALT),
            "STD-B": lambda: Brakes("STD-B", "Standard Brakes", 300, 45, 92, 38, 50),
            "SPT-B": lambda: Brakes("SPT-B", "Sport Brakes", 750, 75, 82, 44, 80),
            "CER-B": lambda: Brakes("CER-B", "Ceramic Brakes", 1_300, 94, 75, 40, 98),
        }
        try:
            return builders[code.upper()]()
        except KeyError as exc:
            raise InvalidPartError(f"Unknown part code: {code}") from exc

    @classmethod
    def from_save_data(cls, data: dict[str, object]) -> CarPart:
        try:
            part = cls.create(str(data["code"]))
            part.restore_durability(float(data["durability"]))
            return part
        except (KeyError, TypeError, ValueError) as exc:
            raise SaveDataError("A saved car part is invalid.") from exc


# ---------------------------------------------------------------------------
# OOP: STRATEGY PATTERN AND POLYMORPHISM
# ---------------------------------------------------------------------------


class DrivingStyle(ABC):
    """Interchangeable algorithm used by a Car during a race."""

    name: ClassVar[str] = "Unknown"
    wear_multiplier: ClassVar[float] = 1.0

    @abstractmethod
    def adjust_score(
        self,
        base_score: float,
        reliability: float,
        rng: random.Random,
    ) -> float:
        """Modify a car's score according to this driving strategy."""

    def __str__(self) -> str:
        return self.name


class BalancedStyle(DrivingStyle):
    name = "Balanced"
    wear_multiplier = 1.0

    def adjust_score(
        self, base_score: float, reliability: float, rng: random.Random
    ) -> float:
        return base_score * rng.uniform(0.94, 1.06)


class AggressiveStyle(DrivingStyle):
    name = "Aggressive"
    wear_multiplier = 1.35

    def adjust_score(
        self, base_score: float, reliability: float, rng: random.Random
    ) -> float:
        mistake_chance = 0.08 + (100 - reliability) / 400
        if rng.random() < mistake_chance:
            return base_score * rng.uniform(0.68, 0.82)
        return base_score * rng.uniform(1.06, 1.15)


class CarefulStyle(DrivingStyle):
    name = "Careful"
    wear_multiplier = 0.65

    def adjust_score(
        self, base_score: float, reliability: float, rng: random.Random
    ) -> float:
        return base_score * rng.uniform(0.91, 0.97)


class StyleFactory:
    _STYLES: ClassVar[dict[str, type[DrivingStyle]]] = {
        "Balanced": BalancedStyle,
        "Aggressive": AggressiveStyle,
        "Careful": CarefulStyle,
    }

    @classmethod
    def names(cls) -> tuple[str, ...]:
        return tuple(cls._STYLES)

    @classmethod
    def create(cls, name: str) -> DrivingStyle:
        try:
            return cls._STYLES[name]()
        except KeyError as exc:
            raise SaveDataError(f"Unknown driving style: {name}") from exc


# ---------------------------------------------------------------------------
# OOP: A SECOND ABSTRACT BASE CLASS AND SUBTYPE POLYMORPHISM
# ---------------------------------------------------------------------------


class Vehicle(ABC):
    """Race only depends on this abstraction, not on a specific vehicle type."""

    def __init__(self, name: str) -> None:
        if not name.strip():
            raise ValueError("A vehicle must have a name.")
        self._name = name.strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def race_condition(self) -> float:
        """Return a general 0-100 condition value."""

    @abstractmethod
    def race_rating(self, track: Track, rng: random.Random) -> float:
        """Calculate performance on the supplied track."""

    @abstractmethod
    def take_wear(self, track: Track) -> None:
        """Apply the cost of completing a race."""

    def __str__(self) -> str:
        return self.name


class Car(Vehicle):
    """A customizable vehicle composed of parts and a driving style."""

    cars_created: ClassVar[int] = 0

    def __init__(
        self,
        nickname: str,
        engine: Engine,
        tires: Tires,
        brakes: Brakes,
        driving_style: DrivingStyle | None = None,
    ) -> None:
        self.validate_nickname(nickname)
        super().__init__(nickname)
        self._engine = engine
        self._tires = tires
        self._brakes = brakes
        self._driving_style = driving_style or BalancedStyle()
        Car.cars_created += 1

    @staticmethod
    def validate_nickname(nickname: str) -> None:
        if not 2 <= len(nickname.strip()) <= 20:
            raise ValueError("Car nickname must contain 2 to 20 characters.")

    # OOP: An alternative constructor creates a complete starter object.
    @classmethod
    def starter_car(cls, nickname: str) -> Car:
        engine = PartFactory.create("ECO-3")
        tires = PartFactory.create("STR-T")
        brakes = PartFactory.create("STD-B")
        if not isinstance(engine, Engine) or not isinstance(tires, Tires) or not isinstance(brakes, Brakes):
            raise InvalidPartError("The starter-car factory configuration is invalid.")
        return cls(
            nickname,
            engine=engine,
            tires=tires,
            brakes=brakes,
        )

    @property
    def nickname(self) -> str:
        return self.name

    @nickname.setter
    def nickname(self, value: str) -> None:
        self.validate_nickname(value)
        self._name = value.strip()

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def tires(self) -> Tires:
        return self._tires

    @property
    def brakes(self) -> Brakes:
        return self._brakes

    @property
    def driving_style(self) -> DrivingStyle:
        return self._driving_style

    @driving_style.setter
    def driving_style(self, value: DrivingStyle) -> None:
        if not isinstance(value, DrivingStyle):
            raise TypeError("driving_style must be a DrivingStyle object.")
        self._driving_style = value

    @property
    def parts(self) -> tuple[CarPart, ...]:
        return (self.engine, self.tires, self.brakes)

    @property
    def race_condition(self) -> float:
        return sum(part.durability for part in self.parts) / len(self)

    @property
    def reliability(self) -> float:
        return sum(
            part.reliability * part.condition_factor for part in self.parts
        ) / len(self)

    @property
    def repair_quote(self) -> int:
        return sum(part.repair_quote for part in self.parts)

    def install(self, new_part: CarPart) -> CarPart:
        """Install a compatible part and return the part that was removed."""

        if isinstance(new_part, Engine):
            old_part = self._engine
            self._engine = new_part
        elif isinstance(new_part, Tires):
            old_part = self._tires
            self._tires = new_part
        elif isinstance(new_part, Brakes):
            old_part = self._brakes
            self._brakes = new_part
        else:
            raise InvalidPartError(f"Cannot install {type(new_part).__name__}.")
        return old_part

    def stats(self) -> dict[str, float]:
        total_weight = sum(part.weight for part in self.parts)
        return {
            "Horsepower": float(self.engine.horsepower),
            "Top speed": 80 + self.engine.horsepower * 0.32 - total_weight * 0.02,
            "Acceleration": self.engine.performance * 0.75 + self.tires.grip * 0.25,
            "Handling": self.tires.grip * 0.65 + self.brakes.stopping_power * 0.35,
            "Reliability": self.reliability,
            "Condition": self.race_condition,
        }

    def race_rating(self, track: Track, rng: random.Random) -> float:
        # OOP: Polymorphism. Python chooses Engine.track_bonus,
        # Tires.track_bonus, or Brakes.track_bonus for each object.
        part_score = sum(part.track_bonus(track) for part in self.parts)
        weight_penalty = sum(part.weight for part in self.parts) * 0.04
        base_score = part_score - weight_penalty
        return self.driving_style.adjust_score(base_score, self.reliability, rng)

    def take_wear(self, track: Track) -> None:
        style_wear = self.driving_style.wear_multiplier
        self.engine.degrade(track.length * (0.35 + track.difficulty * 0.05) * style_wear)
        self.tires.degrade(track.length * (0.45 + track.difficulty * 0.06) * style_wear)
        self.brakes.degrade(track.length * (0.30 + track.difficulty * 0.08) * style_wear)

    def repair_all(self) -> None:
        for part in self.parts:
            part.repair()

    def to_save_data(self) -> dict[str, object]:
        return {
            "nickname": self.nickname,
            "engine": self.engine.to_save_data(),
            "tires": self.tires.to_save_data(),
            "brakes": self.brakes.to_save_data(),
            "driving_style": self.driving_style.name,
        }

    @classmethod
    def from_save_data(cls, data: dict[str, object]) -> Car:
        try:
            engine = PartFactory.from_save_data(data["engine"])  # type: ignore[arg-type]
            tires = PartFactory.from_save_data(data["tires"])    # type: ignore[arg-type]
            brakes = PartFactory.from_save_data(data["brakes"])  # type: ignore[arg-type]
            if not isinstance(engine, Engine):
                raise SaveDataError("Saved engine has the wrong part type.")
            if not isinstance(tires, Tires):
                raise SaveDataError("Saved tires have the wrong part type.")
            if not isinstance(brakes, Brakes):
                raise SaveDataError("Saved brakes have the wrong part type.")
            return cls(
                str(data["nickname"]),
                engine,
                tires,
                brakes,
                StyleFactory.create(str(data["driving_style"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SaveDataError("Saved car data is invalid.") from exc

    def __len__(self) -> int:
        """len(car) is the number of installed parts."""

        return len(self.parts)

    def __iter__(self) -> Iterator[CarPart]:
        """Allows: for part in car"""

        return iter(self.parts)

    def __str__(self) -> str:
        return f"{self.nickname} [{self.driving_style} style, {self.race_condition:.0f}% condition]"


class RivalCar(Vehicle):
    """A simpler Vehicle implementation used for computer-controlled racers."""

    def __init__(
        self,
        name: str,
        base_rating: float,
        preferred_surface: Surface,
    ) -> None:
        super().__init__(name)
        self.base_rating = base_rating
        self.preferred_surface = preferred_surface
        self._condition = 100.0

    @property
    def race_condition(self) -> float:
        return self._condition

    def race_rating(self, track: Track, rng: random.Random) -> float:
        surface_bonus = 1.08 if track.surface is self.preferred_surface else 0.96
        return self.base_rating * surface_bonus * (self._condition / 100) * rng.uniform(0.9, 1.1)

    def take_wear(self, track: Track) -> None:
        self._condition = max(40.0, self._condition - track.length * 0.6)


# ---------------------------------------------------------------------------
# OOP: AGGREGATION AND OBJECT COLLABORATION
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RaceResult:
    vehicle: Vehicle
    score: float

    @property
    def vehicle_name(self) -> str:
        return self.vehicle.name


class Race:
    """Temporarily groups Vehicle objects without owning their lifetimes."""

    def __init__(self, track: Track, entrants: list[Vehicle]) -> None:
        if len(entrants) < 2:
            raise ValueError("A race needs at least two entrants.")
        self.track = track
        self.entrants = entrants

    def run(self, rng: random.Random) -> list[RaceResult]:
        results: list[RaceResult] = []
        for vehicle in self.entrants:
            # OOP: Race does not care whether this is Car or RivalCar.
            # It calls the same interface and gets subtype-specific behavior.
            score = vehicle.race_rating(self.track, rng)
            vehicle.take_wear(self.track)
            results.append(RaceResult(vehicle, round(score, 2)))
        return sorted(results, key=lambda result: result.score, reverse=True)


class Garage:
    """Owns the player's active car and spare-part inventory."""

    inventory_capacity: ClassVar[int] = 12

    def __init__(self, active_car: Car, inventory: list[CarPart] | None = None) -> None:
        self.active_car = active_car
        self._inventory = list(inventory or [])
        if len(self._inventory) > self.inventory_capacity:
            raise GarageFullError("Saved inventory is larger than the garage.")

    def add_part(self, part: CarPart) -> None:
        if len(self) >= self.inventory_capacity:
            raise GarageFullError("Your spare-part inventory is full.")
        self._inventory.append(part)

    def install_from_inventory(self, index: int) -> tuple[CarPart, CarPart]:
        try:
            new_part = self._inventory.pop(index)
        except IndexError as exc:
            raise InvalidPartError("That inventory slot does not exist.") from exc
        old_part = self.active_car.install(new_part)
        self._inventory.append(old_part)
        return new_part, old_part

    def to_save_data(self) -> dict[str, object]:
        return {
            "active_car": self.active_car.to_save_data(),
            "inventory": [part.to_save_data() for part in self._inventory],
        }

    @classmethod
    def from_save_data(cls, data: dict[str, object]) -> Garage:
        try:
            car = Car.from_save_data(data["active_car"])  # type: ignore[arg-type]
            inventory = [
                PartFactory.from_save_data(item)
                for item in data["inventory"]  # type: ignore[union-attr]
            ]
            return cls(car, inventory)
        except (KeyError, TypeError) as exc:
            raise SaveDataError("Saved garage data is invalid.") from exc

    def __len__(self) -> int:
        return len(self._inventory)

    def __iter__(self) -> Iterator[CarPart]:
        return iter(self._inventory)


class Player:
    """Encapsulates the driver's money and garage."""

    starting_credits: ClassVar[int] = 2_000

    def __init__(self, name: str, credits: int, garage: Garage) -> None:
        if not name.strip():
            raise ValueError("Player name cannot be empty.")
        if credits < 0:
            raise ValueError("Credits cannot be negative.")
        self._name = name.strip()
        self._credits = credits
        self.garage = garage

    @property
    def name(self) -> str:
        return self._name

    @property
    def credits(self) -> int:
        return self._credits

    @classmethod
    def new_driver(cls, name: str, car_name: str = "Python Racer") -> Player:
        return cls(name, cls.starting_credits, Garage(Car.starter_car(car_name)))

    def spend(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot spend a negative amount.")
        if amount > self._credits:
            raise NotEnoughCreditsError(
                f"You need {amount:,} credits but only have {self._credits:,}."
            )
        self._credits -= amount

    def earn(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot earn a negative amount.")
        self._credits += amount

    def can_afford(self, item: Purchasable) -> bool:
        """Works with any object that satisfies the Purchasable protocol."""

        return self.credits >= item.price

    def buy(self, item: CarPart) -> None:
        """Buy a compatible part and move it into the garage."""

        if len(self.garage) >= self.garage.inventory_capacity:
            raise GarageFullError("Your spare-part inventory is full.")
        self.spend(item.price)
        try:
            self.garage.add_part(item)
        except GarageGameError:
            self.earn(item.price)
            raise

    def to_save_data(self) -> dict[str, object]:
        return {
            "version": 1,
            "name": self.name,
            "credits": self.credits,
            "garage": self.garage.to_save_data(),
        }

    @classmethod
    def from_save_data(cls, data: dict[str, object]) -> Player:
        try:
            if data["version"] != 1:
                raise SaveDataError("This save file uses an unsupported version.")
            return cls(
                str(data["name"]),
                int(data["credits"]),
                Garage.from_save_data(data["garage"]),  # type: ignore[arg-type]
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SaveDataError("Saved player data is invalid.") from exc

    def __str__(self) -> str:
        return f"{self.name} | {self.credits:,} credits | Car: {self.garage.active_car}"


# ---------------------------------------------------------------------------
# SERIALIZATION: TURN OBJECTS INTO JSON AND RECONSTRUCT THEM
# ---------------------------------------------------------------------------


class GameRepository:
    """Keeps file handling separate from game rules."""

    @staticmethod
    def save(player: Player, path: Path = SAVE_FILE) -> None:
        try:
            path.write_text(json.dumps(player.to_save_data(), indent=2), encoding="utf-8")
        except OSError as exc:
            raise SaveDataError(f"Could not save the game: {exc}") from exc

    @staticmethod
    def load(path: Path = SAVE_FILE) -> Player:
        try:
            raw_data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw_data, dict):
                raise SaveDataError("The save file must contain a JSON object.")
            return Player.from_save_data(raw_data)
        except (OSError, json.JSONDecodeError) as exc:
            raise SaveDataError(f"Could not load the game: {exc}") from exc


# ---------------------------------------------------------------------------
# THE TERMINAL USER INTERFACE
# ---------------------------------------------------------------------------

class Game:
    """Coordinates the menu while domain objects enforce the actual rules."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.player: Player | None = None

    @property
    def current_player(self) -> Player:
        if self.player is None:
            raise RuntimeError("The game has not started.")
        return self.player

    def start(self) -> None:
        self._heading("OOP GARAGE CHAMPIONSHIP")
        print("Build a car, manage your parts, and race while learning Python OOP.\n")
        self.player = self._load_or_create_player()

        actions = {
            "1": self.show_car,
            "2": self.visit_shop,
            "3": self.manage_inventory,
            "4": self.change_driving_style,
            "5": self.repair_car,
            "6": self.test_drive,
            "7": self.enter_race,
            "8": self.show_oop_guide,
            "9": self.save_game,
        }

        while True:
            self._heading("MAIN GARAGE")
            print(self.current_player)
            print(
                "\n1. Inspect car\n"
                "2. Buy parts\n"
                "3. Install a spare part\n"
                "4. Change driving style\n"
                "5. Repair car\n"
                "6. Test drive\n"
                "7. Enter a race\n"
                "8. Open OOP reference\n"
                "9. Save game\n"
                "0. Save and quit"
            )
            choice = input("\nChoose an action: ").strip()
            if choice == "0":
                self.save_game(pause=False)
                print("Thanks for racing. Your progress was saved.")
                return
            action = actions.get(choice)
            if action is None:
                print("Please enter a number from 0 to 9.")
                self._pause()
                continue
            try:
                action()
            except GarageGameError as exc:
                print(f"\nCould not complete that action: {exc}")
                self._pause()

    def _load_or_create_player(self) -> Player:
        if SAVE_FILE.exists() and self._yes_no("Load the existing save file?"):
            try:
                player = GameRepository.load()
                print(f"Welcome back, {player.name}!")
                return player
            except SaveDataError as exc:
                print(f"The save could not be loaded ({exc}). Starting fresh.")
        name = input("Driver name: ").strip() or "Driver"
        car_name = input("Name your first car (2-20 characters): ").strip()
        while True:
            try:
                return Player.new_driver(name, car_name or "Python Racer")
            except ValueError as exc:
                print(exc)
                car_name = input("Choose another car name: ").strip()

    def show_car(self) -> None:
        car = self.current_player.garage.active_car
        self._heading(f"{car.nickname.upper()} - CAR REPORT")
        for part in car:
            print(part.describe())
        print(f"\nDriving style: {car.driving_style}")
        print("\nEstimated stats:")
        for label, value in car.stats().items():
            suffix = " hp" if label == "Horsepower" else ""
            print(f"  {label:<12} {value:>6.1f}{suffix}")
        self._pause()

    def visit_shop(self) -> None:
        self._heading("PART SHOP")
        print(f"Credits: {self.current_player.credits:,}")
        print(f"Spare slots: {len(self.current_player.garage)}/{Garage.inventory_capacity}\n")
        for blueprint in PartFactory.blueprints():
            print(
                f"{blueprint.code:<6} | {blueprint.category:<6} | "
                f"{blueprint.name:<16} | {blueprint.price:>5,} cr | {blueprint.summary}"
            )
        code = input("\nEnter a part code to buy, or press Enter to leave: ").strip()
        if not code:
            return
        part = PartFactory.create(code)
        self.current_player.buy(part)
        print(f"Purchased {part.name}. It is now in your spare-part inventory.")
        self._pause()

    def manage_inventory(self) -> None:
        garage = self.current_player.garage
        self._heading("SPARE-PART INVENTORY")
        if len(garage) == 0:
            print("You do not own any spare parts. Visit the shop first.")
            self._pause()
            return
        for number, part in enumerate(garage, start=1):
            print(f"{number}. {part}")
        choice = self._number_input("\nInstall which part? (0 cancels): ", 0, len(garage))
        if choice == 0:
            return
        installed, removed = garage.install_from_inventory(choice - 1)
        print(f"Installed {installed.name}; {removed.name} moved to spare inventory.")
        self._pause()

    def change_driving_style(self) -> None:
        car = self.current_player.garage.active_car
        self._heading("DRIVING STYLE")
        descriptions = {
            "Balanced": "steady performance and normal wear",
            "Aggressive": "higher potential, more mistakes and wear",
            "Careful": "lower speed, much less wear",
        }
        for number, name in enumerate(StyleFactory.names(), start=1):
            marker = " (current)" if name == car.driving_style.name else ""
            print(f"{number}. {name}{marker}: {descriptions[name]}")
        choice = self._number_input("\nChoose a style: ", 1, len(StyleFactory.names()))
        car.driving_style = StyleFactory.create(StyleFactory.names()[choice - 1])
        print(f"Driving style changed to {car.driving_style}.")
        self._pause()

    def repair_car(self) -> None:
        car = self.current_player.garage.active_car
        self._heading("REPAIR BAY")
        quote = car.repair_quote
        if quote == 0:
            print("Every installed part is already at 100% condition.")
        elif self._yes_no(f"Repair all installed parts for {quote:,} credits?"):
            self.current_player.spend(quote)
            car.repair_all()
            print("Your car has been fully repaired.")
        self._pause()

    def test_drive(self) -> None:
        car = self.current_player.garage.active_car
        track = self._choose_track("TEST DRIVE")
        before = car.race_condition
        rating = car.race_rating(track, self.rng)
        car.take_wear(track)
        benchmark = 135 + track.difficulty * 4
        if rating >= benchmark * 1.12:
            report = "Outstanding setup. This car is ready to fight for first place."
        elif rating >= benchmark:
            report = "Competitive setup. A podium finish is realistic."
        else:
            report = "The car completed the run, but upgrades or another style may help."
        print(f"\nTest rating: {rating:.1f} (track benchmark: {benchmark:.1f})")
        print(report)
        print(f"Condition: {before:.1f}% -> {car.race_condition:.1f}%")
        self._pause()

    def enter_race(self) -> None:
        car = self.current_player.garage.active_car
        track = self._choose_track("RACE REGISTRATION")
        rivals = self._make_rivals(track)
        race = Race(track, [car, *rivals])
        results = race.run(self.rng)

        self._heading(f"{track.name.upper()} RESULTS")
        for place, result in enumerate(results, start=1):
            marker = " <- YOU" if result.vehicle is car else ""
            print(f"{place}. {result.vehicle_name:<18} {result.score:>7.2f}{marker}")

        player_place = next(
            place
            for place, result in enumerate(results, start=1)
            if result.vehicle is car
        )
        prize_factors = {1: 1.0, 2: 0.5, 3: 0.25}
        winnings = round(track.prize * prize_factors.get(player_place, 0))
        if winnings:
            self.current_player.earn(winnings)
            print(f"\nYou finished #{player_place} and earned {winnings:,} credits!")
        else:
            print(f"\nYou finished #{player_place}. Only the top three earn credits.")
        print(f"Car condition is now {car.race_condition:.1f}%.")
        self._pause()

    def _make_rivals(self, track: Track) -> list[RivalCar]:
        names = ("Byte Bandit", "Lambda Lightning", "Syntax Storm")
        surfaces = (Surface.ASPHALT, Surface.DIRT, Surface.WET)
        base = 132 + track.difficulty * 3.5
        return [
            RivalCar(name, base + index * 8 + self.rng.uniform(-4, 4), surfaces[index])
            for index, name in enumerate(names)
        ]

    def _choose_track(self, title: str) -> Track:
        self._heading(title)
        for number, track in enumerate(TRACKS, start=1):
            print(
                f"{number}. {track.name:<20} | {track.surface:<7} | "
                f"Difficulty {track.difficulty}/10 | Prize {track.prize:,} cr"
            )
        choice = self._number_input("\nChoose a track: ", 1, len(TRACKS))
        return TRACKS[choice - 1]

    def show_oop_guide(self) -> None:
        self._heading("OOP REFERENCE")
        print(textwrap.dedent(OOP_GUIDE).strip())
        self._pause()

    def save_game(self, pause: bool = True) -> None:
        GameRepository.save(self.current_player)
        print(f"Game saved to {SAVE_FILE}.")
        if pause:
            self._pause()

    @staticmethod
    def _heading(title: str) -> None:
        width = max(40, len(title) + 4)
        print(f"\n{'=' * width}\n{title.center(width)}\n{'=' * width}")

    @staticmethod
    def _pause() -> None:
        input("\nPress Enter to continue...")

    @staticmethod
    def _yes_no(prompt: str) -> bool:
        while True:
            answer = input(f"{prompt} [y/n]: ").strip().lower()
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            print("Please enter y or n.")

    @staticmethod
    def _number_input(prompt: str, minimum: int, maximum: int) -> int:
        while True:
            try:
                value = int(input(prompt))
                if minimum <= value <= maximum:
                    return value
            except ValueError:
                pass
            print(f"Please enter a whole number from {minimum} to {maximum}.")


# ---------------------------------------------------------------------------
# NON-INTERACTIVE LEARNING AND VERIFICATION MODES
# ---------------------------------------------------------------------------


def run_demo() -> None:
    """Run a predictable example without asking for terminal input."""

    rng = random.Random(7)
    player = Player.new_driver("Demo Driver", "Inheritance GT")
    print("Created:", player)

    sport_engine = PartFactory.create("V6-S")
    player.buy(sport_engine)
    installed, removed = player.garage.install_from_inventory(0)
    print(f"Composition: installed {installed.name}; stored {removed.name}.")

    car = player.garage.active_car
    car.driving_style = AggressiveStyle()
    track = TRACKS[0]
    entrants: list[Vehicle] = [
        car,
        RivalCar("Polymorphism AI", 145, Surface.ASPHALT),
        RivalCar("Abstract Racer", 150, Surface.DIRT),
    ]
    results = Race(track, entrants).run(rng)

    print(f"\nDemo race: {track.name}")
    for place, result in enumerate(results, start=1):
        print(f"{place}. {result.vehicle_name}: {result.score:.2f}")
    print(f"\nObjects created through CarPart hierarchy: {CarPart.total_parts_created}")
    print("Run with --concepts for the complete concept map.")


def run_self_test() -> None:
    """Small smoke test for construction, errors, races, and persistence."""

    player = Player.new_driver("Test Driver", "Unit Test GT")
    assert player.credits == Player.starting_credits
    assert len(player.garage.active_car) == 3

    first_engine = PartFactory.create("V6-S")
    second_engine = PartFactory.create("V6-S")
    assert first_engine is not second_engine
    first_engine.degrade(10)
    assert second_engine.durability == 100

    player.buy(first_engine)
    installed, removed = player.garage.install_from_inventory(0)
    assert installed is first_engine
    assert isinstance(removed, Engine)
    assert player.garage.active_car.engine is first_engine

    try:
        player.spend(99_999)
    except NotEnoughCreditsError:
        pass
    else:
        raise AssertionError("Overspending should raise NotEnoughCreditsError.")

    rng = random.Random(11)
    entrants: list[Vehicle] = [
        player.garage.active_car,
        RivalCar("Test Rival", 140, Surface.ASPHALT),
    ]
    results = Race(TRACKS[0], entrants).run(rng)
    assert len(results) == 2
    assert results[0].score >= results[1].score

    with tempfile.TemporaryDirectory() as temporary_directory:
        test_path = Path(temporary_directory) / "save.json"
        GameRepository.save(player, test_path)
        loaded = GameRepository.load(test_path)
        assert loaded.name == player.name
        assert loaded.credits == player.credits
        assert loaded.garage.active_car.engine.code == first_engine.code
        assert loaded.garage.active_car.engine.durability == first_engine.durability

    print("All OOP Garage self-tests passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Play OOP Garage Championship.")
    parser.add_argument("--concepts", action="store_true", help="print the OOP reference map")
    parser.add_argument("--demo", action="store_true", help="run a non-interactive example race")
    parser.add_argument("--self-test", action="store_true", help="run built-in smoke tests")
    args = parser.parse_args()

    if args.concepts:
        print(textwrap.dedent(OOP_GUIDE).strip())
    elif args.demo:
        run_demo()
    elif args.self_test:
        run_self_test()
    else:
        try:
            Game().start()
        except (EOFError, KeyboardInterrupt):
            print("\nGame closed. Use menu option 0 next time if you want to save first.")


if __name__ == "__main__":
    main()
