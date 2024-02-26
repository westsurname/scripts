from discord_webhook import DiscordWebhook, DiscordEmbed
from shared.shared import discord

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

def discordUpdate(title, message=None):
    if discord['updateEnabled']:
        embed = DiscordEmbed(title, message, color=3066993)
        webhook = DiscordWebhook(
            url=discord['webhookUrl'], 
            rate_limit_retry=True, 
            username='Update Bot', 
            embeds=[embed]
        )
        response = webhook.execute()
