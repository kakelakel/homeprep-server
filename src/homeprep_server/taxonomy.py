"""Canonical HomePrep inventory taxonomy mirrored from the HA standalone integration.

Field values must stay in lock-step with ``custom_components.homeprep.core.taxonomy``.
The Server exposes this metadata so Web and future Android clients do not invent a
parallel set of categories, item types, units or form behaviour.
"""

CATEGORIES = {
    "food": "Food",
    "water": "Water",
    "medicine": "Medicine",
    "first_aid": "First aid",
    "hygiene": "Hygiene",
    "lighting": "Lighting",
    "power": "Power",
    "communication": "Communication",
    "fire_safety": "Fire safety",
    "tools": "Tools",
    "shelter_warmth": "Shelter & warmth",
    "cooking": "Cooking",
    "documents": "Documents",
    "cash": "Cash",
    "pet_supplies": "Pet supplies",
    "other": "Other",
}

ITEM_TYPES = {"consumable": "Consumable", "equipment": "Equipment"}

CATEGORY_META = {
    "food": {
        "group": "Essentials",
        "icon": "mdi:food",
        "form_profile": "expiry",
        "default_unit": "piece",
        "preferred_units": [
            "piece", "pack", "can", "jar", "bag", "portion", "meal", "serving",
            "gram", "kilogram",
        ],
    },
    "water": {
        "group": "Essentials",
        "icon": "mdi:water",
        "form_profile": "expiry",
        "default_unit": "liter",
        "preferred_units": [
            "liter", "milliliter", "canister", "bottle", "gallon_us", "gallon_imperial",
        ],
    },
    "medicine": {
        "group": "Health",
        "icon": "mdi:pill",
        "form_profile": "expiry",
        "default_unit": "tablet",
        "preferred_units": [
            "tablet", "blister_pack", "capsule", "dose", "bottle", "milliliter",
            "ampoule", "vial",
        ],
    },
    "first_aid": {
        "group": "Health",
        "icon": "mdi:medical-bag",
        "form_profile": "balanced",
        "default_unit": "piece",
        "preferred_units": ["piece", "pack", "box", "roll", "sheet", "bottle", "tube"],
    },
    "hygiene": {
        "group": "Health",
        "icon": "mdi:shower",
        "form_profile": "expiry",
        "default_unit": "piece",
        "preferred_units": ["piece", "pack", "roll", "bottle", "tube", "milliliter", "liter"],
    },
    "lighting": {
        "group": "Utilities",
        "icon": "mdi:lightbulb",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": ["piece", "pack", "set"],
    },
    "power": {
        "group": "Utilities",
        "icon": "mdi:battery-charging",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": ["piece", "pack", "set", "watt_hour", "kilowatt_hour"],
    },
    "communication": {
        "group": "Utilities",
        "icon": "mdi:radio",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": ["piece", "set", "pack"],
    },
    "fire_safety": {
        "group": "Safety",
        "icon": "mdi:fire-extinguisher",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": ["piece", "set", "pack", "kilogram", "liter"],
    },
    "tools": {
        "group": "Household",
        "icon": "mdi:tools",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": ["piece", "set", "pair", "pack"],
    },
    "shelter_warmth": {
        "group": "Essentials",
        "icon": "mdi:home-thermometer",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": [
            "piece", "set", "pair", "pack", "meter", "square_meter", "foot", "square_foot",
        ],
    },
    "cooking": {
        "group": "Essentials",
        "icon": "mdi:pot-steam",
        "form_profile": "balanced",
        "default_unit": "piece",
        "preferred_units": ["piece", "set", "pack", "bottle", "canister", "liter", "kilogram"],
    },
    "documents": {
        "group": "Administration",
        "icon": "mdi:file-document",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": ["piece", "set", "sheet"],
    },
    "cash": {
        "group": "Administration",
        "icon": "mdi:cash",
        "form_profile": "inspection",
        "default_unit": "piece",
        "preferred_units": ["piece"],
    },
    "pet_supplies": {
        "group": "Household",
        "icon": "mdi:paw",
        "form_profile": "balanced",
        "default_unit": "piece",
        "preferred_units": ["piece", "pack", "bag", "can", "bottle", "liter", "kilogram"],
    },
    "other": {
        "group": "Other",
        "icon": "mdi:package-variant",
        "form_profile": "balanced",
        "default_unit": "piece",
        "preferred_units": ["piece", "pack", "set"],
    },
}


def _unit(label: str, symbol: str | None, group: str, system: str) -> dict[str, str | None]:
    return {"label": label, "symbol": symbol, "group": group, "system": system}


