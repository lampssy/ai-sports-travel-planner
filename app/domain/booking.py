from urllib.parse import urlencode


def build_accommodation_link(*, destination_name: str, country: str) -> str:
    query = urlencode(
        {
            "ss": f"{destination_name}, {country}",
            "group_adults": 2,
            "no_rooms": 1,
            "group_children": 0,
        }
    )
    return f"https://www.booking.com/searchresults.html?{query}"
