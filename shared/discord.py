import requests
from discord_webhook import DiscordWebhook, DiscordEmbed
from shared.shared import discord, checkRequiredEnvs

def validateDiscordWebhookUrl():
    url = discord['webhookUrl']
    try:
        response = requests.get(url)
        return response.status_code == 200
    except Exception as e:
        return False

requiredEnvs = {
    'Discord webhook URL': (discord['webhookUrl'], validateDiscordWebhookUrl)
}

if discord['enabled'] or discord['updateEnabled']:
    checkRequiredEnvs(requiredEnvs)

def discordError(title, message=None):
    if discord['enabled']:
        embed = DiscordEmbed(title, f"```{message}```", color=15548997)
        webhook = DiscordWebhook(
            url=discord['webhookUrl'], 
            rate_limit_retry=True, 
            username='Error Bot', 
            embeds=[embed]
        )
        response = webhook.execute()
        return response.json().get('id')

def discordUpdate(title, message=None, color=3066993, message_id=None):
    embed = DiscordEmbed(title=title, description=message, color=color)
    webhook = DiscordWebhook(
        url=discord['webhookUrl'], 
        rate_limit_retry=True, 
        username='Update Bot'
    )
    webhook.add_embed(embed)

    if message_id:
        webhook.id = message_id
        response = webhook.edit()
    else:
        response = webhook.execute()
        return response.json().get('id')
