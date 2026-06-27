from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import ORJSONResponse
from postal import expand as expand_
from postal.parser import parse_address

app = FastAPI(default_response_class=ORJSONResponse)


def _build_structured(parsed: list[list[str]]) -> dict[str, str]:
    address1_parts: list[str] = []
    address2_parts: list[str] = []
    city = ""
    state = ""
    postal = ""
    country = ""

    for value, component in parsed:
        match component:
            case "house_number" | "road":
                address1_parts.append(value.upper())
            case (
                "unit"
                | "building"
                | "entrance"
                | "staircase"
                | "level"
                | "po_box"
                | "house"
                | "block"
                | "neighbourhood"
            ):
                address2_parts.append(value.upper())
            case "city" | "suburb":
                city = value.upper()
            case "state" | "province":
                state = value.upper()
            case "postal_code" | "postcode":
                postal = value.upper()
            case "country":
                country = value.upper()

    return {
        "address1": " ".join(address1_parts),
        "address2": " ".join(address2_parts) if address2_parts else "",
        "city": city,
        "state": state,
        "postal": postal,
        "country": country,
    }


@app.get("/parse")
def parse(
    address: str,
    language: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> list[list[str]]:
    """Wrap https://github.com/openvenues/pypostal/blob/1.1/postal/parser.py."""
    if country is not None and language is None:
        detail = "Specifying country without specifying language is disallowed"
        raise HTTPException(status_code=400, detail=detail)
    return parse_address(**locals())


@app.get("/format")
def format_address(
    address: str,
    language: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> dict[str, str]:
    """Parse an address and return structured fields."""
    if country is not None and language is None:
        detail = "Specifying country without specifying language is disallowed"
        raise HTTPException(status_code=400, detail=detail)
    parsed = parse_address(address=address, language=language, country=country)
    return _build_structured(parsed)


@app.get("/expand")
def expand(
    address: str,
    languages: Annotated[list[str] | None, Query(min_length=2, max_length=2)] = None,
    # defaults taken from https://github.com/openvenues/libpostal/blob/e2590bca/src/libpostal.c#L22-L44
    address_components: int = (
        expand_.ADDRESS_NAME
        | expand_.ADDRESS_HOUSE_NUMBER
        | expand_.ADDRESS_STREET
        | expand_.ADDRESS_PO_BOX
        | expand_.ADDRESS_UNIT
        | expand_.ADDRESS_LEVEL
        | expand_.ADDRESS_ENTRANCE
        | expand_.ADDRESS_STAIRCASE
        | expand_.ADDRESS_POSTAL_CODE
    ),
    latin_ascii: bool = True,
    transliterate: bool = True,
    strip_accents: bool = True,
    decompose: bool = True,
    lowercase: bool = True,
    trim_string: bool = True,
    replace_word_hyphens: bool = False,
    delete_word_hyphens: bool = False,
    replace_numeric_hyphens: bool = True,
    delete_numeric_hyphens: bool = True,
    split_alpha_from_numeric: bool = True,
    delete_final_periods: bool = True,
    delete_acronym_periods: bool = True,
    drop_english_possessives: bool = True,
    delete_apostrophes: bool = True,
    expand_numex: bool = True,
    roman_numerals: bool = True,
) -> list[str]:
    """Wrap https://github.com/openvenues/pypostal/blob/1.1/postal/expand.py."""
    return expand_.expand_address(**locals())


@app.get("/expandparse")
def expandparse(
    address: str,
    language: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    address_components: int = (
        expand_.ADDRESS_NAME
        | expand_.ADDRESS_HOUSE_NUMBER
        | expand_.ADDRESS_STREET
        | expand_.ADDRESS_PO_BOX
        | expand_.ADDRESS_UNIT
        | expand_.ADDRESS_LEVEL
        | expand_.ADDRESS_ENTRANCE
        | expand_.ADDRESS_STAIRCASE
        | expand_.ADDRESS_POSTAL_CODE
    ),
    latin_ascii: bool = True,
    transliterate: bool = True,
    strip_accents: bool = True,
    decompose: bool = True,
    lowercase: bool = True,
    trim_string: bool = True,
    replace_word_hyphens: bool = False,
    delete_word_hyphens: bool = False,
    replace_numeric_hyphens: bool = True,
    delete_numeric_hyphens: bool = True,
    split_alpha_from_numeric: bool = True,
    delete_final_periods: bool = True,
    delete_acronym_periods: bool = True,
    drop_english_possessives: bool = True,
    delete_apostrophes: bool = True,
    expand_numex: bool = True,
    roman_numerals: bool = True,
) -> list[list[list[str]]]:
    """Wrap expand, and parse all outputs."""
    kwargs = locals().copy()
    kwargs.pop("language", None)
    kwargs.pop("country", None)
    kwargs["languages"] = [language] if language else None
    return [
        parse(address=address, language=language, country=country)
        for address in expand(**kwargs)
    ]
