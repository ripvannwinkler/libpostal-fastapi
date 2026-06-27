"""
libpostal-fastapi: Address parsing microservice.

Wraps libpostal (via pypostal) in a FastAPI service providing four endpoints:
  - /parse    — Raw component breakdown of an address
  - /format   — Structured fields (address1, city, state, postal, country, etc.)
  - /expand   — Generate address variants (e.g. "St" → "Street")
  - /expandparse — Expand then parse each variant

Country auto-detection in /format:
  1. Parsed from address data (highest priority)
  2. US ZIP code pattern (\d{5} or \d{5}-\d{4}) → "US"
  3. Canadian postal code pattern ([A-HJ-NPR-TV-Z]\d[A-HJ-NPR-TV-Z] \d[A-HJ-NPR-TV-Z]\d) → "CA"
  4. User-provided ?country= query param (fallback)

Usage examples:
    curl 'http://localhost:8001/format?address=201+N+State+St,+Freeburg,+IL+62258'
    # {"address1":"201 N STATE ST","address2":"","city":"FREEBURG","state":"IL","postal":"62258","country":"US"}

    curl 'http://localhost:8001/format?address=760+Fountain+View+Dr,+Apt+D,+Mascoutah,+IL+62258'
    # {"address1":"760 FOUNTAIN VIEW DR","address2":"APT D","city":"MASCOUTAH","state":"IL","postal":"62258","country":"US"}

    curl 'http://localhost:8001/format?address=123+Ottawa+St,+Toronto,+ON+M5H+2N2'
    # {"address1":"123 OTTAWA ST","address2":"","city":"TORONTO","state":"ON","postal":"M5H 2N2","country":"CA"}
"""

import re
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import ORJSONResponse
from postal import expand as expand_
from postal.parser import parse_address

app = FastAPI(
    title="libpostal-fastapi",
    description="Address parsing microservice backed by libpostal.",
    default_response_class=ORJSONResponse,
)


def _build_structured(
    parsed: list[list[str]],
    user_country: str | None = None,
) -> dict[str, str]:
    """
    Convert raw pypostal output into structured address fields.

    Args:
        parsed: Raw output from postal.parser.parse_address(), e.g.:
            [["201","house_number"],["n state st","road"],["freeburg","city"],...]
        user_country: Optional country query param (?country=us) used as fallback.

    Returns:
        Dict with keys: address1, address2, city, state, postal, country.
        All values are uppercased for consistency.
    """
    # Accumulators — each field collects its value(s) from the parsed list
    address1_parts: list[str] = []  # house_number + road
    address2_parts: list[str] = []  # unit, apt, suite, building, etc.
    city = ""
    state = ""
    postal = ""
    country = ""

    # Map each parsed component to its corresponding structured field
    for value, component in parsed:
        match component:
            # Street address line 1: house number + street name
            case "house_number" | "road":
                address1_parts.append(value.upper())

            # Address line 2: apartment, unit, suite, floor, entrance, etc.
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

            # City-level components
            case "city" | "suburb":
                city = value.upper()

            # State/province/region
            case "state" | "province":
                state = value.upper()

            # Postal / zip code (pypostal returns "postal_code" or "postcode")
            case "postal_code" | "postcode":
                postal = value.upper()

            # Country (if present in parsed data)
            case "country":
                country = value.upper()

    # Auto-detect country from postal code patterns if not already set
    if not country and re.fullmatch(r"\d{5}(-\d{4})?", postal):
        country = "US"  # US ZIP or ZIP+4

    if not country and re.fullmatch(
        r"[ABCEGHJ-NPRSTV-Z]\d[ABCEGHJ-NPRSTV-Z] ?\d[ABCEGHJ-NPRSTV-Z]\d", postal
    ):
        country = "CA"  # Canadian A1A 1A1 format

    # Fallback: use user-provided country query param
    if not country and user_country:
        country = user_country.upper()

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
    language: Annotated[
        str | None, Query(min_length=2, max_length=2)
    ] = None,
    country: Annotated[
        str | None, Query(min_length=2, max_length=2)
    ] = None,
) -> list[list[str]]:
    """
    Parse an address into its component parts.

    Returns a flat list of [value, type] pairs describing each token in the address.

    Args:
        address: The full address string to parse (URL-encoded).
        language: Optional 2-letter language code (e.g. "en", "fr"). Required if country is set.
        country: Optional 2-letter country code (e.g. "us", "gb", "ca") for disambiguation.

    Raises:
        HTTPException(400): If country is provided without language.

    Example:
        GET /parse?address=30+W+26th+St,+New+York,+NY

        Returns:
            [["30","house_number"],["w 26th st","road"],["new york","city"],["ny","state"]]
    """
    if country is not None and language is None:
        raise HTTPException(
            status_code=400,
            detail="Specifying country without specifying language is disallowed",
        )
    return parse_address(**locals())


