from functools import partial
from typing import Callable, Dict, List, Tuple, Union

from slm.defines import (
    AntennaReferencePoint,
    Aspiration,
    CollocationStatus,
    FractureSpacing,
    FrequencyStandardType,
    ISOCountry,
    TectonicPlates,
)
from slm.parsing.legacy.parser import (
    Error,
    ParsedSection,
    SiteLogParser,
    Warn,
    normalize,
)
import re
from slm.parsing import (
    to_int,
    to_enum,
    to_float,
    to_date,
    to_radome,
    to_antenna,
    to_receiver,
    to_datetime,
    to_satellites,
    to_str,
    BaseBinder
)

TEMP_RANGE_REGEX = re.compile(
    r'(\d+(?:[.]\d*)?)[\s()°degrsDEGRSCc]*(?:(?:-)|(?:to))\s*'
    r'(\d+(?:[.]\d*)?)[\s()°degrsDEGRSCc]*'
)
TEMP_STAB_REGEX = re.compile(
    r'(\d+(?:[.]\d*)?)?[\s()°degrsDEGRSCc]*(?:(?:±)|'
    r'(?:\+/?-))?\s*(\d+(?:[.]\d*)?)?[\s()°degrsDEGRSCc]*'
)

param_registry = {}


def reg(name, header_index, bindings):
    for binding in [bindings] if isinstance(bindings, tuple) else bindings:
        param_registry.setdefault(header_index, {})[binding[0]] = name
    return normalize(name)


class _Ignored:
    pass


def ignored(value):
    return _Ignored


def to_temp_stab(value):

    value = value.replace('º', '') if value else value

    def get_tuple():
        temp = None
        stab = None
        if value:
            range_mtch = TEMP_RANGE_REGEX.match(value)
            if range_mtch:
                v1 = float(range_mtch.group(1))
                v2 = float(range_mtch.group(2))
                return (v1 + v2) / 2, abs(v1 - v2) / 2

            stab_mtch = TEMP_STAB_REGEX.match(value)
            if stab_mtch:
                temp = (
                    float(stab_mtch.group(1))
                    if stab_mtch.group(1)
                    else None
                )
                stab = (
                    float(stab_mtch.group(2))
                    if stab_mtch.group(2)
                    else None
                )

        if stab is None and temp is not None and temp <= 10:
            stab = temp
            temp = None

        return temp, stab

    temp, stab = get_tuple()
    if value and temp is None and stab is None:
        raise ValueError(
            f'Unable to parse "{value}" into a temperature stabilization. '
            f'format: deg C +/- deg C'
        )
    return temp, stab


def effective_start(value):
    try:
        if value.strip():
            return to_date(value.split('/')[0])
        return None
    except ValueError as ve:
        raise ValueError(
            f'Unable to parse {value} into an expected start date. Expected '
            f'format: CCYY-MM-DD/CCYY-MM-DD'
        ) from ve


def effective_end(value):
    try:
        if value.strip():
            splt = value.split('/')
            if len(splt) > 1:
                return to_date(value.split('/')[1])
        return None
    except ValueError as ve:
        raise ValueError(
            f'Unable to parse {value} into an expected end date. Expected '
            f'format: CCYY-MM-DD/CCYY-MM-DD'
        ) from ve


