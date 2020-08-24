import requests
from requests_oauthlib import OAuth2Session
import pyperclip



''' ------------------------------------------------------------------------------------------------
INSTRUCTIONS

This process is difficult to automate and requires a users input, but only needs to be done once a year
1) Make sure to change the password_file  variable to the desired file name
2) Make sure to be signed in as a Canvas admin in a web browser
3) Run the code in the Windows Command Prompt
	a. This Command Prompt code is used to go to the folder called API in your Documents: 
			cd Documents/API
	b. Once in the correct directory, this code is used to run the python file:
			python new_refresh_token.py
4) The code will prompt the user to enter a link in their browser, which they are signed in as an admin
5) The user will have to click "Authorize"
6) Once Authorized, a code will be in the URL and needs to be copied onto the users clipboard
	a. There is other information in the URL besides the code
7) The user will now paste the code into the command prompt and press <enter>
8) The refresh token will now be in the passwords file

------------------------------------------------------------------------------------------------ '''


# This is the only variable necessary to change:
password_file = "name_of_password_file.txt"


# Open passwords file and gets all passwords
file = open(password_file, "r+")
passwords = eval(str(file.read()))
file.close()
client_id = passwords.get("client_id")
client_secret = passwords.get("client_secret")
login_url = passwords.get("login_url")
redirect_uri = passwords.get("redirect_uri")
token_url = passwords.get("token_url")


# Request a code from Canvas using credentials
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)
authorization_url, state = oauth.authorization_url(login_url)


# Authorize and get the code from Canvas
pyperclip.copy(authorization_url)
print ("The link is in your clipboard. Paste link into web browser and authorize the request.")
print ("Make sure you are signed in with an admin Canvas account")
print ("Click 'Authorize', the code will be in the URL. Copy only the code.")
code = str(input('Enter code:'))


# Recieve the new refresh token
data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': redirect_uri}
r = requests.post(token_url, data=data, auth=(client_id, client_secret))
refresh_token = r.json().get("refresh_token")[5:]


# Inputs the new token in our passwords file
passwords["refresh_token"] = refresh_token
file = open(password_file, "w+")
file.write(str(passwords))
file.close()
print ("--------- Process Complete ---------")
print ("You can now access the API data")