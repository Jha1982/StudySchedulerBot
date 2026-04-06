import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://nmc.udu.edu.ua/cgi-bin/timetable.cgi"

data = {
    "group": "2-033",   # аудитория
    "submit": "Показати розклад занять"
}

response = requests.post(URL, data=data, verify=False)
response.encoding = "cp1251"

soup = BeautifulSoup(response.text, "html.parser")

print(soup.get_text()[:2000])
