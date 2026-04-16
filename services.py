import httpx

async def get_genderize_data(name):
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.genderize.io', params={"name": name})
    return response.json()

async def get_agify_data(name):
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.agify.io', params={"name": name})
    return response.json()

async def get_nationalize_data(name):
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.nationalize.io', params={"name": name})
    return response.json()

def classify_age(age):
    if (age >= 60):
        return "senior"
    elif (age >=20):
        return "adult"
    elif (age >= 13):
        return "teenager"
    else:
        return "child"


def choose_country(country_list):
    return max(country_list, key=lambda c: c["probability"])