class SiteLogBinder(BaseBinder):

    EFFECTIVE_DATES = [
        ('Effective Dates', [
            ('effective_start', effective_start),
            ('effective_end', effective_end)
        ]),
    ]

    METEROLOGICAL_TRANSLATION = [
        ('Manufacturer', ('manufacturer', to_str)),
        ('Serial Number', ('serial_number', to_str)),
        ('Height Diff to Ant', ('height_diff', to_float)),
        ('Calibration date', ('calibration', to_date)),
        *EFFECTIVE_DATES,
        ('Notes', ('notes', to_str))
    ]

    ONGOING_CONDITIONS = [
        *EFFECTIVE_DATES,
        ('Additional Information', ('additional_information', to_str))
    ]

    AGENCY_POC = [
        ('Agency', ('agency', to_str)),
        ('Preferred Abbreviation', ('preferred_abbreviation', to_str)),
        ('Mailing Address', ('mailing_address', to_str)),
        ('Primary Contact::Contact Name', ('primary_name', to_str)),
        ('Primary Contact::Telephone (primary)', ('primary_phone1', to_str)),
        ('Primary Contact::Telephone (secondary)',
            ('primary_phone2', to_str)),
        ('Primary Contact::Fax', ('primary_fax', to_str)),
        ('Primary Contact::E-mail', ('primary_email', to_str)),
        ('Secondary Contact::Contact Name', ('secondary_name', to_str)),
        ('Secondary Contact::Telephone (primary)',
            ('secondary_phone1', to_str)),
        ('Secondary Contact::Telephone (secondary)',
            ('secondary_phone2', to_str)),
        ('Secondary Contact::Fax', ('secondary_fax', to_str)),
        ('Secondary Contact::E-mail', ('secondary_email', to_str)),
        ('Additional Information', ('additional_information', to_str))
    ]

    # the translation table maps binding functions and names to normalized
    # parameter names. Multiple normalized parameter names can be bound to the
    # same binding name and are to allow slight permissible variations in
    # site log parameter names. In all cases - the "canonical" name for each
    # parameter should be listed *last* in the list.

    TRANSLATION_TABLE: Dict[
        Union[int, Tuple[int, int]],
        Dict[
            str,
            Union[
                Tuple[str, Callable],
                List[Tuple[str, Callable]]
            ]
        ]
    ] = {
        0: {
            reg(log_name, 0, bindings): bindings for log_name, bindings in [
                ('Prepared by (full name)', ('prepared_by', to_str)),
                ('Date Prepared', ('date_prepared', to_date)),
                ('Report Type', ('report_type', to_str)),
                ('Previous Site Log', ('previous_log', to_str)),
                ('Modified/Added Sections', ('modified_section', to_str))
            ]
        },
        1: {
            reg(log_name, 1, bindings): bindings for log_name, bindings in [
                ('Site Name', ('site_name', to_str)),
                ('Four Character ID', ('four_character_id', ignored)),
                ('Monument Inscription', ('monument_inscription', to_str)),
                ('IERS DOMES Number', ('iers_domes_number', to_str)),
                ('CDP Number', ('cdp_number', to_str)),
                ('Date Installed', ('date_installed', to_datetime)),
                ('Monument Description', ('monument_description', to_str)),
                ('Height of the Monument', ('monument_height', to_float)),
                ('Height of the Monument (m)', ('monument_height', to_float)),
                ('Monument Foundation', ('monument_foundation', to_str)),
                ('Foundation Depth', ('foundation_depth', to_float)),
                ('Foundation Depth (m)', ('foundation_depth', to_float)),
                ('Marker Description', ('marker_description', to_str)),
                ('Geologic Characteristic', ('geologic_characteristic', to_str)),
                ('Bedrock Type', ('bedrock_type', to_str)),
                ('Bedrock Condition', ('bedrock_condition', to_str)),
                ('Fracture Spacing',
                    ('fracture_spacing', partial(to_enum, FractureSpacing))),
                ('Fault Zones Nearby', ('fault_zones', to_str)),
                ('Distance/activity', ('distance', to_str)),
                ('Additional Information', ('additional_information', to_str))
            ]
        },
        2: {
            reg(log_name, 2, bindings): bindings for log_name, bindings in [
                ('City or Town', ('city', to_str)),
                ('State or Province', ('state', to_str)),
                ('Country', ('country', partial(to_enum, ISOCountry))),
                ('Tectonic Plate',
                    ('tectonic', partial(to_enum, TectonicPlates))),

                ('X coordinate', ('x', to_float)),
                ('Y coordinate', ('y', to_float)),
                ('Z coordinate', ('z', to_float)),
                ('Latitude', ('latitude', to_float)),
                ('Longitude', ('longitude', to_float)),
                ('Elevation', ('elevation', to_float)),

                ('X coordinate (m)', ('x', to_float)),
                ('Y coordinate (m)', ('y', to_float)),
                ('Z coordinate (m)', ('z', to_float)),
                ('Latitude (N is +)', ('latitude', to_float)),
                ('Longitude (E is +)', ('longitude', to_float)),
                ('Elevation (m,ellips.)', ('elevation', to_float)),
    
                ('Additional Information', ('additional_information', to_str))
            ]
        },
        3: {
            reg(log_name, 3, bindings): bindings for log_name, bindings in [
                ('Receiver Type', ('receiver_type', to_receiver)),
                ('Satellite System', ('satellite_system', to_satellites)),
                ('Serial Number', ('serial_number', to_str)),
                ('Firmware Version', ('firmware', to_str)),
                ('Elevation Cutoff Setting', ('elevation_cutoff', to_float)),
                ('Date Installed', ('installed', to_datetime)),
                ('Date Removed', ('removed', to_datetime)),
                ('Temperature Stabiliz.', [
                    ('temp', lambda val: to_temp_stab(val)[0]),
                    ('temp_stab', lambda val: to_temp_stab(val)[1])
                ]),
                ('Additional Information', ('additional_info', to_str))
            ]
        },
        4: {
            reg(log_name, 4, bindings): bindings for log_name, bindings in [
                ('Antenna Type', ('antenna_type', to_antenna)),
                ('Serial Number', ('serial_number', to_str)),
                ('Antenna Reference Point',
                    ('reference_point', partial(to_enum, AntennaReferencePoint))),

                ('Marker->ARP Up Ecc.', ('marker_up', to_float)),
                ('Marker->ARP North Ecc', ('marker_north', to_float)),
                ('Marker->ARP East Ecc', ('marker_east', to_float)),

                ('Marker->ARP Up Ecc. (m)', ('marker_up', to_float)),
                ('Marker->ARP North Ecc(m)', ('marker_north', to_float)),
                ('Marker->ARP East Ecc(m)', ('marker_east', to_float)),

                ('Alignment from True N', ('alignment', to_float)),
                ('Antenna Radome Type', ('radome_type', to_radome)),
                ('Radome Serial Number', ('radome_serial_number', to_str)),
                ('Antenna Cable Type', ('cable_type', to_str)),
                ('Antenna Cable Length', ('cable_length', to_float)),
                ('Date Installed', ('installed', to_datetime)),
                ('Date Removed', ('removed', to_datetime)),
                ('Additional Information', ('additional_information', to_str))
            ]
        },
        5: {
            reg(log_name, 5, bindings): bindings for log_name, bindings in [
                ('Tied Marker Name', ('name', to_str)),
                ('Tied Marker Usage', ('usage', to_str)),
                ('Tied Marker CDP Number', ('cdp_number', to_str)),
                ('Tied Marker DOMES Number', ('domes_number', to_str)),

                ('dx', ('dx', to_float)),
                ('dy', ('dy', to_float)),
                ('dz', ('dz', to_float)),

                ('dx (m)', ('dx', to_float)),
                ('dy (m)', ('dy', to_float)),
                ('dz (m)', ('dz', to_float)),

                ('Accuracy', ('accuracy', to_float)),

                ('Accuracy (mm)', ('accuracy', to_float)),

                ('Survey method', ('survey_method', to_str)),
                ('Date Measured', ('measured', to_datetime)),
                ('Additional Information', ('additional_information', to_str))
            ]
        },
        6: {
            reg(log_name, 6, bindings): bindings for log_name, bindings in [
                ('Standard Type',
                    ('standard_type', 
                     partial(to_enum, FrequencyStandardType))
                 ),
                ('Input Frequency', ('input_frequency', to_float)),
                *EFFECTIVE_DATES,
                ('Notes', ('notes', to_str))
            ]
        },
        7: {
            reg(log_name, 7, bindings): bindings for log_name, bindings in [
                ('Instrumentation Type', ('instrument_type', to_str)),
                ('Status', ('status', partial(to_enum, CollocationStatus))),
                *EFFECTIVE_DATES,
                ('Notes', ('notes', to_str))
            ]
        },
        (8, 1): {
            reg(log_name, (8, 1), bindings): bindings for log_name, bindings in
            [

                ('Accuracy', ('accuracy', to_float)),
                
                ('Humidity Sensor Model', ('model', to_str)),
                ('Data Sampling Interval', ('sampling_interval', to_int)),
                ('Accuracy (% rel h)', ('accuracy', to_float)),
                ('Aspiration', ('aspiration', partial(to_enum, Aspiration))),
                *METEROLOGICAL_TRANSLATION
            ]
        },
        (8, 2): {
            reg(log_name, (8, 2), bindings): bindings for log_name, bindings in
            [
                ('Pressure Sensor Model', ('model', to_str)),
                ('Data Sampling Interval', ('sampling_interval', to_int)),
                ('Accuracy', ('accuracy', to_float)),
                *METEROLOGICAL_TRANSLATION
             ]
        },
        (8, 3): {
            reg(log_name, (8, 3), bindings): bindings for log_name, bindings in
            [
                ('Temp. Sensor Model', ('model', to_str)),
                ('Data Sampling Interval', ('sampling_interval', to_int)),
                ('Accuracy', ('accuracy', to_float)),
                ('Aspiration', ('aspiration', partial(to_enum, Aspiration))),
                *METEROLOGICAL_TRANSLATION
            ]
        },
        (8, 4): {
            reg(log_name, (8, 4), bindings): bindings for log_name, bindings in
            [
                ('Water Vapor Radiometer', ('model', to_str)),
                ('Distance to Antenna', ('distance_to_antenna', to_float)),
                *METEROLOGICAL_TRANSLATION
            ]
        },
        (8, 5): {
            reg(log_name, (8, 5), bindings): bindings for log_name, bindings in
            [
                ('Other Instrumentation', ('instrumentation', to_str))
            ]
        },
        (9, 1): {
            reg(log_name, (9, 1), bindings): bindings for log_name, bindings in
            [
                *ONGOING_CONDITIONS,
                ('Radio Interferences', ('interferences', to_str)),
                ('Observed Degradations', ('degradations', to_str)),
            ]
        },
        (9, 2): {
            reg(log_name, (9, 2), bindings): bindings for log_name, bindings in
            [
                *ONGOING_CONDITIONS,
                ('Multipath Sources', ('sources', to_str))
            ]
        },
        (9, 3): {
            reg(log_name, (9, 3), bindings): bindings for log_name, bindings in
            [
                *ONGOING_CONDITIONS,
                ('Signal Obstructions', ('obstructions', to_str))
            ]
        },
        10: {
            reg(log_name, 10, bindings): bindings for log_name, bindings in [
                ('Date', EFFECTIVE_DATES[0][1]),
                ('Event', ('event', to_str))
            ]
        },
        11: {
            reg(log_name, 11, bindings): bindings for log_name, bindings in
            AGENCY_POC
        },
        12: {
            reg(log_name, 12, bindings): bindings for log_name, bindings in
            AGENCY_POC
        },
        13: {
            reg(log_name, 13, bindings): bindings for log_name, bindings in [
                ('Primary Data Center', ('primary', to_str)),
                ('Secondary Data Center', ('secondary', to_str)),
                ('URL for More Information', ('more_info', to_str)),
                ('Site Map', ('sitemap', to_str)),
                ('Site Diagram', ('site_diagram', to_str)),
                ('Horizon Mask', ('horizon_mask', to_str)),
                ('Monument Description', ('monument_description', to_str)),
                ('Site Pictures', ('site_picture', to_str)),
                ('Additional Information', ('additional_information', to_str))
            ]
        }
    }

    def __init__(self, parsed: SiteLogParser):
        super().__init__(parsed)
        for _, section in self.parsed.sections.items():
            if section.example or not section.contains_values:
                continue
            if section.heading_index not in self.TRANSLATION_TABLE:
                for line_no in range(section.line_no, section.line_end):
                    self.parsed.add_finding(
                        Warn(
                            section.line_no,
                            self.parsed,
                            f'Unexpected section {section.index_string}',
                            section=section
                        )
                    )
            else:
                self.bind_section(
                    section=section,
                    translations=self.TRANSLATION_TABLE[
                        section.heading_index
                    ]
                )

    def bind_section(
            self,
            section: ParsedSection,
            translations: Dict[
                str,
                Union[
                    Tuple[str, Callable],
                    List[Tuple[str, Callable]]
                ]
            ]
    ) -> None:

        expected = set()
        binding_errors = set()
        for _, bindings in translations.items():
            for param, _ in (
                bindings if isinstance(bindings, list)
                else [bindings]
            ):
                expected.add(param)

        for norm_name, parameter in section.parameters.items():
            translation = translations.get(norm_name, None)
            while not translation and '::' in norm_name:
                norm_name = [
                    part for part in norm_name.split('::')
                    if part.strip()
                ][0]
                translation = translations.get(norm_name, None)

            if not translation:
                self.parsed.add_finding(
                    Warn(
                        parameter.line_no,
                        self.parsed,
                        f'Unrecognized parameter: {parameter.name}',
                        section=section
                    )
                )
                continue

            for param, parse in (
                translation if isinstance(translation, list)
                else [translation]
            ):
                try:
                    parameter.bind(
                        param,
                        parse('') if parameter.is_placeholder else
                        parse(parameter.value)
                    )
                except Exception as err:
                    binding_errors.add(param)
                    for line_no in range(
                        parameter.line_no,
                        parameter.line_end+1
                    ):
                        self.parsed.add_finding(
                            Error(
                                line_no,
                                self.parsed,
                                str(err),
                                section=section
                            )
                        )

        # if any binding parameters were not found attach a listing
        # of them as an error to the relevant header line
        missing = [
            param for param in expected
            if not section.get_param(param) and param not in binding_errors
        ]
        if missing and not self.parsed.findings.get(section.line_no):
            missing = '\n'.join({
                param_registry[section.heading_index][missing]
                for missing in missing
            })
            self.parsed.add_finding(
                Error(
                    section.line_no,
                    self.parsed,
                    f'Missing parameters:\n{missing}',
                    section=section
                )
            )
