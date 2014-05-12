# -*- coding: utf-8 -*-

import csvvalidator as cv
import datetime, time
import re
import json
import base64

def resourceToCSVValidator(resource, deep=True):
    """
    Takes a valid resource metadata object and returns an appropriate CSVValidator.
    """
    
    # A shortcut to the metadata's `fields` attribute.
    fields = resource["schema"]["fields"]

    # Set up the basic validator.
    # The validator will reject any CSV that doesn't have the expected fields.
    validator = cv.CSVValidator([f["name"] for f in fields])
    validator.add_header_check()

    # Add value checks for each field.
    # Only if this is a "deep" check.
    if deep:
        for f in fields:
            validator.add_value_check(f["name"], fieldValidator(f))

    return validator

def fieldValidator(field):
    """
    Takes field metadata and returns an appropriate field validator function.
    """

    # Catch special fields before trying the standard validators.
    special_names = {
        "cofog": cofogValidator,
        "gfsmExpense": gfsmExpenseValidator,
        "gfsmRevenue": gfsmRevenueValidator,
        "type": typeValidator
    }
    if field["name"] in special_names.keys():
        return special_names[field["name"]]

    # Dates and datetimes require special treatment; catch those too.
    if field["type"] in ["date", "datetime"]:
        return dateFieldValidator(field)

    # For the rest: default field parsers.
    field_parsers = {
        'number': float,
        'integer': int,
        'int': int,
        'string': str,
        'time': lambda x: time.strptime(x, '%H:%M'),
        'boolean': bool,
        'binary': base64.b64decode,
        'object': json.loads,
        'json': json.loads,
        'geojson': json.loads,
        'array': list,
        }

    if field["type"] in field_parsers.keys():
        return field_parsers[field["type"]]
    raise ValueError("No field validator for field type " + field["type"])

def dateFieldValidator(field):
    """
    Generator for validators functions for date fields.
    Takes a field of type `date` and returns an appropriate validator.
    
    This validator will either use the default ISO6801 format
    or the format supplied on the field itself.
    """
    if not (field["type"] == "datetime" or field["type"] == "date"):
        raise ValueError("DateFieldValidator error: field type " + field["type"])
    if "format" in field:
        format_string = field["format"]
        # The following is borrowed from datapackage.py...

        # Order of the replacements is important since month and minutes
        # can be denoted in a similar fashion
        replacement_order = [('hh', '%m'), (':mm', ':%M'), ('ss', '%S'),
                             ('yyyy', '%Y'), ('yy', '%y'), ('mm', '%m'),
                             ('dd', '%d')]

        # For each replacement we substitute (and ignore the case)
        for (old, new) in replacement_order:
            format_string = re.sub("(?i)%s" % old, new, format_string)
        if field["type"] == "datetime":
            return lambda x: datetime.datetime.strptime(x, format_string)
        else:
            return lambda x: datetime.datetime.strptime(x, format_string).date()
    else:
        if field["type"] == "datetime":
            return lambda x: datetime.datetime.strptime(x, '%Y-%m-%dT%H:%M:%S%Z')
        else:
            return lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date()

def cofogValidator(cofog):
    """
    Validator function.
    Checks if a string is a valid COFOG value.
    """
    p = r"^((10)|(0?[1-9]))(\.[1-9]){0,2}$"
    if re.search(p,cofog):
        return cofog
    raise ValueError("Invalid COFOG value: " + cofog)

def gfsmRevenueValidator(gfsm):
    """
    Validator function.
    Checks if a string is a valid GFSM 2001 revenue value.
    """
    p = r"^1(1(1(1|2|3)?|2|3(1|2|3|4|5|6)?|4(1(1|2|3)?|2|3|4|5(1|2)?|6)?|5|6(1|2)?)?|2(1(1|2|3|4)?|2(1|2|3)?)?|3(1(1|2)?|2(1|2)?|3(1|2)?)?|4(1(1|2|3|4)?|2(1|2|3|4)?|3|4(1|2)?|5)?)?$"
    if re.search(p,gfsm):
        return gfsm
    raise ValueError("Invalid GFSM revenue value: " + gfsm)

def gfsmExpenseValidator(gfsm):
    """
    Validator function.
    Checks if a string is a valid GFSM 2001 expenditure value.
    """
    p = r"^2(1(1(1|2)?|2(1|2)?)?|2|3|4(1|2|3)?|5(1|2)?|6(1(1|2)?|2(1|2)?|3(1|2)?)?|7(1(1|2)?|2(1|2)?|3(1|2)?)?|8(1(1|2|3|4)?|2(1|2)?)?)?$"
    if re.search(p,gfsm):
        return gfsm
    raise ValueError("Invalid GFSM expense value: " + gfsm)

# Validator for "type" fields.
typeValidator = cv.enumeration(
    "personnel",
    "non-personnel recurrent",
    "capital",
    "other"
    )