CITIES = {
    "Hyderabad": ["SC", "HYB", "KCG", "LPI"],
    "Kolkata": ["HWH", "KOAA", "SDAH", "SHM", "SRC"],
    "Delhi": ["NDLS", "DLI", "NZM", "ANVT", "DEE"],
    "Mumbai": ["CSMT", "MMCT", "LTT", "BDTS", "DR", "DDR"],
    "Chennai": ["MAS", "MS"],
    "Bengaluru": ["SBC", "SMVB", "YPR", "BNC"],
    "Lucknow": ["LKO", "LJN"],
    "Kochi": ["ERS", "ERN"],
    "Varanasi": ["BSB", "BCY"],
    "Patna": ["PNBE", "PNC"],
    "Jaipur": ["JP", "GADJ"],
    "Kanpur": ["CNB", "CPA"],
    "Goa": ["MAO", "THVM", "KRMI", "VSG"],  # no station is actually called Goa
    "Visakhapatnam": ["VSKP"],
}

OTHER_NAMES = {
    "Bangalore": "Bengaluru",
    "Calcutta": "Kolkata",
    "Bombay": "Mumbai",
    "Madras": "Chennai",
    "New Delhi": "Delhi",
    "Secunderabad": "Hyderabad",
    "Cochin": "Kochi",
    "Ernakulam": "Kochi",
    "Banaras": "Varanasi",
    "Madgaon": "Goa",
    "Margao": "Goa",
    "Vizag": "Visakhapatnam",
}

#  names in the dataset are abbreviated 
DISPLAY_NAMES = {
    "MAS": "Chennai Central",
    "CSMT": "Mumbai CSMT",
    "KOAA": "Kolkata Terminal",
    "DDU": "Pt Deen Dayal Upadhyaya Jn",
    "LTT": "Lokmanya Tilak Terminus",
    "SBC": "KSR Bengaluru",
    "SMVB": "SMVT Bengaluru",
    "JAT": "Jammu Tawi",
    "VGLJ": "Jhansi (Virangana Lakshmibai)",
    "RKMP": "Rani Kamalapati (Bhopal)",
}


def city_matches(q):
    q = q.strip().lower()
    out = []
    for city, codes in CITIES.items():
        names = [city] + [k for k, v in OTHER_NAMES.items() if v == city]
        if any(n.lower().startswith(q) for n in names):
            out.append(city)
    return out
