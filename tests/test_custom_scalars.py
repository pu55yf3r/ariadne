from datetime import date, datetime

from graphql import graphql_sync
from graphql.language.ast import StringValueNode

from ariadne import make_executable_schema

TEST_DATE = date(2006, 9, 13)
TEST_DATE_SERIALIZED = TEST_DATE.strftime("%Y-%m-%d")

type_defs = """
    scalar DateReadOnly
    scalar DateInput

    type Query {
        testSerialize: DateReadOnly!
        testInput(value: DateInput!): Boolean!
    }
"""


def serialize(date):
    return date.strftime("%Y-%m-%d")


def parse_literal(ast):
    if not isinstance(ast, StringValueNode):
        raise ValueError()

    formatted_date = ast.value
    parsed_datetime = datetime.strptime(formatted_date, "%Y-%m-%d")
    return parsed_datetime.date()


def parse_value(formatted_date):
    parsed_datetime = datetime.strptime(formatted_date, "%Y-%m-%d")
    return parsed_datetime.date()


def resolve_test_serialize(*_):
    return TEST_DATE


def resolve_test_input(*_, value):
    assert value == TEST_DATE
    return True


resolvers = {
    "Query": {"testSerialize": resolve_test_serialize, "testInput": resolve_test_input},
    "DateReadOnly": {"serialize": serialize},
    "DateInput": {"parse_literal": parse_literal, "parse_value": parse_value},
}

schema = make_executable_schema(type_defs, resolvers)


def test_serialize_date_obj_to_date_str():
    result = graphql_sync(schema, "{ testSerialize }")
    assert result.errors is None
    assert result.data == {"testSerialize": TEST_DATE_SERIALIZED}


def test_parse_literal_valid_str_ast_to_date_instance():
    test_input = TEST_DATE_SERIALIZED
    result = graphql_sync(schema, '{ testInput(value: "%s") }' % test_input)
    assert result.errors is None
    assert result.data == {"testInput": True}


def test_parse_literal_invalid_str_ast_to_date_instance():
    test_input = "invalid string"
    result = graphql_sync(schema, '{ testInput(value: "%s") }' % test_input)
    assert result.errors is not None
    assert str(result.errors[0]).splitlines()[:1] == [
        'Expected type DateInput!, found "invalid string"; '
        "time data 'invalid string' does not match format '%Y-%m-%d'"
    ]


def test_parse_literal_invalid_int_ast_errors():
    test_input = 123
    result = graphql_sync(schema, "{ testInput(value: %s) }" % test_input)
    assert result.errors is not None
    assert str(result.errors[0]).splitlines()[:1] == [
        "Expected type DateInput!, found 123."
    ]


parametrized_query = """
    query parseValueTest($value: DateInput!) {
        testInput(value: $value)
    }
"""


def test_parse_value_valid_date_str_returns_date_instance():
    variables = {"value": TEST_DATE_SERIALIZED}
    result = graphql_sync(schema, parametrized_query, variable_values=variables)
    assert result.errors is None
    assert result.data == {"testInput": True}


def test_parse_value_invalid_str_errors():
    variables = {"value": "invalid string"}
    result = graphql_sync(schema, parametrized_query, variable_values=variables)
    assert result.errors is not None
    assert str(result.errors[0]).splitlines()[:1] == [
        "Variable '$value' got invalid value 'invalid string'; "
        "Expected type DateInput; "
        "time data 'invalid string' does not match format '%Y-%m-%d'"
    ]


def test_parse_value_invalid_value_type_int_errors():
    variables = {"value": 123}
    result = graphql_sync(schema, parametrized_query, variable_values=variables)
    assert result.errors is not None
    assert str(result.errors[0]).splitlines()[:1] == [
        "Variable '$value' got invalid value 123; Expected type DateInput; "
        "strptime() argument 1 must be str, not int"
    ]