UNITS = {
    "piece": _unit("Piece", "pcs", "Count", "neutral"),
    "pair": _unit("Pair", None, "Count", "neutral"),
    "set": _unit("Set", None, "Count", "neutral"),
    "dozen": _unit("Dozen", "doz", "Count", "neutral"),
    "pack": _unit("Pack", None, "Packaging", "neutral"),
    "box": _unit("Box", None, "Packaging", "neutral"),
    "carton": _unit("Carton", None, "Packaging", "neutral"),
    "crate": _unit("Crate", None, "Packaging", "neutral"),
    "bag": _unit("Bag", None, "Packaging", "neutral"),
    "sachet": _unit("Sachet", None, "Packaging", "neutral"),
    "bottle": _unit("Bottle", None, "Packaging", "neutral"),
    "can": _unit("Can", None, "Packaging", "neutral"),
    "jar": _unit("Jar", None, "Packaging", "neutral"),
    "tube": _unit("Tube", None, "Packaging", "neutral"),
    "roll": _unit("Roll", None, "Packaging", "neutral"),
    "sheet": _unit("Sheet", None, "Packaging", "neutral"),
    "bucket": _unit("Bucket", None, "Packaging", "neutral"),
    "canister": _unit("Canister", None, "Packaging", "neutral"),
    "blister_pack": _unit("Blister pack", None, "Medicine", "neutral"),
    "tablet": _unit("Tablet", None, "Medicine", "neutral"),
    "capsule": _unit("Capsule", None, "Medicine", "neutral"),
    "dose": _unit("Dose", None, "Medicine", "neutral"),
    "ampoule": _unit("Ampoule", None, "Medicine", "neutral"),
    "vial": _unit("Vial", None, "Medicine", "neutral"),
    "portion": _unit("Portion", None, "Food", "neutral"),
    "meal": _unit("Meal", None, "Food", "neutral"),
    "serving": _unit("Serving", None, "Food", "neutral"),
    "milliliter": _unit("Milliliter", "ml", "Volume", "metric"),
    "centiliter": _unit("Centiliter", "cl", "Volume", "metric"),
    "deciliter": _unit("Deciliter", "dl", "Volume", "metric"),
    "liter": _unit("Liter", "L", "Volume", "metric"),
    "cubic_meter": _unit("Cubic meter", "m³", "Volume", "metric"),
    "fluid_ounce_us": _unit("US fluid ounce", "fl oz", "Volume", "us_customary"),
    "cup_us": _unit("US cup", "cup", "Volume", "us_customary"),
    "pint_us": _unit("US pint", "pt", "Volume", "us_customary"),
    "quart_us": _unit("US quart", "qt", "Volume", "us_customary"),
    "gallon_us": _unit("US gallon", "gal", "Volume", "us_customary"),
    "fluid_ounce_imperial": _unit("Imperial fluid ounce", "fl oz", "Volume", "imperial"),
    "pint_imperial": _unit("Imperial pint", "pt", "Volume", "imperial"),
    "quart_imperial": _unit("Imperial quart", "qt", "Volume", "imperial"),
    "gallon_imperial": _unit("Imperial gallon", "gal", "Volume", "imperial"),
    "milligram": _unit("Milligram", "mg", "Mass", "metric"),
    "gram": _unit("Gram", "g", "Mass", "metric"),
    "kilogram": _unit("Kilogram", "kg", "Mass", "metric"),
    "ounce": _unit("Ounce", "oz", "Mass", "customary"),
    "pound": _unit("Pound", "lb", "Mass", "customary"),
    "stone": _unit("Stone", "st", "Mass", "imperial"),
    "millimeter": _unit("Millimeter", "mm", "Length", "metric"),
    "centimeter": _unit("Centimeter", "cm", "Length", "metric"),
    "meter": _unit("Meter", "m", "Length", "metric"),
    "kilometer": _unit("Kilometer", "km", "Length", "metric"),
    "inch": _unit("Inch", "in", "Length", "customary"),
    "foot": _unit("Foot", "ft", "Length", "customary"),
    "yard": _unit("Yard", "yd", "Length", "customary"),
    "mile": _unit("Mile", "mi", "Length", "customary"),
    "square_meter": _unit("Square meter", "m²", "Area", "metric"),
    "square_inch": _unit("Square inch", "in²", "Area", "customary"),
    "square_foot": _unit("Square foot", "ft²", "Area", "customary"),
    "square_yard": _unit("Square yard", "yd²", "Area", "customary"),
    "cubic_inch": _unit("Cubic inch", "in³", "Volume", "customary"),
    "cubic_foot": _unit("Cubic foot", "ft³", "Volume", "customary"),
    "watt_hour": _unit("Watt-hour", "Wh", "Energy", "neutral"),
    "kilowatt_hour": _unit("Kilowatt-hour", "kWh", "Energy", "neutral"),
    "other": _unit("Other", None, "Other", "neutral"),
}


def inventory_taxonomy() -> dict[str, object]:
    return {
        "categories": CATEGORIES,
        "category_meta": CATEGORY_META,
        "item_types": ITEM_TYPES,
        "units": UNITS,
    }
