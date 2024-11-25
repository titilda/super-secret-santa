import discord
import discord.ext.commands
import psycopg.errors
import asyncio
from psycopg import AsyncCursor
from random import shuffle

import constants
from config import config
from database import get_connection, connection_pool

# TODO: manage graceful shutdown of the bot
# from signal import signal, SIGINT


async def create_santa_assignment(cur: AsyncCursor, guild_id: int, user_id: int, giftee_id: int):
    await cur.execute(
        """INSERT INTO Giftees (user_id, guild_id) VALUES (%s, %s);""",
        (giftee_id, guild_id),
    )
    await cur.execute(
        """UPDATE Memberships SET giftee = (select id from Giftees where user_id = %s) WHERE user_id = %s AND guild_id = %s;""",
        (giftee_id, user_id, guild_id),
    )

    bot.get_user(user_id).send(
        f"Your Secret Santa assignment is: {bot.get_user(giftee_id).mention()}. You can message them with `/santa message <message>`.",
    )


class CampaignView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)  # persistent

    @discord.ui.button(label="Join Secret Santa!", custom_id="join-sss", style=discord.ButtonStyle.primary, emoji="🎅")
    async def join_button_callback(self, button, interaction: discord.Interaction):
        async with get_connection() as conn:
            try:
                cur = conn.cursor()
                await cur.advisory_lock(interaction.guild.id)
                try:
                    await cur.execute(
                        "INSERT INTO Memberships (user_id, guild_id) VALUES (%s, %s);",
                        (interaction.user.id, interaction.guild.id),
                    )
                except psycopg.errors.ForeignKeyViolation:
                    await interaction.response.send_message(
                        "There is no Secret Santa campaign on this server. You may create one with `/santa create <name>`.",
                        ephemeral=True,
                        delete_after=constants.DELETE_AFTER_DELAY,
                    )
                    return
            except psycopg.errors.UniqueViolation:
                await interaction.response.send_message(
                    "You have already joined the **Secret Santa campaign!**",
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

        await interaction.response.send_message(
            "You have joined the **Secret Santa campaign!**", ephemeral=True, delete_after=constants.DELETE_AFTER_DELAY
        )
        print(f"User {interaction.user.nick} joined the campaign {interaction.message.id}")

    @discord.ui.button(
        label="Leave Secret Santa!", custom_id="leave-sss", style=discord.ButtonStyle.danger, emoji="🎄"
    )
    async def leave_button_callback(self, button, interaction: discord.Interaction):
        async with get_connection() as conn:
            # if the user is the organizer, they cannot leave
            cur = conn.cursor()
            await cur.advisory_lock(interaction.guild.id)
            await cur.execute(
                "SELECT is_organizer FROM Memberships WHERE user_id = %s AND guild_id = %s;",
                (interaction.user.id, interaction.guild.id),
            )
            is_organizer = await cur.fetchone()
            if is_organizer:
                await interaction.response.send_message(
                    "You are the organizer. To delete the campaign, use /santa delete",
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

            # if the campaign is already started, the user cannot leave
            await cur.execute(
                "SELECT state FROM Campaigns WHERE guild_id = %s;",
                (interaction.guild.id,),
            )
            state = await cur.fetchone()
            if state == "started":
                await interaction.response.send_message(
                    "The campaign has already started. You cannot leave now.",
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

            await cur.execute(
                "DELETE FROM Memberships WHERE user_id = %s AND guild_id = %s RETURNING *;",
                (interaction.user.id, interaction.guild.id),
            )

            result = await cur.fetchone()

            await interaction.response.send_message(
                (
                    "You have left the **Secret Santa campaign!**"
                    if result
                    else "You are not part of a campaign on this server!"
                ),
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )

    @discord.ui.button(
        label="Start Secret Santa!", custom_id="start-sss", style=discord.ButtonStyle.success, emoji="🎁"
    )
    async def start_button_callback(self, button, interaction: discord.Interaction):
        async with get_connection() as conn:
            cur: AsyncCursor = conn.cursor()
            await cur.advisory_lock(interaction.guild.id)

            await cur.execute(
                "SELECT user_id FROM Memberships WHERE guild_id = %s;",
                (interaction.guild.id,),
            )
            members = await cur.fetchall()

            if len(members) < 3:
                if len(members) == 0:
                    error_message = "No members have joined a campaign or none exists!"
                else:
                    error_message = "You need at least 3 members to start the Secret Santa campaign!"
                await interaction.response.send_message(
                    error_message,
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

            # only continue if the user is the organizer
            await cur.execute(
                "SELECT is_organizer FROM Memberships WHERE user_id = %s AND guild_id = %s;",
                (interaction.user.id, interaction.guild.id),
            )

            is_organizer = await cur.fetchone()
            if not is_organizer:
                await interaction.response.send_message(
                    "You can only start the campaign if you are the organizer!",
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

            # only continue if the campaign is in the awaiting state
            await cur.execute(
                "SELECT state FROM Campaigns WHERE guild_id = %s;",
                (interaction.guild.id,),
            )
            state = await cur.fetchone()
            if state != "awaiting":
                await interaction.response.send_message(
                    "The campaign is not in the awaiting state!",
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

            await cur.execute(
                "UPDATE Campaigns SET state = 'started' WHERE guild_id = %s;",
                (interaction.guild.id,),
            )

            await interaction.response.send_message(
                "The Secret Santa campaign has started! Check your DMs for your giftee!",
                ephemeral=False,
            )

            await cur.execute(
                "SELECT user_id FROM Memberships WHERE guild_id = %s;",
                (interaction.guild.id,),
            )

            members = await cur.fetchall()
            people = members.copy()
            shuffle(members)

            i = len(members) - 2
            while i > 0:
                giver = (people.pop(-1)[0],)
                receiver = (members.pop(-1)[0],)

                if giver == receiver:
                    people.insert(-1, giver)
                    members.insert(0, receiver)
                    continue

                await create_santa_assignment(cur, interaction.guild.id, giver[0], receiver[0])

                i -= 1

            # last two people remaining:

            if members[0] == people[0] or members[1] == people[1]:
                # swap
                members[0], members[1] = members[1], members[0]

            await asyncio.gather(
                create_santa_assignment(cur, interaction.guild.id, members[0][0], people[0][0]),
                create_santa_assignment(cur, interaction.guild.id, members[1][0], people[1][0]),
            )


bot = discord.Bot()

santa_command_group = bot.create_group("santa", "Secret Santa commands")


@santa_command_group.command()
async def create(ctx: discord.ext.commands.Context, campaign_name: str):
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

            await ctx.respond(
                f"Super Secret Santa campaign: **{campaign_name}**\nStarted by {ctx.author.mention}!",
                view=CampaignView(),
            )

        except psycopg.errors.UniqueViolation:
            await ctx.respond(
                "There is already a campaign on this server!",
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )
            return


@santa_command_group.command()
async def delete(ctx: discord.ext.commands.Context):
    async with get_connection() as conn:
        cur = conn.cursor()
        await cur.advisory_lock(ctx.guild.id)
        await cur.execute(
            "SELECT is_organizer FROM Memberships WHERE user_id = %s AND guild_id = %s;",
            (ctx.author.id, ctx.guild.id),
        )
        is_organizer = await cur.fetchone()
        if not is_organizer:
            await ctx.respond(
                "You can only delete campaigns you have organized!",
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )
            return

        await cur.execute(
            "DELETE FROM Campaigns WHERE guild_id = %s;",
            (ctx.guild.id,),
        )  # cascade delete of Memberships

    await ctx.respond(
        "The campaign has been deleted!",
        ephemeral=True,
        delete_after=constants.DELETE_AFTER_DELAY,
    )


@santa_command_group.command()
async def message(ctx: discord.ext.commands.Context, message: str):
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
                await ctx.respond(
                    "You are not part of any started campaigns!",
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return
            case 1:
                campaign = campaigns[0]
            case _:
                message_to_send = "Please select one of the campaigns to send the message to with /santa messagex <number> <message>:\n"
                for number, campaign in enumerate(campaigns, start=1):
                    message_to_send += f"{number}. {campaign[2]} ({bot.get_user(campaign[1]).mention()})\n"
                ctx.respond(
                    message_to_send,
                    ephemeral=True,
                    delete_after=constants.DELETE_AFTER_DELAY,
                )
                return

        await ctx.send(
            f"Sending message to {bot.get_user(campaign[1].mention)} in the campaign **{campaign[2]}**...",
            ephemeral=True,
        )

        # send the message to the user
        user = bot.get_user(campaign[1])
        try:
            await user.send(f"Your Secret Santa in campaign **{campaign[2]}** has sent you a message:\n{message}")
            ctx.respond(
                "Message sent successfully!",
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )
        except Exception:
            ctx.respond(
                "Message could not be sent!",
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )


# TODO: merge message and messagex
@santa_command_group.command()
async def messagex(ctx: discord.ext.commands.Context, number: int, message: str):
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
            await ctx.respond(
                "Invalid number!",
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )
            return

        await ctx.send(
            f"Sending message to {bot.get_user(campaign[1].mention)} in the campaign **{campaign[2]}**...",
            ephemeral=False,
        )

        # send the message to the user
        user = bot.get_user(campaign[1])
        try:
            await user.send(f"Your Secret Santa in campaign **{campaign[2]}** has sent you a message:\n{message}")
            ctx.respond(
                "Message sent successfully!",
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )
        except Exception:
            ctx.respond(
                "Message could not be sent!",
                ephemeral=True,
                delete_after=constants.DELETE_AFTER_DELAY,
            )


@bot.event
async def on_ready():
    await connection_pool.open()
    bot.add_view(CampaignView())
    print(
        f"We have logged in as {bot.user}. "
        "Add to your server: "
        "https://discord.com/oauth2/authorize?"
        f"client_id={bot.user.id}"
        "&scope={constants.REQUIRED_SCOPES}"
        f"&permissions={constants.REQUIRED_PERMISSIONS}"
        "\n--------------------------------------------------\n"
    )


if __name__ == "__main__":
    bot.run(config.get("Discord", "token"))