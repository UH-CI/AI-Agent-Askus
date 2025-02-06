from bs4 import BeautifulSoup
import requests

request = requests.get("https://www.hawaii.edu/policy/index.php?action=viewPolicy&policySection=ap&policyChapter=9&policyNumber=030")

soup = BeautifulSoup(request.content, "html.parser")
print(soup.prettify())