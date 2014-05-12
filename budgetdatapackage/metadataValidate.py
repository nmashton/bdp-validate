# -*- coding: utf-8 -*-

from jsonschema import validate, ValidationError
from voluptuous import Schema, Invalid

# Generic combinators for welding together validator functions.
def allValidators(reqs):
    """
    Takes an array of validator functions and returns a new
    function that tries each of the functions on an argument, returning
    the value of the last function in the array.
    (Validators should return the original value, so this should
    be the original value.)

    The returned function is also a validator function.

    This combinator has the effect of enforcing all the validators.
    It is like combining the validators by a logical `and`.
    """
    def composed(arg):
        for r in reqs:
            res = r(arg)
        return res
    return composed

def anyValidators(reqs):
    """
    The disjunctive equivalent of allValidators.

    Takes an array of validator functions and returns a new
    function that tries the functions until one of them works.
    If none of them does, it throws an aggregate ValueError.

    This is a short-circuiting `or` for validators.
    """
    def composed(arg):
        errors = []
        for r in reqs:
            try:
                res = r(arg)
                return res
            except Invalid as e:
                errors.append(e)
                pass
        raise Invalid("None satisfied: [" + ("; ".join([str(e) for e in errors]) + "]"))
    return composed

# Schema-specific validators.
def FieldRequirement(fieldname):
    """
    Takes a field name and returns a checker function.
    The function is a validator, per the voluptuous API:
    It returns the original value if it 'validates',
    and it throws an Invalid if it fails.

    The returned checker function takes a well-formed `fields` array
    from the Data Package metadata (i.e. an array that contains
    objects that include at least a `name` attribute) and
    ensures that the array contains an object with the field name.
    """
    def checker(fields):
        fieldnames = [x["name"] for x in fields]
        check = fieldname in fieldnames
        if check:
            return fields
        raise Invalid("Field missing: " + fieldname)
    return checker

# Field requirements for all data types.
generalFields = allValidators([
    FieldRequirement("amount"),
    FieldRequirement("id")
    ])

# Field requirements for aggregated expenditures data.
aggregatedExpenditureFields = allValidators([
    generalFields,
    FieldRequirement("admin"),
    anyValidators([
        FieldRequirement("functionalID"),
        FieldRequirement("cofog")
        ])
    ])

# Field requirements for aggregated revenue data.
# Transactional revenue data has the same requirements.
aggregatedRevenueFields = allValidators([
    generalFields,
    anyValidators([
        FieldRequirement("economicID"),
        FieldRequirement("gfsmRevenue")
        ])
    ])
transactionalRevenueFields = aggregatedRevenueFields

# Field requirements for transactional expenditure data.
transactionalExpenditureFields = allValidators([
    generalFields,
    FieldRequirement("admin"),
    FieldRequirement("date"),
    FieldRequirement("supplier")
    ])

def resourceFieldsValidator(resource):
    """
    Takes a resource object and returns the proper validator
    for its fields.
    """
    validators = {"aggregated-expenditure": aggregatedExpenditureFields,
        "transactional-expenditure": transactionalExpenditureFields,
        "aggregated-revenue": aggregatedRevenueFields,
        "transactional-revenue": transactionalRevenueFields}
    category = "-".join([resource["granularity"], resource["type"]])
    return validators[category]

def validateResource(resource):
    """
    Validates a resource object in a type-sensitive way.
    """
    schema = Schema({"schema": {"fields": resourceFieldsValidator(resource)}}, extra=True)
    return schema(resource)

def validateMetadata(metadata,schema):
    """
    Takes a metadata object and the Budget Data Package JSON schema.
    Attempts to validate the metadata.

    First, the basic requirements given by the JSON schema are tested.

    Next, the deeper requirements are satisfied.
    For now, the only 'deep requirement' is that the inner JSON table
    schema's `fields` attribute contain the fields that are appropriate
    to data of the type given by the resource's `granularity` and `type`
    attributes.
    """
    # This is a simple wrapper for jsonschema.
    # If JSON Schema validation fails, an Invalid exception will be raised.
    try:
        validate(metadata,schema)
    except ValidationError as e:
        raise Invalid("JSON Schema validation error: " + str(e))
    schema = Schema({
        "resources": [validateResource]
        }, extra=True)
    # This will throw an Invalid exception if this doesn't work.
    schema(metadata)
    return metadata
