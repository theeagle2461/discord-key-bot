print("BOT_BUILD=admin-gated-no-autobuy-002")
# ... existing code ...
# Special admin user IDs for key generation and management
SPECIAL_ADMIN_IDS = [1216851450844413953, 414921052968452098, 485182079923912734]  # Admin user IDs

# Reusable app command check for special admins
from discord import app_commands as _appc

def special_admin_only():
    async def _pred(interaction: discord.Interaction) -> bool:
        return interaction.user.id in SPECIAL_ADMIN_IDS
    return _appc.check(_pred)
# Error handling for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CheckFailure):
        try:
            await interaction.response.send_message("❌ Special admins only.", ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send("❌ Special admins only.")
            except Exception:
                pass
        return
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        try:
            await interaction.response.send_message(f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send(f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            except Exception:
                pass
    elif isinstance(error, discord.app_commands.MissingPermissions):
        try:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send("❌ You don't have permission to use this command.")
            except Exception:
                pass
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        try:
            await interaction.response.send_message("❌ I don't have the required permissions to execute this command.", ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send("❌ I don't have the required permissions to execute this command.")
            except Exception:
                pass
    else:
        try:
            await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
        except Exception:
            try:
                await interaction.followup.send(f"❌ An error occurred: {str(error)}")
            except Exception:
                pass
