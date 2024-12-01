import psycopg.errors
from discord.commands.context import ApplicationContext
from loguru import logger
from datetime import datetime

from . import constants
from .bot import bot
from .views import CampaignView
from .database import get_connection


def setup():
    santa_command_group = bot.create_group("santa", "Secret Santa commands")

    @santa_command_group.command()
    async def create(ctx: ApplicationContext, campaign_name: str):
        await ctx.defer(ephemeral=True)
        """Create a new Secret Santa campaign"""
        if not ctx.guild:
            await ctx.followup.send(
                "This command can only be used in a server!",
                delete_after=constants.DELETE_AFTER_DELAY,
            )
            return
        async with get_connection() as conn:
            cur = conn.cursor()
            try:
                await cur.advisory_lock(ctx.guild.id)
                await cur.execute(
                    """
                    INSERT INTO Campaigns (guild_id, name)
                    VALUES (%s, %s);
                    """,
                    (
                        ctx.guild.id,
                        campaign_name,
                    ),
                )

                await cur.execute(
                    """
                    INSERT INTO Memberships (user_id, guild_id, is_organizer)
                    VALUES (%s, %s, TRUE);
                    """,
                    (
                        ctx.author.id,
                        ctx.guild.id,
                    ),
                )

                await ctx.channel.send(
                    f"Super Secret Santa campaign: **{campaign_name}**\nCreated by {ctx.author.mention}!",
                    view=CampaignView(),
                )
                logger.info(f"User {ctx.author.global_name} created the campaign {campaign_name}")

            except psycopg.errors.UniqueViolation:
                await ctx.followup.send(
                    "There is already a campaign on this server!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

    @santa_command_group.command()
    async def delete(ctx: ApplicationContext):
        """Delete the current Secret Santa campaign on the server"""
        await ctx.defer(ephemeral=True)
        if not ctx.guild:
            await ctx.followup.send(
                "This command can only be used in a server!",
                delete_after=constants.DELETE_AFTER_DELAY,
            )
            return
        async with get_connection() as conn:
            cur = conn.cursor()
            await cur.advisory_lock(ctx.guild.id)
            await cur.execute(
                "SELECT is_organizer FROM Memberships WHERE user_id = %s AND guild_id = %s AND is_organizer = TRUE;",
                (ctx.author.id, ctx.guild.id),
            )
            is_organizer = await cur.fetchone()
            if not is_organizer:
                await ctx.followup.send(
                    "You can only delete campaigns you have organized!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

            await cur.execute(
                "DELETE FROM Campaigns WHERE guild_id = %s;",
                (ctx.guild.id,),
            )  # cascade delete of Memberships

        await ctx.followup.send(
            "The campaign has been deleted!",
            delete_after=constants.DELETE_AFTER_DELAY,
        )
        logger.info(f"User {ctx.author.global_name} deleted the campaign")

    @santa_command_group.command()
    async def message(ctx: ApplicationContext, message: str):
        """Send a message to your giftee, whom you must get a gift for (NOT your Secret Santa)"""
        await ctx.defer(ephemeral=True)
        # we need to find out all started campaigns the Member is part of, where `giftee` is not NULL
        async with get_connection() as conn:
            cur = conn.cursor()
            await cur.execute(
                """
                SELECT m.guild_id, g.user_id, c.name
                FROM Memberships m
                INNER JOIN Giftees g ON m.giftee = g.id AND g.user_id IS NOT NULL
                INNER JOIN Campaigns c ON m.guild_id = c.guild_id AND c.state = 'started'
                WHERE m.user_id = %s;
                """,
                (ctx.author.id,),
            )

            campaigns = await cur.fetchall()
            match len(campaigns):
                case 0:
                    await ctx.followup.send(
                        "You are not part of any started campaigns!",
                        delete_after=constants.DELETE_AFTER_DELAY,
                    )
                    return
                case 1:
                    campaign = campaigns[0]
                case _:
                    message_to_send = "Please select one of the campaigns to send the message to with `/santa messagex <number> <message>`:\n"
                    for number, campaign in enumerate(campaigns, start=1):
                        message_to_send += f"{number}. {campaign[2]} ({(await bot.fetch_user(campaign[1])).mention})\n"
                    ctx.followup.send(
                        message_to_send,
                        delete_after=constants.DELETE_AFTER_DELAY,
                    )
                    return

            await ctx.followup.send(
                f"Sending message to {((await bot.fetch_user(campaign[1])).mention)} in the campaign **{campaign[2]}**...",
            )

            # send the message to the user
            user = await bot.fetch_user(campaign[1])
            try:
                await user.send(f"Your Secret Santa in campaign **{campaign[2]}** has sent you a message:\n{message}")
                await ctx.followup.send(
                    "Message sent successfully!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                logger.debug(f"Sent message to {user.id} ({user.global_name})")
            except Exception:
                ctx.followup.send(
                    "Message could not be sent!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )

    # TODO: merge message and messagex
    @santa_command_group.command()
    async def messagex(ctx: ApplicationContext, number: int, message: str):
        """Send a message to your giftee, whom you must get a gift for (NOT your Secret Santa)"""
        await ctx.defer(ephemeral=True)
        # we need to find out all started campaigns the Member is part of, where `giftee` is not NULL
        async with get_connection() as conn:
            cur = conn.cursor()
            await cur.execute(
                """
                SELECT m.guild_id, g.user_id, c.name
                FROM Memberships m
                INNER JOIN Giftees g ON m.giftee = g.id AND g.user_id IS NOT NULL
                INNER JOIN Campaigns c ON m.guild_id = c.guild_id AND c.state = 'started'
                WHERE m.user_id = %s;
                """,
                (ctx.author.id,),
            )

            campaigns = await cur.fetchall()
            try:
                campaign = campaigns[number - 1]
            except IndexError:
                await ctx.followup.send(
                    "Invalid number!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

            await ctx.followup.send(
                f"Sending message to {((await bot.fetch_user(campaign[1])).mention)} in the campaign **{campaign[2]}**...",
                delete_after=constants.DELETE_AFTER_DELAY,
            )

            # send the message to the user
            user = await bot.fetch_user(campaign[1])
            try:
                await user.send(
                    f"Your Secret Santa in campaign **{campaign[2]}** has sent you a message:\n{message.upper()}"
                )
                await ctx.followup.send(
                    "Message sent successfully!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                logger.debug(f"Sent message to {user.id} ({user.global_name})")

            except Exception:
                await ctx.followup.send(
                    "Message could not be sent!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )

    @santa_command_group.command()
    async def list(ctx: ApplicationContext):
        """List all members of the campaign"""
        await ctx.defer(ephemeral=True)
        if not ctx.guild:
            await ctx.followup.send(
                "This command can only be used in a server!",
                delete_after=constants.DELETE_AFTER_DELAY,
            )
            return

        async with get_connection() as conn:
            time_code = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.cursor()
            await cur.execute(
                """
                SELECT user_id
                FROM Memberships
                WHERE guild_id = %s;
                """,
                (ctx.guild.id,),
            )
            members = await cur.fetchall()

            if not members:
                await ctx.followup.send(
                    "There are no members in the campaign!",
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                # This should not really happen
                return

            message = f"Members of the campaign as of {time_code}:\n"

            guild_members = [(await ctx.guild.fetch_member(member[0])) for member in members]

            member_names = sorted(
                (member.nick if member.nick else member.global_name if member.global_name else "Unknown member")
                for member in guild_members
            )

            message += "\n".join([f"* {name}" for name in member_names])

            await ctx.followup.send(message, delete_after=None)  # (this takes longer to read than other messages)

    @santa_command_group.command()
    async def status(ctx: ApplicationContext):
        """Show the bot status on the channel"""
        await ctx.respond("Showing statistics now...")
        server_count = len(bot.guilds)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await ctx.channel.send(
            f"Bot is currently running on {server_count} server{"" if server_count == 1 else "s"}\nCurrent time: {current_time}",
        )
