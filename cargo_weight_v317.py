"""Cargo weight display: confirmed game-file mass or MapRunner packed cargo mass.

MapRunner lists separate *loose* and *packed* masses.  The below hand-checked
lookup is for **PACKED** cargo only, as of 2026-11-20.  These are independent
community-reference values; they have NOT been imported from the user's
installed game or validated against a particular game build/mod setup.

Never derive mass from cargo slot counts.  Omit cargo with ambiguous/missing
community values.  A tuple denotes an attested range, never an invented mean.
"""
from __future__ import annotations
import math

MAPRUNNER_SOURCE_URL = 'https://www.maprunner.info/cargo'
MAPRUNNER_CHECKED_DATE = '2026-11-20'

# kg when packed; ranges also in kg. Names are internal catalog cargo IDs.
# The site reports no packed weight for repair parts and water, and does not
# identify our catalog's variant wood plank and special spare parts IDs.
MAPRUNNER_PACKED_MASS_KG = {
    'ba_20_armored_car': 3000,
    'bricks': 1000,
    'burnt_logs': (4000, 8250),
    'cabin': 3000,
    'cable_car': 4500,
    'cable_drum': 2500,
    'cargo_container': 3000,
    'cellulose': 1500,
    'cement': 2500,
    'chemical_barrels': 2500,
    'cistern': 1000,
    'concrete_blocks': 3000,
    'concrete_slab': 6000,
    'consumables': 2500,
    'data_buoy': 2341,
    'drilling_equipment': 10000,
    'drilling_spare_parts': 1000,
    'empty_container': 3000,
    'engine_assembly': 2500,
    'extended_crew_cabin': 10000,
    'fertilizer': 1500,
    'filled_container': 3000,
    'freezer': 3000,
    'fuel': 1500,
    'garbage': 3000,
    'gold': 3120,
    'hay_bale': 1500,
    'industrial_boiler': 10000,
    'industrial_chiller': 5000,
    'large_pipe': 8000,
    'long_logs': 12000,
    'long_planks': 2000,
    'medium_logs': (5000, 8300),
    'medium_pipes': 4500,
    'medium_planks': 1000,
    'metal_beams': 5000,
    'metal_rolls': 1000,
    'mine_cart': 4500,
    'multistage_pump': 5750,
    'oil_barrels': 1500,
    'oil_rig_drill': 10000,
    'oversized_cargo': 10000,
    'packaged_sand': 2500,
    'part_of_the_airplane_fuselage': 10000,
    'piece_of_the_airplane_wing': 2000,
    'potato_samples': 2500,
    'potatoes': 2500,
    'rail_section': 1000,
    'rails': 10000,
    'rescue_shelter': 2000,
    'secure_container': 1000,
    'sequoia': 1000,
    'service_spare_parts': 1200,
    'short_logs': (4000, 4050),
    'silver': 3120,
    'slate_blocks': 7000,
    'small_pipes': 3500,
    'solar_panels': 2500,
    'soybeans': 2500,
    'special_cargo': 3000,
    'stage_2_fuel_tank': 1500,
    'stage_3_fuel_tank': 2100,
    'tetrapod': 1500,
    'transformer': 2200,
    'vehicle_spare_parts': 1200,
    'water_pipe': 6000,
    'wing_fragments_with_the_engine': 2000,
    'wooden_planks': 500,
}

VERIFIED_MASS_SOURCES = frozenset({'local_game_data', 'official_game_files'})


def verified_mass_t(entry):
    """Only return a single game-file-provenanced tonnage, never estimates."""
    if not isinstance(entry, dict):
        return None
    if entry.get('mass_source') not in VERIFIED_MASS_SOURCES:
        return None
    value = entry.get('mass_t')
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def _format_t(value, lang='ru', decimals=3):
    number = f'{value:.{decimals}f}'.rstrip('0').rstrip('.')
    return (number.replace('.', ',') + ' т') if lang == 'ru' else number + ' t'


def cargo_weight_source(entry):
    """State exact data provenance without conflating MapRunner with game files."""
    if verified_mass_t(entry) is not None:
        return 'game_files'
    if isinstance(entry, dict) and entry.get('id') in MAPRUNNER_PACKED_MASS_KG:
        return 'maprunner_packed'
    return None


def cargo_weight_label(entry, lang='ru'):
    """Mass label for catalog rows/details. Return 'No data' if truly unknown."""
    actual = verified_mass_t(entry)
    if actual is not None:
        return _format_t(actual,lang,decimals=2)
    if isinstance(entry, dict):
        reference = MAPRUNNER_PACKED_MASS_KG.get(entry.get('id'))
        if isinstance(reference, int):
            if reference > 0:
                return _format_t(reference / 1000,lang)
        elif (isinstance(reference, tuple) and len(reference)==2 and
              all(isinstance(x,int) and x>0 for x in reference) and
              reference[0] < reference[1]):
            # Ranges for logs: do not substitute a fake single weight.
            a,b=reference
            first=_format_t(a/1000,lang).split()[0]
            second=_format_t(b/1000,lang)
            return first + '–' + second
    return 'Нет данных' if lang == 'ru' else 'No data'