@app.get("/format")
def format_address(
    address: str,
    language: Annotated[
        str | None, Query(min_length=2, max_length=2)
    ] = None,
    country: Annotated[
        str | None, Query(min_length=2, max_length=2)
    ] = None,
) -> dict[str, str]:
    """
    Parse an address and return structured fields.

    This is the simplest endpoint for most use cases — it returns a flat JSON object
    with conventional address field names (address1, city, state, postal, country).

    Country auto-detection priority:
      1. Parsed from address data
      2. US ZIP pattern → "US"
      3. Canadian postal code pattern → "CA"
      4. User-provided ?country= query param (fallback)

    Args:
        address: The full address string to parse (URL-encoded).
        language: Optional 2-letter language code for disambiguation. Required if country is set.
        country: Optional 2-letter country code for disambiguation. Also returned in response.

    Raises:
        HTTPException(400): If country is provided without language.

    Example:
        GET /format?address=201+N+State+St,+Freeburg,+IL+62258

        Returns:
            {
              "address1": "201 N STATE ST",
              "address2": "",
              "city": "FREEBURG",
              "state": "IL",
              "postal": "62258",
              "country": "US"
            }

        GET /format?address=760+Fountain+View+Dr,+Apt+D,+Mascoutah,+IL+62258

        Returns:
            {
              "address1": "760 FOUNTAIN VIEW DR",
              "address2": "APT D",
              "city": "MASCOUTAH",
              "state": "IL",
              "postal": "62258",
              "country": "US"
            }
    """
    if country is not None and language is None:
        raise HTTPException(
            status_code=400,
            detail="Specifying country without specifying language is disallowed",
        )
    parsed = parse_address(address=address, language=language, country=country)
    return _build_structured(parsed, user_country=country)


@app.get("/expand")
def expand(
    address: str,
    languages: Annotated[list[str] | None, Query(min_length=2, max_length=2)] = None,
    # Defaults for address_components taken from libpostal source:
    # https://github.com/openvenues/libpostal/blob/e2590bca/src/libpostal.c#L22-L44
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
    """
    Expand an address into multiple normalized variants.

    Generates alternative spellings and expansions (e.g. "St" → "Street", "Ave" → "Avenue")
    useful for fuzzy matching or normalization before parsing.

    Args:
        address: The address string to expand.
        languages: Optional list of 2-letter language codes.
        address_components: Bitmask controlling which components to expand (see libpostal docs).
        latin_ascii: Convert non-ASCII chars to Latin equivalents.
        transliterate: Transliterate text to ASCII where possible.
        strip_accents: Remove diacritical marks (é → e).
        decompose: Decompose characters into base + combining marks.
        lowercase: Lowercase all output.
        trim_string: Trim leading/trailing whitespace from tokens.
        replace_word_hyphens: Replace hyphens with spaces between words.
        delete_word_hyphens: Remove hyphens between words entirely.
        replace_numeric_hyphens: Replace hyphens in numbers (123-456 → 123 456).
        delete_numeric_hyphens: Remove hyphens in numbers entirely.
        split_alpha_from_numeric: Split adjacent letters and digits (A1B → A 1 B).
        delete_final_periods: Remove trailing periods from tokens.
        delete_acronym_periods: Remove periods between capital letters (U.S.A → USA).
        drop_english_possessives: Remove 's / 'es suffixes.
        delete_apostrophes: Remove all apostrophes.
        expand_numex: Expand number expressions ("2nd" → "two").
        roman_numerals: Expand Roman numerals ("II" → "two").

    Example:
        GET /expand?address=30+W+26th+St,+New+York,+NY

        Returns:
            [
              "30 west 26th saint new york ny",
              "30 west 26th street new york ny",
              ...
            ]
    """
    return expand_.expand_address(**locals())


@app.get("/expandparse")
def expandparse(
    address: str,
    language: Annotated[
        str | None, Query(min_length=2, max_length=2)
    ] = None,
    country: Annotated[
        str | None, Query(min_length=2, max_length=2)
    ] = None,
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
    """
    Expand an address into variants, then parse each variant.

    Combines /expand and /parse to return multiple possible parses of ambiguous addresses.
    Useful for finding the best match when an address has multiple valid interpretations.

    Args:
        address: The address string to expand and parse.
        language: Optional 2-letter language code (e.g. "en"). Required if country is set.
        country: Optional 2-letter country code (e.g. "us") for disambiguation.
        address_components: Bitmask of components to expand (same as /expand).
        [Other parameters same as /expand — see that endpoint's docstring.]

    Returns:
        A list of parsed results, one per expanded variant. Each result is a list of
        [value, type] pairs (same format as /parse).

    Example:
        GET /expandparse?address=30+W+26th+St,+New+York,+NY&language=en&country=us

        Returns:
            [
              [["30","house_number"],["west 26th saint","road"],["new york","city"],["ny","state"]],
              [["30","house_number"],["west 26th street","road"],["new york","city"],["ny","state"]]
            ]
    """
    kwargs = locals().copy()
    kwargs.pop("language", None)
    kwargs.pop("country", None)
    kwargs["languages"] = [language] if language else None
    return [
        parse(address=address, language=language, country=country)
        for address in expand(**kwargs)
    ]
