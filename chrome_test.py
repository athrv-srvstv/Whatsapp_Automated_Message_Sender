import yaml, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
p = yaml.safe_load(open(open("settings_path.txt").read().strip()))["chrome_settings"]
print("using:", p["path_to_chrome"])
o = Options()
o.add_argument("start-maximized")
o.add_argument("--user-data-dir=./user_data/test_profile")
o.binary_location = p["path_to_chrome"]
d = webdriver.Chrome(options=o)
d.get("https://web.whatsapp.com")
print("Browser open. Holding for 90 seconds - scan the QR if you want.")
time.sleep(90)
d.quit()
