import logging
import httpx
import smtplib
from email.mime.text import MIMEText
import yagmail
from datetime import datetime
from packetthings.config import config

logger = logging.getLogger(__name__)

sender = "packetworx24@gmail.com"
app_password = 'utdcmnikmfhieydw' # not plain password 

async def send_simple_message(to: str, subject: str, body: str):
    contents = [body] 

    with yagmail.SMTP(config.MAILSENDER, config.APP_PASSWORD) as yag:
        yag.send(to, subject, contents)
        logger.debug('Sent email successfully')


class APIResponseError(Exception):
    pass


async def yysend_simple_message(to: str, subject: str, body: str):
    logger.debug(f"Sending email to '{to[:3]}' with subject '{subject[:20]}'")
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(sender, "utdc mnik mfhi eydw")
       smtp_server.sendmail(sender, recipients, msg.as_string())
    logger.debug("Message sent!")


async def xxsend_simple_message(to: str, subject: str, body: str):
    logger.debug(f"Sending email to '{to[:3]}' with subject '{subject[:20]}'")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.mailgun.net/v3/{config.MAILGUN_DOMAIN}/messages",
                auth=("api", config.MAILGUN_API_KEY),
                data={
                    "from": f"PacketWorx <mailgun@{config.MAILGUN_DOMAIN}>",
                    "to": [to],
                    "subject": subject,
                    "text": body,
                },
            )
            response.raise_for_status()

            logger.debug(response.content)

            return response
        except httpx.HTTPStatusError as err:
            raise APIResponseError(
                f"API request failed with status code {err.response.status_code}"
            ) from err


async def send_user_registration_email(email: str, confirmation_url: str):
    confirmation_url = "<a href=" + config.CONFIRMATION_URL + confirmation_url + ">Click to verify email</a>"
    return await send_simple_message(
        email,
        "Successfully signed up",
        (
            f"Hi {email}! You have successfully signed up to PacketThings.  Thank you! "
            # " Please confirm your email by clicking on the"
            # f" following link: {confirmation_url}"
        ),
    )


async def send_forgot_password_email(email: str, confirmation_url: str):
    token1 = confirmation_url
    confirmation_url = "<a href=" + config.RESETPASSWORD_URL + token1 + ">Click to rest password</a>"
    return await send_simple_message(
        email,
        "Reset password",
        (
            f"Hi {email}! This is your reset password. <br>"
            " Please click on the"
            f" following link: {confirmation_url} <br>"
            f" This is your reset token: {token1}"
        ),
    )


async def send_otp_email(email: str, otp: str):
    now = datetime.now()
    return await send_simple_message(
        email,
        "OTP",
        (
            f" This is your OTP: {otp} sent at " + now.strftime("%Y-%m-%d %H:%M:%S")
        ),
    )


