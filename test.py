import requests
import certifi

r = requests.get("https://shopify.com", verify=certifi.where())
print(r.status_code)
print(r)
print(certifi.where())