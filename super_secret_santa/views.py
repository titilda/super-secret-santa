import discord
import psycopg.errors
from discord.interactions import Interaction
from psycopg import AsyncCursor
from loguru import logger
from time import sleep

from . import constants
from .bot import bot
from .secret_santa import secret_santa_algo
from .database import get_connection, create_santa_assignment


class CampaignView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent

    @discord.ui.button(label="Join Secret Santa!", custom_id="join-sss", style=discord.ButtonStyle.primary, emoji="🎅")
    async def join_button_callback(self, button, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        async with get_connection() as conn:
            try:
                cur = conn.cursor()
                await cur.advisory_lock(interaction.guild.id)

                await cur.execute(
                    "SELECT state FROM Campaigns WHERE guild_id = %s AND state = 'started';", (interaction.guild.id,)
                )
                started = await cur.fetchone()
                if started:
                    await interaction.followup.send(
                        "The campaign has already started. You cannot join now.",
                        delete_after=constants.DELETE_AFTER_DELAY,
                        ephemeral=True,
                    )
                    return

                try:
                    await cur.execute(
                        "INSERT INTO Memberships (user_id, guild_id) VALUES (%s, %s);",
                        (interaction.user.id, interaction.guild.id),
                    )
                except psycopg.errors.ForeignKeyViolation:
                    await interaction.followup.send(
                        "There is no Secret Santa campaign on this server. You may create one with `/santa create <name>`.",
                        delete_after=constants.DELETE_AFTER_DELAY,
                        ephemeral=True,
                    )
                    return
            except psycopg.errors.UniqueViolation:
                await interaction.followup.send(
                    "You have already joined the **Secret Santa campaign!**",
                    delete_after=constants.DELETE_AFTER_DELAY,
                    ephemeral=True,
                )
                return

        await interaction.followup.send(
            "You have joined the **Secret Santa campaign!**", ephemeral=True, delete_after=constants.DELETE_AFTER_DELAY
        )
        logger.info(f"User {interaction.user.global_name} joined the campaign {interaction.message.id}")

    @discord.ui.button(
        label="Leave Secret Santa!", custom_id="leave-sss", style=discord.ButtonStyle.danger, emoji="🎄"
    )
    async def leave_button_callback(self, button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with get_connection() as conn:
            # if the user is the organizer, they cannot leave
            cur = conn.cursor()
            await cur.advisory_lock(interaction.guild.id)
            await cur.execute(
                "SELECT is_organizer FROM Memberships WHERE user_id = %s AND guild_id = %s AND is_organizer = TRUE;",
                (interaction.user.id, interaction.guild.id),
            )
            is_organizer = await cur.fetchone()
            if is_organizer:
                await interaction.followup.send(
                    "You are the organizer. To delete the campaign, use `/santa delete`",
                    delete_after=constants.DELETE_AFTER_DELAY,
                    ephemeral=True,
                )
                return

            # if the campaign is already started, the user cannot leave
            await cur.execute(
                "SELECT state FROM Campaigns WHERE guild_id = %s AND state = 'started';",
                (interaction.guild.id,),
            )
            started = await cur.fetchone()
            if started:
                await interaction.followup.send(
                    "The campaign has already started. You cannot leave now.",
                    delete_after=constants.DELETE_AFTER_DELAY,
                    ephemeral=True,
                )
                return

            await cur.execute(
                "DELETE FROM Memberships WHERE user_id = %s AND guild_id = %s RETURNING *;",
                (interaction.user.id, interaction.guild.id),
            )

            result = await cur.fetchone()

            await interaction.followup.send(
                (
                    "You have left the **Secret Santa campaign!**"
                    if result
                    else "You are not part of a campaign on this server!"
                ),
                delete_after=constants.DELETE_AFTER_DELAY,
                ephemeral=True,
            )

            logger.info(f"User {interaction.user.global_name} left the campaign {interaction.message.id}")

    @discord.ui.button(
        label="Start Secret Santa!", custom_id="start-sss", style=discord.ButtonStyle.success, emoji="🎁"
    )
    async def start_button_callback(self, button, interaction: discord.Interaction):
        await interaction.response.defer()

        async with get_connection() as conn:
            cur: AsyncCursor = conn.cursor()
            await cur.advisory_lock(interaction.guild.id)

            await cur.execute(
                "SELECT user_id FROM Memberships WHERE guild_id = %s;",
                (interaction.guild.id,),
            )
            members: list[int] = [member[0] for member in await cur.fetchall()]

            if len(members) < 3:
                if len(members) == 0:
                    error_message = "No members have joined a campaign or none exists!"
                else:
                    error_message = "You need at least 3 members to start the Secret Santa campaign!"
                await interaction.followup.send(
                    error_message, delete_after=constants.DELETE_AFTER_DELAY, ephemeral=True
                )
                return

            # only continue if the user is the organizer
            await cur.execute(
                "SELECT is_organizer FROM Memberships WHERE user_id = %s AND guild_id = %s AND is_organizer = TRUE;",
                (interaction.user.id, interaction.guild.id),
            )

            is_organizer = await cur.fetchone()
            if not is_organizer:
                await interaction.followup.send(
                    "You can only start the campaign if you are the organizer!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                    ephemeral=True,
                )
                return

            # only continue if the campaign is in the awaiting state
            await cur.execute(
                "SELECT state FROM Campaigns WHERE guild_id = %s;",
                (interaction.guild.id,),
            )
            state = await cur.fetchone()
            if state[0] != "awaiting":
                await interaction.followup.send(
                    "The campaign is not in the awaiting state!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                    ephemeral=True,
                )
                return

            await cur.execute(
                "UPDATE Campaigns SET state = 'started' WHERE guild_id = %s;",
                (interaction.guild.id,),
            )

            await interaction.channel.send(
                "The Secret Santa campaign has started! Check your DMs for your giftee!",
            )

            assignments = secret_santa_algo(members)

            for giver, receiver in assignments:
                await create_santa_assignment(cur, interaction.guild.id, giver, receiver)

            logger.debug("Secret Santa assignments:")
            [
                logger.debug(
                    f"\t{(await bot.fetch_user(a[0])).global_name} -> {(await bot.fetch_user(a[1])).global_name}"
                )
                for a in assignments
            ]

            for giver, receiver in assignments:
                try:
                    user = await bot.fetch_user(giver)
                    giftee = await bot.fetch_user(receiver)
                    await user.send(
                        f"Your Secret Santa assignment is: {giftee.mention} ({giftee.global_name}). You can message them anonymously with `/santa message <message>`.",
                    )
                    logger.debug(f"Sent message to {user.id} ({user.global_name})")
                except Exception as e:
                    logger.error(f"Could not send message to user:\n{e}")
                sleep(0.5)
