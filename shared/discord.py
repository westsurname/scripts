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

def discordStatusUpdate(torrentDict, webhook=None, edit=False, delete=False):
    if discord['updateEnabled']:
        if webhook and webhook.id:
            webhook.delete()

        webhook = DiscordWebhook(
            url=discord['webhookUrl'], 
            rate_limit_retry=True, 
            username='Status Bot'
        )
        
        if delete:
            embed = DiscordEmbed("Downloading Status", f"No Active Downloads", color=9807270)
            webhook.add_embed(embed)
            # response = webhook.edit()
            webhook.__dict__["flags"] = 4096
            response = webhook.execute(remove_embeds=True)
            return webhook
        
        if not edit:
            embed = DiscordEmbed("Downloading Status", f"Current downloading - {len(torrentDict)}", color=16776960)
            for filename,progress in torrentDict.items():
                embed.add_embed_field(name=filename, value=progress, inline=False)
                
            webhook.add_embed(embed)
            # response = webhook.edit()
            webhook.__dict__["flags"] = 4096
            response = webhook.execute(remove_embeds=True)
            return webhook
        else:
            # webhook.remove_embeds() # Used for editing
            embed = DiscordEmbed("Downloading Status", f"Current downloading - {len(torrentDict)}", color=16776960)
            for filename,progress in torrentDict.items():
                embed.add_embed_field(name=filename, value=progress, inline=False)

            webhook.add_embed(embed)
            # response = webhook.edit() # used for editing
            webhook.__dict__["flags"] = 4096
            response = webhook.execute(remove_embeds=True)
            return webhook