import requests

def get_facebook_user_name(adid, access_token):
    url = f"https://graph.facebook.com/{adid}"
    params = {
        "fields": "name",
        "access_token": access_token
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("name")
    else:
        return None
