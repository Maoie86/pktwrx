# client_id = '1289454324791756'
client_id = '178645168876408'
# client_secret = '7194bea28417ba2b03d098a3ab5fccb1'
client_secret = 'e70663cb985efc715c0b06614c0cedb9'

# OAuth endpoints given in the Facebook API documentation
authorization_base_url = 'https://www.facebook.com/dialog/oauth'
token_url = 'https://graph.facebook.com/oauth/access_token'
redirect_uri = 'https://supabase-dev.packetworx.org:8443/facebook/callback'     # Should match Site URL

from requests_oauthlib import OAuth2Session
from requests_oauthlib.compliance_fixes import facebook_compliance_fix
facebook = OAuth2Session(client_id, redirect_uri=redirect_uri)
facebook = facebook_compliance_fix(facebook)

# Redirect user to Facebook for authorization
authorization_url, state = facebook.authorization_url(authorization_base_url)
print(state)

print('Please go here and authorize,', authorization_url)


# Get the authorization verifier code from the callback url
redirect_response = input('Paste the full redirect URL here:')

# Fetch the access token
facebook.fetch_token(token_url, client_secret=client_secret,
                     authorization_response=redirect_response)

# Fetch a protected resource, i.e. user profile
print(state)
r = facebook.get('https://graph.facebook.com/me??fields=id,name,email')
print(r.content)



