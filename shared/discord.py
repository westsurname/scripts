import requests
from discord_webhook import DiscordWebhook, DiscordEmbed
from shared.shared import discord, checkRequiredEnvs
from datetime import datetime

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

def discordUpdate(title, message=None, color=3066993, message_id=None, content=None, timestamp=None):
    embed = DiscordEmbed(title=title, description=message, color=color)
    embed.set_author(name="Blackhole", icon_url="https://cdn.discordapp.com/attachments/1222893572521594962/1262384669161295934/black-hole-556660.png?ex=669666d7&is=66951557&hm=e792b1162ea86c1ba24ee9f4568c571ff1e3429e5b295555fea3fcb94404b434&")
    
    if timestamp:
        embed.set_timestamp(datetime.fromisoformat(timestamp[:-1]))

    webhook = DiscordWebhook(
        url=discord['webhookUrl'], 
        rate_limit_retry=True, 
        username='Update Bot',
        content=content
    )
    webhook.add_embed(embed)

    if message_id:
        webhook.id = message_id
        response = webhook.edit()
    else:
        response = webhook.execute()
        return response.json().get('id')
