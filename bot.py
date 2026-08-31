import os
import discord
from discord.ext import commands

# Configuration from environment variables
TOKEN = os.environ["DISCORD_TOKEN"]
LOG_CHANNEL_ID = int(os.environ["LOG_CHANNEL_ID"])
TRUSTED_ROLE_ID = int(os.environ["TRUSTED_ROLE_ID"])

intents = discord.Intents.default()
intents.guilds = True
intents.invites = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Thresholds
MAX_USES = int(os.environ["MAX_USES"])
MAX_EXPIRY = int(os.environ["MAX_EXPIRY"])  # 7 days in seconds

# Store invites per guild
guild_invites = {}

# Track invites deleted by bot to prevent double logging
deleted_by_bot = set()


async def log(message):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    print(message)
    if channel:
        await channel.send(message)


#rewritten to fix User/Member inconsistency
async def is_trusted(inviter, guild):

    if not inviter:
        return False

    member = guild.get_member(inviter.id) #uses local cache, maintained continuiosly by lib based on events

    if member is None:
        try:
            member = await guild.fetch_member(inviter.id)
        except discord.NotFound:
            print(f"failed to fetch member, {inviter=}")
            return False

    return any(role.id == TRUSTED_ROLE_ID for role in member.roles)


async def enforce_invite_limits(invite, warn=True):
    delete_reason = None

    if invite.max_uses is None or invite.max_uses > MAX_USES:
        delete_reason = (
            f"Max uses {invite.max_uses} exceeds limit of {MAX_USES}"
        )

    if invite.max_uses == 0:
        delete_reason = f"Max uses ∞ exceeds limit of {MAX_USES}"

    if invite.max_age is None or invite.max_age > MAX_EXPIRY:
        if delete_reason:
            delete_reason += " and "
        else:
            delete_reason = ""

        delete_reason += (
            f"Max age {invite.max_age} seconds exceeds "
            f"limit of {MAX_EXPIRY} seconds"
        )

    if invite.max_age == 0:
        if delete_reason:
            delete_reason += " and "
        else:
            delete_reason = ""

        delete_reason += (
            f"Max age ∞ seconds exceeds "
            f"limit of {MAX_EXPIRY} seconds"
        )

    if delete_reason:
        creator = invite.inviter

        if await is_trusted(creator, invite.guild):
            # Trusted role: only send a warning
            if warn:
                try:
                    await creator.send(
                        f"⚠️ WARNING: Your invite `{invite.code}` in "
                        f"'{invite.guild.name}' violates the recommended "
                        f"limits ({delete_reason}), but it will not be deleted "
                        f"because you have the trusted role."
                    )
                except discord.Forbidden:
                    pass

             #avoid spamming admins 
            await log(
                    f"⚠️ WARNING: Trusted user {creator} created invite "
                    f"`{invite.code}` violating limits: {delete_reason}"
            )

            return False  # Do not delete

        else:
            # Normal user: delete invite and send DM
            deleted_by_bot.add(invite.code)
            await invite.delete()


            if creator:
                try:
                    await creator.send(
                        f"❌ Your invite `{invite.code}` in "
                        f"'{invite.guild.name}' was deleted because: "
                        f"{delete_reason}"
                    )
                except discord.Forbidden:
                    pass

            await log(
                f"❌ DELETED: Invite `{invite.code}` by {creator} "
                f"deleted: {delete_reason}"
            )

            return True  # Invite deleted

    return False  # Invite okay


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # Cache current invites and enforce limits at startup
    for guild in bot.guilds:
        guild_invites[guild.id] = await guild.invites()

        for invite in list(guild_invites[guild.id]):
            await enforce_invite_limits(invite, warn=False)

    await log("Bot Restarted:Invite cache reinitialized and limits enforced.")


@bot.event
async def on_invite_create(invite):
    deleted = await enforce_invite_limits(invite)

    if not deleted:
        guild_invites.setdefault(invite.guild.id, []).append(invite)

        await log(
            f"✅ CREATED: Invite `{invite.code}` created by "
            f"{invite.inviter} (max uses: {invite.max_uses}, "
            f"max age: {invite.max_age}s)"
        )


@bot.event
async def on_invite_delete(invite):
    if invite.code in deleted_by_bot:
        deleted_by_bot.remove(invite.code)
        return

    await log(
        f"❌ DELETED: Invite `{invite.code}` by "
        f"{invite.inviter} was deleted."
    )

    # Remove from cache
    if invite.guild.id in guild_invites:
        guild_invites[invite.guild.id] = [
            i
            for i in guild_invites[invite.guild.id]
            if i.code != invite.code
        ]


@bot.event
async def on_member_join(member):
    guild = member.guild

    invites_before = guild_invites.get(guild.id, [])
    invites_after = await guild.invites()

    guild_invites[guild.id] = invites_after

    invites_after_dict = {
        i.code: i for i in invites_after
    }

    used_invite = None

    for before in invites_before:
        after = invites_after_dict.get(before.code)

        if after and after.uses > before.uses:
            used_invite = after
            break

    if used_invite:
        inviter = used_invite.inviter

        await log(
            f"👤 JOIN: {member} joined using invite "
            f"`{used_invite.code}` created by {inviter}."
        )

        try:
            await inviter.send(
                f"{member} joined the server using your invite "
                f"`{used_invite.code}`!"
            )
        except discord.Forbidden:
            pass

    else:
        await log(
            f"👤 JOIN: {member} joined, but the used invite "
            f"could not be determined."
        )

    # Track temporary/new members
    if member.pending or not member.roles:
        await log(
            f"⚠️ TEMP MEMBER: {member} joined as a temporary/new "
            f"member. Monitor for potential spam or drive-by accounts."
        )


bot.run(TOKEN)