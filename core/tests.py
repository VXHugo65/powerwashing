from django.test import TestCase

from twilio.rest import Client


account_sid = 'AC87272ca1c7cd1567927e11b72836e740'
auth_token = '049010abb21487b3e490ece5e33527ce'
client = Client(account_sid, auth_token)
message = client.messages.create(
  messaging_service_sid='MGd18200a103b47c1c70cd4d254e3f6cb7',
  body='Ahoy 👋',
  to='+258878750526'
)
print(message.status)

