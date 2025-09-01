# PaciBot est un bot discord open-source codé en Python avec la librairie discord.py
# PaciBot est un bot de modération et de gestion de serveur discord. 
# Version: 1.7.0
# Auteur: Pacifique
# © 2021 PaciBot
# Licence: GPL-3.0
# Ce bot est sous licence GPL-3.0, ce qui signifie que vous pouvez le modifier et le redistribuer, mais vous devez conserver la même licence.
# Pour toute question ou suggestion, n'hésitez pas à me contacter sur discord: 2p2x#0 Id: 579041797918162975

# Importation des modules
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from dotenv import load_dotenv
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Union
from discord import HTTPException
import aiohttp
import requests
import time
import logging
import random

# Configuration du bot
intents = discord.Intents.default()
intents.members = True  
intents.messages = True  
intents.guilds = True    
intents.message_content = True

bot = commands.Bot(command_prefix='+', intents=intents)
tree = bot.tree 
bot.remove_command('help')

# Chargement des données et variables globales
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WARNINGS_FILE = os.path.join(BASE_DIR,'warnings.json')
MUTED_HISTORY_FILE = os.path.join(BASE_DIR,'muted_history.json')
MUTED_USERS_FILE = os.path.join(BASE_DIR,'muted_users.json')
BLACKLIST_FILE = os.path.join(BASE_DIR,'blacklist.json')
BLACKLISTRANK_FILE = os.path.join(BASE_DIR,'blacklistrank.json')
STATE_FILE = os.path.join(BASE_DIR,'channel_states.json')
ROLES_FILE = os.path.join(BASE_DIR, "roles.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
MUTED_ROLES_FILE = os.path.join(BASE_DIR, "muted_roles.json")
MUTED_USERS_FILE = os.path.join(BASE_DIR, "muted_users.json")
CANTUSE_FILE = os.path.join(BASE_DIR, "cantuse.json")

if os.path.exists(ROLES_FILE):
    with open(ROLES_FILE, "r") as f:
        data = json.load(f)
else:
    data = {}
    with open(ROLES_FILE, "w") as f:
        json.dump(data, f, indent=4)

GUILD_ID = 1133819185856786506
ADMINCHANNEL_ID = 1133826290152116327
AUTH_ROLE_ID = 1133829112419594311
MEMBERSCHANNEL_ID = 1300567053974900767

roles_autorisesperm = data.get("roles_autorisesperm", [])
roles_autoriseswarn = data.get("roles_autoriseswarn", [])
roles_autorisesremovesanction = data.get("roles_autorisesremovesanction", [])
roles_autorisesmute = data.get("roles_autorisesmute", [])
roles_autorises_roles = data.get("roles_autorises_roles", [])
roles_autorisesmove = data.get("roles_autorisesmove", [])
roles_autorises_renew = data.get("roles_autorises_renew", [])
roles_autorises_clear = data.get("roles_autorises_clear", [])
roles_autorises_lock = data.get("roles_autorises_lock", [])
roles_autorisesbl = data.get("roles_autorisesbl", [])
roles_autorisesblrank = data.get("roles_autorisesblrank", [])
roles_autorises_cm = data.get("roles_autorises_cm", [])
roles_autorises_anim = data.get("roles_autorises_anim", [])
ROLES_AUTORISES_COMMU = data.get("ROLES_AUTORISES_COMMU", [])
ROLES_AUTORISES_ANIMATION = data.get("ROLES_AUTORISES_ANIMATION", [])
ROLES_AUTORISESPING = {
    "cm": ROLES_AUTORISES_COMMU,
    "anim": ROLES_AUTORISES_ANIMATION
}

approved_members = {}

if not os.path.exists(CANTUSE_FILE):
    with open(CANTUSE_FILE, "w") as f:
        json.dump({"idsinterdits": []}, f)

with open(CANTUSE_FILE, "r") as f:
    data = json.load(f)
idscantuse = [int(id_) for id_ in data.get("idsinterdits", [])]

# Structure du démarrage sécurisé du bot

@bot.check
async def block_cantuse(ctx):
    return ctx.author.id not in idscantuse

load_dotenv()

async def main():
    token = os.getenv("TOKEN")
    if not token:
        raise ValueError("Il n'y a pas de TOKEN dans les variables d'environnement.")
    await check_rate_limit()
    await login_with_retry(bot, token)
    
async def login_with_retry(bot, token, retries=5, delay=5):
    for _ in range(retries):
        try:
            await bot.start(token)
            break
        except HTTPException as e:
            if e.status == 429:
                print(f"Rate limited. Waiting {delay} seconds before retrying...")
                await check_rate_limit()
                await asyncio.sleep(delay)
                delay *= 2
            else:
                raise

async def check_rate_limit():
    url = "https://discord.com/api/v9/your-endpoint"
    headers = {
        "Authorization": f"Bot {os.getenv('TOKEN')}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 429:
                retry_after = response.headers.get('Retry-After')
                print(f"Rate limited. Retry after: {retry_after} seconds")
            else:
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                rate_limit_reset = response.headers.get('X-RateLimit-Reset')
                rate_limit_reset_after = response.headers.get('X-RateLimit-Reset-After')
                
                if rate_limit_remaining is not None and rate_limit_reset is not None:
                    reset_time = int(rate_limit_reset)
                    current_time = time.time()
                    time_until_reset = reset_time - current_time
                    
                    print(f"Rate limit remaining: {rate_limit_remaining}")
                    print(f"Time until reset: {time_until_reset:.2f} seconds")
                elif rate_limit_reset_after is not None:
                    print(f"Rate limit remaining: {rate_limit_remaining}")
                    print(f"Time until reset: {rate_limit_reset_after} seconds")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@bot.event
async def on_ready():
    logging.info(f"Bot connecté en tant que {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="+help"))
    await bot.tree.sync()
    await update_member_count()
    await check_and_ban_blacklisted_members()
    print("membres actualisés")


# Définition des fonctions
async def check_and_ban_blacklisted_members():
    """Vérifie les membres présents dans le serveur et bannit ceux qui sont dans la blacklist."""
    guild = bot.get_guild(GUILD_ID)
    admin_channel = bot.get_channel(ADMINCHANNEL_ID)

    if not guild:
        logging.warning("Serveur non trouvé lors de la vérification de la blacklist.")
        return

    if not admin_channel:
        logging.warning(f"Salon admin (ID: {ADMINCHANNEL_ID}) introuvable.")
    
    blacklist_ids = set(blacklist.get("blacklist", []))
    for member in guild.members:
        if str(member.id) in blacklist_ids:
            try:
                await guild.ban(member, reason="Membre dans la blacklist détecté au démarrage du bot.")
                logging.info(f"Banni automatiquement : {member} (ID: {member.id}) car présent dans la blacklist.")

                if admin_channel:
                    await admin_channel.send(f"🚫 **{member}** (`{member.id}`) a été automatiquement banni car présent dans la blacklist.")
            except discord.Forbidden:
                logging.warning(f"Permissions insuffisantes pour bannir {member} (ID: {member.id})")
                if admin_channel:
                    await admin_channel.send(f"⚠️ Impossible de bannir **{member}** (`{member.id}`) : permissions insuffisantes.")
            except Exception as e:
                logging.error(f"Erreur lors du bannissement de {member} (ID: {member.id}) : {e}")
                if admin_channel:
                    await admin_channel.send(f"❌ Erreur lors du bannissement de **{member}** (`{member.id}`) : `{e}`")

class JSONManager:
    @staticmethod
    def load(filename):
        """
        Charge les données depuis un fichier JSON.
        Retourne un dictionnaire vide si le fichier est introuvable ou corrompu.
        """
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save(data, filename, indent=4):
        """
        Sauvegarde les données dans un fichier JSON.
        Ajoute une indentation par défaut pour rendre le fichier lisible.
        """
        with open(filename, 'w') as file:
            json.dump(data, file, indent=indent)

def load_channel_states():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = {"state": value, "permissions": {}}  
                return data
            except json.JSONDecodeError:
                return {}
    else:
        return {}

def save_channel_states(states):
    with open(STATE_FILE, 'w') as f:
        json.dump(states, f, indent=4)

async def fetch_all_members(guild):
    members = []
    try:
        async for member in guild.fetch_members(limit=None):
            members.append(member)
    except Exception as e:
        print(f"Erreur lors de la récupération des membres : {e}")
    return members

async def update_member_count():
    try:
        guild = bot.get_guild(GUILD_ID)
        if guild is None:
            print(f"La guilde avec l'ID {GUILD_ID} n'a pas été trouvée.")
            return
        
        members = await fetch_all_members(guild)
        total_member_count = len(members)
        
        channel = bot.get_channel(MEMBERSCHANNEL_ID)
        if channel is None:
            print(f"Le salon avec l'ID {MEMBERSCHANNEL_ID} n'a pas été trouvé.")
            return
        
        new_channel_name = f"📈 ・Membres : {total_member_count}"
        await channel.edit(name=new_channel_name)
    except Exception as e:
        print(f"Erreur lors de la mise à jour du nombre de membres : {e}")

def load_blacklist():
    try:
        with open(BLACKLIST_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def is_member_blacklisted(member_id):
    blacklist = load_blacklist()
    return member_id in blacklist

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            if "allowed_ids" not in data:
                data["allowed_ids"] = []
            return data
    except FileNotFoundError:
        return {"allowed_ids": []} 

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_muted_roles():
    with open(MUTED_ROLES_FILE, "w") as f:
        json.dump(muted_roles_backup, f)

def load_muted_roles():
    global muted_roles_backup
    if os.path.exists(MUTED_ROLES_FILE):
        with open(MUTED_ROLES_FILE, "r") as f:
            try:
                muted_roles_backup = json.load(f)
            except json.JSONDecodeError:
                muted_roles_backup = {}
    else:
        muted_roles_backup = {}

def save_muted_users():
    with open(MUTED_USERS_FILE, "w") as f:
        json.dump(muted_users, f)

def load_muted_users():
    global muted_users
    if os.path.exists(MUTED_USERS_FILE):
        with open(MUTED_USERS_FILE, "r") as f:
            try:
                muted_users = json.load(f)
            except json.JSONDecodeError:
                muted_users = {}
    else:
        muted_users = {}

load_muted_users()

def save_muted_history():
    """Sauvegarde l'historique des mutes"""
    with open(MUTED_HISTORY_FILE, "w") as f:
        json.dump(muted_history, f)

def load_muted_history():
    """Charge l'historique des mutes"""
    global muted_history
    if os.path.exists(MUTED_HISTORY_FILE):
        with open(MUTED_HISTORY_FILE, "r") as f:
            try:
                muted_history = json.load(f)
            except json.JSONDecodeError:
                muted_history = {}
    else:
        muted_history = {}

load_muted_history()

def initialize_data():
    global blacklist, warnings, muted_history, muted_users, blacklist_rank
    blacklist = JSONManager.load(BLACKLIST_FILE)
    warnings = JSONManager.load(WARNINGS_FILE)
    muted_history = JSONManager.load(MUTED_HISTORY_FILE)
    muted_users = JSONManager.load(MUTED_USERS_FILE)
    blacklist_rank = JSONManager.load(BLACKLISTRANK_FILE)
    ids_interdits = JSONManager.load(CANTUSE_FILE)

initialize_data()

# Evenements

@bot.event
async def on_member_join(member):
    if is_member_blacklisted(member.id):
        await member.ban(reason="Membre dans la blacklist.")
    await update_member_count()

@bot.event
async def on_member_remove(member):
    await update_member_count()

@bot.event
async def on_member_update(before, after):
    await handle_admin_roles(before, after)
    await handle_blacklist_roles(after)

async def handle_admin_roles(before, after):
    global approved_members
    if len(before.roles) < len(after.roles):
        new_roles = set(after.roles) - set(before.roles)
        for role in new_roles:
            if role.permissions.administrator:
                if approved_members.get(after.id) == role.id:
                    del approved_members[after.id]
                    return

                await after.remove_roles(role)
                channel = bot.get_channel(ADMINCHANNEL_ID)
                auth_role_mention = f'<@&{AUTH_ROLE_ID}>'
                message_content = (
                    f'{after.mention} tente de se faire attribuer le rôle {role.name} avec des permissions administrateur. '
                    f'Un membre avec le rôle {auth_role_mention} doit approuver cette action.\n'
                    'Cliquez sur ✅ pour approuver cette attribution.'
                )
                message = await channel.send(message_content)
                await message.add_reaction('✅')

                def check(reaction, user):
                    return (
                        user.id != bot.user.id
                        and reaction.message.id == message.id
                        and str(reaction.emoji) == '✅'
                    )

                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    await channel.send("⏰ Temps écoulé. L'attribution du rôle a été annulée.")
                    return

                is_authorized = (
                    AUTH_ROLE_ID in [role.id for role in user.roles]
                    or user.id == 579041797918162975
                )

                if is_authorized:
                    approved_members[after.id] = role.id
                    await after.add_roles(role)
                    await channel.send(
                        f'L\'attribution du rôle {role.name} à {after.mention} a été approuvée par {user.mention}.'
                    )
                else:
                    await channel.send(
                        f'{user.mention} n\'a pas la permission d\'autoriser cette attribution.'
                    )

async def handle_blacklist_roles(after):
    try:
        if str(after.id) in blacklist_rank['listbl_rank']:
            roles_interdits = [role for role in after.roles if role.id in roles_autorisesperm]
            if roles_interdits:
                await after.remove_roles(*roles_interdits)
                channel = after.guild.get_channel(ADMINCHANNEL_ID)
                if channel:
                    await channel.send(
                        f"{after.mention} avait des rôles interdits qui ont été retirés : "
                        f"{', '.join(role.name for role in roles_interdits)}."
                    )
    except Exception as e:
        print(f"Erreur lors de la mise à jour du membre : {e}")

def parse_duration(text: str) -> timedelta:
    """
    Parse une durée du type '1h30', '2j', '15min' en timedelta.
    """
    regex = r"(?:(\d+)\s*j)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*(?:m|min))?"
    match = re.match(regex, text.strip().lower())
    if not match:
        return None

    jours = int(match.group(1)) if match.group(1) else 0
    heures = int(match.group(2)) if match.group(2) else 0
    minutes = int(match.group(3)) if match.group(3) else 0

    return timedelta(days=jours, hours=heures, minutes=minutes)

muted_roles_backup = {}

#   Commandes
# Commande d'aide

async def send_help(destination, author):
    try:
        
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_author(name='Liste des commandes')
        embed.add_field(name="**+bot**", value="Prise en main du bot", inline=False)
        embed.add_field(name="**+help**", value="Affiche la liste des commandes disponibles.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorises_cm for role in author.roles) or any(role.id in roles_autorises_anim for role in author.roles):
            embed.add_field(name="**+ping <ID>**", value="Mentionne un rôle précis.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorisesremovesanction for role in author.roles):
            embed.add_field(name="**+warn <ID> <raison>**", value="Avertit un(e) utilisateur/trice pour un mauvais comportement.", inline=False)
            embed.add_field(name="**+sanction <ID>**", value="Affiche l'historique des sanctions d'un(e) utilisateur/trice.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorisesmute for role in author.roles):
            embed.add_field(name="**+tempmute <ID> <temps en chiffres>m <raison>**", value="Empêche temporairement un membre de parler dans les salons de communauté.", inline=False)
            embed.add_field(name="**+unmute <ID>**", value="Permet de demute sans attendre le temps restant en mentionnant la personne mute ou en écrivant son ID.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorises_roles for role in author.roles):
            embed.add_field(name="**+addrole <ID> <Role1> (<Role2>) (<Role3>)**", value="Ajoute un ou plusieurs rôles à un(e) membre.", inline=False)
            embed.add_field(name="**+removerole <ID> <Role1> (<Role2>) (<Role3>)**", value="Supprime un ou plusieurs rôles d'un(e) membre.", inline=False)
            embed.add_field(name="**+remove_sanction <ID> <mute/warn> <numéro>**", value="Supprime une des sanctions d'un(e) utilisateur/trice.", inline=False)
            embed.add_field(name="**+rename <ID ou Mention ou self> <Nouveau Nom>**", value="Renomme l'utilisateur/trice. Spécifier un(e) utilisateur/trice pour le/la renommer.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorises_renew for role in author.roles):
            embed.add_field(name="**+renew**", value="Recrée le salon dans lequel la commande est exécutée avec les mêmes paramètres.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorises_lock for role in author.roles):
            embed.add_field(name="**+lock**", value="Verrouille le salon dans lequel la commande est exécutée. Ré-exécuter pour déverrouiller.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorisesblrank for role in author.roles):
            embed.add_field(name="**+bl_rank <ID>**", value="Interdit à un membre d'avoir des rôles staffs.", inline=False)
            embed.add_field(name="**+unbl_rank <ID>**", value="Retire un membre de la bl_rank.", inline=False)
            embed.add_field(name="**+info_blrank <ID>**", value="Vérifie si un membre est dans la blacklist rank. Exécuter sans ID pour l'afficher.", inline=False)
       
        if author.guild_permissions.administrator or any(role.id in roles_autorisesmove for role in author.roles):
            embed.add_field(name="**+move <ID de vocal> <ID ou mention> (<ID ou mention>) (<ID ou mention>)**", value="Déplace un ou plusieurs utilisateurs dans un salon vocal. Spécifier un ID de vocal pour déplacer dans le vocal correspondant.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorises_clear for role in author.roles):
            embed.add_field(name="**+clear <Nombre> (<ID ou Mention>)**", value="Supprime un nombre de messages spécifique. Exécuter en spécifiant un membre pour supprimer les messages de celui-ci.", inline=False)
        
        if author.guild_permissions.administrator or any(role.id in roles_autorisesbl for role in author.roles):
            embed.add_field(name="**+bl <ID>**", value="Ajoute un membre à la blacklist.", inline=False)
            embed.add_field(name="**+unbl <ID>**", value="Retire un membre de la blacklist.", inline=False)
            embed.add_field(name="**+info_bl <ID>**", value="Vérifie si un membre est dans la blacklist. Exécuter sans ID pour l'afficher.", inline=False)
        
        embed.add_field(name="**Commandes Slash**", value="Actives pour la plupart des commandes (Soon)", inline=False)
        embed.add_field(name="**Légende :**", value="() : Facultatif, <> : Argument", inline=False)

        if isinstance(destination, discord.Interaction):  
            await destination.response.send_message(embed=embed, ephemeral=True)  
        else:
            await destination.send(embed=embed)
    except discord.Forbidden:
        await destination.send("Je n'ai pas la permission d'envoyer des messages.")
    except Exception as e:
        await destination.send(f"Une erreur est survenue : {e}")

@bot.command()
async def help(ctx):
    await send_help(ctx, ctx.author)

@tree.command(name="help", description="Affiche la liste des commandes disponibles")
async def help_slash(interaction: discord.Interaction):
    await send_help(interaction, interaction.user)

@bot.command(name="bot")
async def bot_status(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="Statut du bot",
        description="🟢 Le bot est en ligne !",
        color=discord.Color.green()
    )
    embed.add_field(name="📶 Latence", value=f"`{latency} ms`", inline=False)
    await ctx.send(embed=embed)

@bot.tree.command(name="bot", description="Affiche si le bot est en ligne et sa latence.")
async def bot_status_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="Statut du bot",
        description="🟢 Le bot est en ligne !",
        color=discord.Color.green()
    )
    embed.add_field(name="📶 Latence", value=f"`{latency} ms`", inline=False)
    await interaction.response.send_message(embed=embed)

# Gestion des membres
# Blacklist

@bot.command(aliases=["feet"])
async def kick(ctx, member: discord.Member, *, reason=None):
    if not (any(role.name in roles_autorisesbl for role in ctx.author.roles) or ctx.author.guild_permissions.administrator):
        return await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande.")

    if ctx.guild.me.top_role <= member.top_role:
        return await ctx.send("❌ Je ne peux pas kicker cette personne (son rôle est trop haut).")

    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ {member.mention} a été kick. Raison : {reason or 'Aucune'}")
    except discord.Forbidden:
        await ctx.send("❌ Je n'ai pas la permission de kicker ce membre.")
    except Exception as e:
        await ctx.send(f"❌ Une erreur est survenue : {e}")

def has_bl_permission(user: discord.Member) -> bool:
    """Vérifie si l'utilisateur a la permission de gérer la blacklist."""
    return user.guild_permissions.administrator or any(role.id in roles_autorisesbl for role in user.roles)

async def add_to_blacklist(member_id: int) -> str:
    """Ajoute un membre à la blacklist et tente de le bannir."""
    member_id_str = str(member_id)
    if member_id_str in blacklist.get("blacklist", []):
        return f"Le membre avec l'ID {member_id} est déjà dans la blacklist."

    blacklist.setdefault("blacklist", []).append(member_id_str)
    JSONManager.save(blacklist, BLACKLIST_FILE)

    guild = bot.get_guild(GUILD_ID)
    if guild:
        try:
            member = await bot.fetch_user(member_id)
            await guild.ban(member, reason="Membre ajouté à la blacklist.")
            return f"Le membre avec l'ID {member_id} a été ajouté à la blacklist et banni.\n||https://cdn.discordapp.com/attachments/1198284633255719082/1398087764624277525/you_are_banned_retro.mp4?ex=68841632&is=6882c4b2&hm=56a7e31afe4b64f726346246372d6c225062c28e26ef0fcb63273d39bc50e393&||"
        except discord.NotFound:
            return f"Impossible de trouver le membre avec l'ID {member_id}. Ajouté à la blacklist mais non banni."
        

    return f"Le membre avec l'ID {member_id} a été ajouté à la blacklist."

async def remove_from_blacklist(member_id: int) -> str:
    """Retire un membre de la blacklist et tente de le débannir."""
    member_id_str = str(member_id)
    if member_id_str not in blacklist.get("blacklist", []):
        return f"Le membre avec l'ID {member_id} n'est pas dans la blacklist."

    blacklist["blacklist"].remove(member_id_str)
    JSONManager.save(blacklist, BLACKLIST_FILE)

    guild = bot.get_guild(GUILD_ID)
    if guild:
        try:
            ban_entry = await guild.fetch_ban(discord.Object(id=member_id))
            await guild.unban(ban_entry.user)
            return f"Le membre avec l'ID {member_id} a été retiré de la blacklist et débanni."
        except discord.NotFound:
            return f"Le membre avec l'ID {member_id} n'est pas banni, mais a été retiré de la blacklist."

    return f"Le membre avec l'ID {member_id} a été retiré de la blacklist."

async def is_blacklisted(member_id: int = None) -> str:
    """Retourne la liste des membres dans la blacklist ou vérifie un membre spécifique."""
    if member_id is None:
        bl_list = blacklist.get("blacklist", [])
        return "Liste des membres dans la blacklist :\n" + "\n".join(f"<@{m}>" for m in bl_list) if bl_list else "La blacklist est vide."
    
    return f"Le membre avec l'ID {member_id} est dans la blacklist." if str(member_id) in blacklist.get("blacklist", []) else f"Le membre avec l'ID {member_id} n'est pas dans la blacklist."

@bot.command(aliases=["skibidiban"])
async def bl(ctx, member_id: int):
    if not has_bl_permission(ctx.author):
        return await ctx.send("Vous n'avez pas la permission nécessaire pour utiliser cette commande.")
    
    message = await add_to_blacklist(member_id)
    await ctx.send(message)

@tree.command(name="bl", description="Ajoute un membre à la blacklist et le bannit.")
@app_commands.describe(member_id="ID du membre à ajouter à la blacklist")
async def bl_slash(interaction: discord.Interaction, member_id: int):
    if not has_bl_permission(interaction.user):
        return await interaction.response.send_message("Vous n'avez pas la permission nécessaire pour utiliser cette commande.", ephemeral=True)

    message = await add_to_blacklist(member_id)
    await interaction.response.send_message(message, ephemeral=True)

@bot.command(aliases=["unskibidi"])
async def unbl(ctx, member_id: int):
    if not has_bl_permission(ctx.author):
        return await ctx.send("Vous n'avez pas la permission nécessaire pour utiliser cette commande.")
    
    message = await remove_from_blacklist(member_id)
    await ctx.send(message)

@tree.command(name="unbl", description="Retire un membre de la blacklist et le débannit.")
@app_commands.describe(member_id="ID du membre à retirer de la blacklist")
async def unbl_slash(interaction: discord.Interaction, member_id: int):
    if not has_bl_permission(interaction.user):
        return await interaction.response.send_message("Vous n'avez pas la permission nécessaire pour utiliser cette commande.", ephemeral=True)

    message = await remove_from_blacklist(member_id)
    await interaction.response.send_message(message, ephemeral=True)

@bot.command()
async def info_bl(ctx, member_id: int = None):
    if not has_bl_permission(ctx.author):
        return await ctx.send("Vous n'avez pas la permission nécessaire pour utiliser cette commande.")
    
    message = await is_blacklisted(member_id)
    await ctx.send(message)

@tree.command(name="info_bl", description="Affiche la liste des membres dans la blacklist ou vérifie un ID.")
@app_commands.describe(member_id="ID du membre à vérifier (laisser vide pour afficher toute la blacklist)")
async def info_bl_slash(interaction: discord.Interaction, member_id: int = None):
    if not has_bl_permission(interaction.user):
        return await interaction.response.send_message("Vous n'avez pas la permission nécessaire pour utiliser cette commande.", ephemeral=True)

    message = await is_blacklisted(member_id)
    await interaction.response.send_message(message, ephemeral=True)

# Blacklist rank

async def has_permission_blrank(ctx):
    """Vérifie si l'utilisateur a les permissions nécessaires."""
    return ctx.author.guild_permissions.administrator or any(role.id in roles_autorisesblrank for role in ctx.author.roles)

async def manage_blacklist_rank(ctx, member_id: int, action: str):
    """Ajoute ou supprime un membre de la blacklist rank."""
    if not await has_permission_blrank(ctx):
        return await ctx.send("🚫 Vous n'avez pas la permission nécessaire.")

    member_id_str = str(member_id)
    member = ctx.guild.get_member(member_id)

    if action == "add":
        if member_id_str in blacklist_rank['listbl_rank']:
            return await ctx.send(f"⚠️ Le membre <@{member_id}> est déjà dans la blacklist rank.")

        blacklist_rank['listbl_rank'].append(member_id_str)
        JSONManager.save(blacklist_rank, BLACKLISTRANK_FILE)
        await ctx.send(f"✅ Le membre <@{member_id}> a été ajouté à la blacklist rank.")

        if member:
            roles_interdits = [role for role in member.roles if role.id in roles_autorisesperm]
            if roles_interdits:
                await member.remove_roles(*roles_interdits)
                await ctx.send(f"🔻 Rôles interdits retirés de {member.mention}.")
    else:
        if member_id_str not in blacklist_rank['listbl_rank']:
            return await ctx.send(f"⚠️ Le membre <@{member_id}> n'est pas dans la blacklist rank.")

        blacklist_rank['listbl_rank'].remove(member_id_str)
        JSONManager.save(blacklist_rank, BLACKLISTRANK_FILE)
        await ctx.send(f"✅ Le membre <@{member_id}> a été retiré de la blacklist rank.")

# Commandes classiques
@bot.command()
async def bl_rank(ctx, member_id: int):
    """Ajoute un membre à la blacklist rank."""
    await manage_blacklist_rank(ctx, member_id, "add")

@bot.command()
async def unbl_rank(ctx, member_id: int):
    """Retire un membre de la blacklist rank."""
    await manage_blacklist_rank(ctx, member_id, "remove")

@bot.command()
async def info_blrank(ctx, member_id: int = None):
    """Affiche les membres de la blacklist rank ou vérifie un membre spécifique."""
    if not await has_permission_blrank(ctx):
        return await ctx.send("🚫 Vous n'avez pas la permission nécessaire.")

    if member_id:
        if str(member_id) in blacklist_rank['listbl_rank']:
            await ctx.send(f"✅ Le membre <@{member_id}> est dans la blacklist rank.")
        else:
            await ctx.send(f"⚠️ Le membre <@{member_id}> n'est pas dans la blacklist rank.")
    else:
        if not blacklist_rank['listbl_rank']:
            return await ctx.send("ℹ️ La blacklist rank est vide.")

        chunks = ["📋 **Liste des membres dans la blacklist rank :**\n"]
        for member in blacklist_rank['listbl_rank']:
            chunks[-1] += f"• <@{member}>\n"
            if len(chunks[-1]) > 1900:
                chunks.append("")

        for chunk in chunks:
            await ctx.send(chunk)

# Commandes Slash
@bot.tree.command(name="bl_rank", description="Ajoute un membre à la blacklist rank.")
@app_commands.describe(member="Membre à ajouter à la blacklist")
async def bl_rank_slash(interaction: discord.Interaction, member: discord.Member):
    await manage_blacklist_rank(interaction, member.id, "add")

@bot.tree.command(name="unbl_rank", description="Retire un membre de la blacklist rank.")
@app_commands.describe(member="Membre à retirer de la blacklist")
async def unbl_rank_slash(interaction: discord.Interaction, member: discord.Member):
    await manage_blacklist_rank(interaction, member.id, "remove")

@bot.tree.command(name="info_blrank", description="Affiche les membres de la blacklist rank.")
@app_commands.describe(member="Membre à vérifier (optionnel)")
async def info_blrank_slash(interaction: discord.Interaction, member: discord.Member = None):
    await info_blrank(interaction, member.id if member else None)

# Commandes de gestion des rôles

def get_role(ctx, role_arg):
    if role_arg.isdigit():
        return discord.utils.get(ctx.guild.roles, id=int(role_arg))
    elif role_arg.startswith("<@&") and role_arg.endswith(">"):
        return discord.utils.get(ctx.guild.roles, id=int(role_arg[3:-1]))
    else:
        return discord.utils.get(ctx.guild.roles, name=role_arg)

def has_permission_roles(ctx):
    return ctx.author.guild_permissions.administrator or any(role.id in roles_autorises_roles for role in ctx.author.roles)

async def manage_role(ctx, member, roles, action):
    if not has_permission_roles(ctx):
        await ctx.send("Vous n'avez pas la permission nécessaire pour utiliser cette commande.")
        return

    for role_arg in roles:
        role = get_role(ctx, role_arg)
        if role is None:
            await ctx.send(f"Le rôle '{role_arg}' n'a pas été trouvé.")
            continue

        if member.id in blacklist_rank['listbl_rank'] and role.id in roles_autorisesperm:
            await ctx.send(f"Le rôle '{role.name}' est interdit pour les membres de la blacklist rank.")
            continue

        if role.position > ctx.author.top_role.position:
            await ctx.send(f"Vous ne pouvez pas modifier le rôle {role.name} car il est supérieur à votre propre rôle.")
            continue

        try:
            if action == "add":
                await member.add_roles(role)
                await ctx.send(f"{member.mention} a reçu le rôle {role.name}.")
            elif action == "remove":
                await member.remove_roles(role)
                await ctx.send(f"{member.mention} n'a plus le rôle {role.name}.")
        except discord.Forbidden:
            await ctx.send("Je n'ai pas la permission nécessaire pour gérer les rôles.")
        except discord.HTTPException:
            await ctx.send("Une erreur s'est produite lors de la modification du rôle.")

@bot.command()
async def addrole(ctx, member: discord.Member, *roles):
    await manage_role(ctx, member, roles, "add")

@bot.command()
async def removerole(ctx, member: discord.Member, *roles):
    await manage_role(ctx, member, roles, "remove")

@app_commands.command(name="addrole", description="Ajoute un rôle à un membre")
@app_commands.describe(member="Membre à qui ajouter le rôle", roles="Rôle(s) à ajouter")
async def slash_addrole(interaction: discord.Interaction, member: discord.Member, roles: str):
    roles_list = roles.split()
    await manage_role(interaction, member, roles_list, "add")
    await interaction.response.send_message(f"Rôle(s) ajouté(s) à {member.mention}.", ephemeral=True)

@app_commands.command(name="removerole", description="Retire un rôle à un membre")
@app_commands.describe(member="Membre à qui retirer le rôle", roles="Rôle(s) à retirer")
async def slash_removerole(interaction: discord.Interaction, member: discord.Member, roles: str):
    roles_list = roles.split()
    await manage_role(interaction, member, roles_list, "remove")
    await interaction.response.send_message(f"Rôle(s) retiré(s) de {member.mention}.", ephemeral=True)

# Commandes de gestion des sanctions

async def get_or_create_muted_role(guild):
    muted_role = discord.utils.get(guild.roles, name="Muet")
    if muted_role is None:
        muted_role = await guild.create_role(name="Muet", reason="Création automatique pour mute temporaire")
        for channel in guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False)
    return muted_role

def has_permission(ctx, role_list):
    user = ctx.author if isinstance(ctx, commands.Context) else ctx.user  
    return user.guild_permissions.administrator or any(role.id in role_list for role in user.roles)

async def send_response(ctx, message=None, embed=None):
    """ Envoie une réponse sans erreur d'interaction expirée. """
    if isinstance(ctx, commands.Context):  
        if embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send(message)
    elif isinstance(ctx, discord.Interaction):  
        try:
            if ctx.response.is_done():  
                await ctx.followup.send(content=message, embed=embed if embed else None)
            else:
                await ctx.response.send_message(content=message, embed=embed if embed else None)
        except discord.NotFound:
            print("⚠️ Impossible d'envoyer un message : l'interaction n'existe plus.")

# Affichage des sanctions
@bot.command()
async def sanction(ctx, member: discord.Member):
    await show_sanctions(ctx, member)

@bot.tree.command(name="sanction", description="Affiche les sanctions d'un membre")
async def slash_sanction(interaction: discord.Interaction, member: discord.Member):
    await show_sanctions(interaction, member)

async def show_sanctions(ctx, member):
    if not has_permission(ctx, roles_autorisesremovesanction):
        await send_response(ctx, "🚫 Vous n'avez pas la permission nécessaire.")
        return
    
    warns = warnings.get(str(member.id), [])
    mute_history = muted_history.get(str(member.id), [])

    embed = discord.Embed(title=f"📌 Sanctions de {member.display_name}", color=discord.Color.blurple())
    
    warn_text = "\n".join([f"#{w['numéro']} - {w['time']} - {w['reason']}" for w in warns]) or "Aucun avertissement."
    mute_text = "\n".join([f"#{m['numéro']} - {m['time']} - {m['reason']}" for m in mute_history]) or "Aucun mute."
    
    embed.add_field(name="⚠️ Avertissements", value=warn_text, inline=False)
    embed.add_field(name="🔇 Mutes", value=mute_text, inline=False)
    
    await send_response(ctx, embed=embed)


# Retirer une sanction
@bot.command()
async def remove_sanction(ctx, member: discord.Member, sanction_type: str, sanction_number: int):
    await handle_remove_sanction(ctx, member, sanction_type, sanction_number)

@bot.tree.command(name="remove_sanction", description="Retire une sanction d'un membre")
async def slash_remove_sanction(interaction: discord.Interaction, member: discord.Member, sanction_type: str, sanction_number: int):
    await handle_remove_sanction(interaction, member, sanction_type, sanction_number)

async def handle_remove_sanction(ctx, member, sanction_type, sanction_number):
    if not has_permission(ctx, roles_autorisesremovesanction):
        await send_response(ctx, "🚫 Vous n'avez pas la permission nécessaire.")
        return
    
    data = warnings if sanction_type.lower() == "warn" else muted_history if sanction_type.lower() == "mute" else None
    if not data:
        await send_response(ctx, "❌ Type de sanction invalide. Utilisez 'warn' ou 'mute'.")
        return
    
    user_sanctions = data.get(str(member.id), [])
    updated_sanctions = [s for s in user_sanctions if s["numéro"] != sanction_number]
    
    if len(updated_sanctions) == len(user_sanctions):
        await send_response(ctx, f"⚠️ Aucune sanction trouvée avec ce numéro pour {member.mention}.")
        return
    
    data[str(member.id)] = updated_sanctions
    JSONManager.save(data, WARNINGS_FILE if sanction_type.lower() == "warn" else MUTED_HISTORY_FILE)
    await send_response(ctx, f"✅ Sanction {sanction_number} retirée pour {member.mention}.")

# Ajouter un avertissement
@bot.command()
async def warn(ctx, member: discord.Member, *, reason: str):
    await handle_warn(ctx, member, reason)

@bot.tree.command(name="warn", description="Ajoute un avertissement à un membre")
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    await handle_warn(interaction, member, reason)

async def handle_warn(ctx, member, reason):
    if not has_permission(ctx, roles_autoriseswarn):
        await send_response(ctx, "🚫 Vous n'avez pas la permission nécessaire.")
        return
    
    warnings.setdefault(str(member.id), []).append({
        "numéro": len(warnings[str(member.id)]) + 1,
        "reason": reason,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    JSONManager.save(warnings, WARNINGS_FILE)
    await send_response(ctx, f"⚠️ {member.mention} a été averti pour : {reason}.")

# Mute temporaire
@bot.command()
async def tempmute(ctx, member: discord.Member, time: str, *, reason: str):
    await handle_tempmute(ctx, member, time, reason)

@bot.tree.command(name="tempmute", description="Mute temporairement un membre")
async def slash_tempmute(interaction: discord.Interaction, member: discord.Member, time: str, reason: str):
    await handle_tempmute(interaction, member, time, reason)

async def handle_tempmute(ctx, member, duration_str, reason):
    global muted_users, muted_roles_backup

    if not isinstance(duration_str, str):
        await send_response(ctx, "❌ Durée invalide. Utilisez un format comme '10m', '1h', '2d'.")
        return

    time_match = re.match(r"(\d+)([smhd])", duration_str)
    if not time_match:
        await send_response(ctx, "❌ Format de durée invalide. Utilisez '10m', '1h', '2d'.")
        return

    if member.voice and member.voice.channel:
        try:
            await member.move_to(None)
            await send_response(ctx, f"🔇 {member.mention} a été déconnecté du vocal.")
        except discord.Forbidden:
            await send_response(ctx, f"❌ Je n'ai pas la permission de déconnecter {member.mention} du vocal.")
        except Exception as e:
            await send_response(ctx, f"⚠️ Erreur lors de la tentative de déconnexion de {member.mention} : {e}")

    amount, unit = time_match.groups()
    amount = int(amount)

    if unit == "s":
        delta = amount
    elif unit == "m":
        delta = amount * 60
    elif unit == "h":
        delta = amount * 3600
    elif unit == "d":
        delta = amount * 86400
    else:
        await send_response(ctx, "❌ Unité de temps invalide.")
        return

    end_time = int(time.time() + delta)  

    muted_roles_backup[str(member.id)] = [role.id for role in member.roles if role != ctx.guild.default_role]
    JSONManager.save(muted_roles_backup, MUTED_ROLES_FILE)

    muted_role = await get_or_create_muted_role(ctx.guild)
    await member.edit(roles=[muted_role])
    
    muted_users[str(member.id)] = {"end_time": end_time, "reason": reason}
    JSONManager.save(muted_users, MUTED_USERS_FILE)

    mute_number = len(muted_history.get(str(member.id), [])) + 1
    if str(member.id) not in muted_history:
        muted_history[str(member.id)] = []
    muted_history[str(member.id)].append({
        "numéro": mute_number,
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "reason": reason
    })
    JSONManager.save(muted_history, MUTED_HISTORY_FILE)

    await send_response(ctx, f"🔇 {member.mention} a été mute pour {duration_str}.")
    
    await asyncio.sleep(delta)
    
    await handle_unmute(ctx, member)

# Unmute
@bot.command()
async def unmute(ctx, member: discord.Member):
    await handle_unmute(ctx, member)

@bot.tree.command(name="unmute", description="Démute un membre")
async def slash_unmute(interaction: discord.Interaction, member: discord.Member):
    await handle_unmute(interaction, member)

async def handle_unmute(ctx, member):
    global muted_users, muted_roles_backup

    muted_role = await get_or_create_muted_role(ctx.guild)

    roles_a_restaurer = [ctx.guild.get_role(role_id) for role_id in muted_roles_backup.get(str(member.id), [])]

    muted_users.pop(str(member.id), None)
    muted_roles_backup.pop(str(member.id), None)

    JSONManager.save(muted_users, MUTED_USERS_FILE)
    JSONManager.save(muted_roles_backup, MUTED_ROLES_FILE)

    await member.edit(roles=[r for r in roles_a_restaurer if r is not None], reason="Fin du mute.")
    await send_response(ctx, f"✅ {member.mention} a été unmute et ses rôles ont été restaurés.")

# Commandes de gestion des salons

async def has_move_permission(ctx_or_interaction):
    """Vérifie si l'utilisateur a la permission de déplacer des membres."""
    user = ctx_or_interaction.author if isinstance(ctx_or_interaction, commands.Context) else ctx_or_interaction.user
    return user.guild_permissions.administrator or any(role.id in roles_autorisesmove for role in user.roles)


async def send_message(ctx, message):
    """Gère l'envoi de messages pour les commandes normales et slash."""
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(message, ephemeral=True)
    else:
        await ctx.send(message)

async def move_members(ctx, target_channel, members):
    """Déplace une liste de membres vers un salon vocal."""
    if target_channel is None or not isinstance(target_channel, discord.VoiceChannel):
        await send_message(ctx, "Salon vocal invalide.")
        return

    if not target_channel.permissions_for(ctx.guild.me).move_members:
        await send_message(ctx, "Je n'ai pas la permission de déplacer des membres ici.")
        return

    members_to_move = []
    for member_str in members:
        try:
            member_id = int(re.sub(r"\D", "", member_str)) 
            member = ctx.guild.get_member(member_id)
            if member and member.voice and member.voice.channel:
                members_to_move.append(member)
            else:
                await send_message(ctx, f"{member_str} n'est pas connecté à un salon vocal.")
        except ValueError:
            await send_message(ctx, f"Argument invalide : `{member_str}`")

    for member in members_to_move:
        try:
            await member.move_to(target_channel)
            await send_message(ctx, f"{member.mention} a été déplacé vers {target_channel.name}.")
        except discord.Forbidden:
            await send_message(ctx, f"Je n'ai pas la permission de déplacer {member.mention}.")
        except discord.HTTPException as e:
            await send_message(ctx, f"Erreur lors du déplacement de {member.mention} : {e}")

@bot.command()
async def move(ctx, target_channel: str, *members):
    if not await has_move_permission(ctx):
        await ctx.send("Vous n'avez pas la permission nécessaire.")
        return

    if ctx.author.voice is None:
        await ctx.send("Vous devez être dans un salon vocal pour utiliser cette commande.")
        return

    if target_channel.lower() == "here":
        target_channel = ctx.author.voice.channel
    else:
        try:
            channel_id = int(target_channel)
            target_channel = bot.get_channel(channel_id)
        except ValueError:
            await ctx.send("Argument invalide pour l'ID du salon vocal.")
            return

    await move_members(ctx, target_channel, members)

@bot.tree.command(name="move", description="Déplace des membres vers un salon vocal")
async def slash_move(interaction: discord.Interaction, target_channel: discord.VoiceChannel, members: str):
    if not await has_move_permission(interaction):
        await interaction.response.send_message("Vous n'avez pas la permission nécessaire.", ephemeral=True)
        return

    members_list = members.split() 
    await move_members(interaction, target_channel, members_list)

@bot.command()
async def genmove(ctx, channel_id: int):
    if ctx.author.guild_permissions.administrator:
        genmovechannel = bot.get_channel(channel_id)

        if not isinstance(genmovechannel, discord.VoiceChannel):
            await ctx.send("L'ID fourni ne correspond pas à un salon vocal.")
            return
        
        for guild in bot.guilds:
            for voice_channel in guild.voice_channels:
                for member in voice_channel.members:
                    try:
                        await member.move_to(genmovechannel)
                        await ctx.send(f'{member.name} a été déplacé vers {genmovechannel.name}')
                    except discord.Forbidden:
                        await ctx.send(f'Permission refusée pour déplacer {member.name}.')
                    except discord.HTTPException as e:
                        await ctx.send(f'Erreur HTTP lors du déplacement de {member.name}: {e}')

        await ctx.send('Tous les utilisateurs ont été déplacés.')
    else:
        await ctx.send("Vous n'avez pas la permission nécessaire pour utiliser cette commande.")

@bot.command()
async def renew(ctx):
    if any(role.id in roles_autorises_renew for role in ctx.author.roles) or ctx.author.guild_permissions.administrator:
        try:
            channel = ctx.channel
            channel_name = channel.name
            channel_category = channel.category
            channel_position = channel.position
            channel_permissions = channel.overwrites

            new_channel = await channel.clone(name=channel_name, reason="Channel renewal")

            await new_channel.edit(category=channel_category, position=channel_position)

            for role, overwrite in channel_permissions.items():
                await new_channel.set_permissions(role, overwrite=overwrite)

            await channel.delete(reason="Channel renewal")

            await new_channel.send(f"Ce salon a été renouvelé par {ctx.author.mention}")
        except discord.Forbidden:
            await ctx.send("Je n'ai pas la permission nécessaire pour gérer ce salon.")
        except discord.HTTPException as e:
            await ctx.send(f"Une erreur s'est produite lors du renouvellement du salon : {e}")
    else:
        await ctx.send("Vous n'avez pas la permission nécessaire pour utiliser cette commande.")

@bot.command(name="lock")
async def lock(ctx):
    await handle_lock(ctx, ctx.channel)

@bot.tree.command(name="lock", description="Verrouille ou déverrouille un salon")
async def slash_lock(interaction: discord.Interaction):
    await handle_lock(interaction, interaction.channel)

async def handle_lock(source, channel: discord.abc.GuildChannel):
    states = load_channel_states()
    channel_id = str(channel.id)

    def is_interaction(obj):
        return isinstance(obj, discord.Interaction)

    async def reply(msg):
        if is_interaction(source):
            await source.response.send_message(msg, ephemeral=True)
        else:
            await source.send(msg)

    if channel_id in states and states[channel_id]["state"] == "locked":
        if "permissions" in states[channel_id]:
            for role_id, saved_permission in states[channel_id]["permissions"].items():
                role = channel.guild.get_role(int(role_id))
                if role:
                    overwrite = channel.overwrites_for(role)
                    if isinstance(channel, discord.TextChannel):
                        overwrite.send_messages = saved_permission
                    elif isinstance(channel, discord.VoiceChannel):
                        overwrite.connect = saved_permission
                    await channel.set_permissions(role, overwrite=overwrite)

        states[channel_id] = {"state": "unlocked"}
        await reply(f"🔓 {channel.mention} a été déverrouillé.")

    else:
        role_permissions = {}
        for role in channel.overwrites:
            overwrite = channel.overwrites[role]

            if isinstance(channel, discord.TextChannel):
                if overwrite.send_messages is None or overwrite.send_messages is True:
                    role_permissions[str(role.id)] = overwrite.send_messages
                    overwrite.send_messages = False
                    await channel.set_permissions(role, overwrite=overwrite)

            elif isinstance(channel, discord.VoiceChannel):
                if overwrite.connect is None or overwrite.connect is True:
                    role_permissions[str(role.id)] = overwrite.connect
                    overwrite.connect = False
                    await channel.set_permissions(role, overwrite=overwrite)

        if isinstance(channel, discord.VoiceChannel):
            for member in channel.members:
                try:
                    await member.move_to(None)
                except discord.Forbidden:
                    pass
                except Exception as e:
                    print(f"Erreur en déconnexion vocale : {e}")

        states[channel_id] = {
            "state": "locked",
            "permissions": role_permissions
        }

        await reply(f"🔒 {channel.mention} a été verrouillé.")

    save_channel_states(states)

# Commandes de gestion des messages

async def handle_clear(ctx_or_interaction, amount: int, member: Union[discord.Member, int, None] = None, after_time: datetime = None):
    if isinstance(ctx_or_interaction, discord.Interaction):
        interaction = ctx_or_interaction
        await interaction.response.defer(ephemeral=True)
        author = interaction.user
        channel = interaction.channel
        async def send_response(msg): return await interaction.followup.send(msg, ephemeral=True)
    else:
        ctx = ctx_or_interaction
        author = ctx.author
        channel = ctx.channel
        async def send_response(msg): return await ctx.send(msg)

    if not (any(role.id in roles_autorises_clear for role in author.roles) or author.guild_permissions.administrator):
        return await send_response("❌ Permission insuffisante.")

    if not channel.permissions_for(channel.guild.me).manage_messages:
        return await send_response("❌ Je n'ai pas la permission de gérer les messages.")

    if amount < 1 or amount > 100:
        return await send_response("❌ Nombre invalide (1-100 messages max).")

    member_id = member.id if isinstance(member, discord.Member) else member if isinstance(member, int) else None

    def check(msg):
        if member_id is not None and msg.author.id != member_id:
            return False
        if after_time is not None and msg.created_at < after_time:
            return False
        return True

    try:
        deleted = await channel.purge(limit=amount, check=check, bulk=True)
        msg = await send_response(f"✅ {len(deleted)} messages supprimés.")
        if not isinstance(ctx_or_interaction, discord.Interaction):
            await msg.delete(delay=5)
    except discord.Forbidden:
        await send_response("❌ Permission refusée.")
    except discord.HTTPException as e:
        await send_response(f"❌ Erreur : {e}")

@bot.command(name='clear')
async def clear(ctx, amount: int, *args):
    member = None
    after_time = None

    for arg in args:
        if arg.startswith("<@") and arg.endswith(">"):
            try:
                member_id = int(re.sub(r"\D", "", arg))
                member = ctx.guild.get_member(member_id)
            except:
                pass
        elif arg.lower().startswith("depuis"):
            duration_text = arg.lower().replace("depuis", "").strip()
            delta = parse_duration(duration_text)
            if delta:
                after_time = datetime.now(timezone.utc) - delta

    await ctx.message.delete()
    await handle_clear(ctx, amount, member=member, after_time=after_time)

@bot.tree.command(name="clear", description="Supprime un nombre spécifié de messages.")
@app_commands.describe(amount="Nombre de messages à supprimer", member="Utilisateur ciblé (optionnel)", temps="Durée depuis laquelle supprimer (ex: 1h30, 2j)")
async def slash_clear(interaction: discord.Interaction, amount: int, member: discord.Member = None, temps: str = None):
    after_time = None
    if temps:
        delta = parse_duration(temps)
        if delta:
            after_time = datetime.now(timezone.utc) - delta

    await handle_clear(interaction, amount, member=member, after_time=after_time)

# Commandes utilitaires

async def rename_member(member: discord.Member, new_name: str, requester: discord.Member) -> str:
    """Renomme un membre et retourne un message de confirmation ou d'erreur."""
    if member != requester and not (requester.guild_permissions.administrator or any(role.id in roles_autorises_roles for role in requester.roles)):
        return "Vous n'avez pas la permission de renommer d'autres membres."

    try:
        await member.edit(nick=new_name)
        return f"{member.mention} a été renommé(e) en '{new_name}'." if new_name else f"{member.mention} a été réinitialisé à son nom par défaut."
    except discord.Forbidden:
        return "Je n'ai pas la permission de renommer des membres."
    except discord.HTTPException:
        return "Une erreur s'est produite lors du rename."

@bot.command()
async def rename(ctx, target: str, *, new_name: str = None):
    member = (
        ctx.author if target.lower() == "self"
        else ctx.guild.get_member(int(target)) if target.isdigit()
        else ctx.message.mentions[0] if ctx.message.mentions
        else None
    )

    if member is None:
        await ctx.send("Utilisateur non trouvé. Veuillez spécifier un ID valide, une mention ou 'self'.")
        return

    message = await rename_member(member, new_name, ctx.author)
    await ctx.send(message)

@tree.command(name="rename", description="Renomme un utilisateur.")
@app_commands.describe(target="Membre à renommer (laisser vide pour vous-même)", new_name="Nouveau nom (laisser vide pour réinitialiser)")
async def rename_slash(interaction: discord.Interaction, target: discord.Member = None, new_name: str = None):
    member = target or interaction.user
    message = await rename_member(member, new_name, interaction.user)
    await interaction.response.send_message(message, ephemeral=True)

async def get_ping_permission(user: discord.Member, role: discord.Role) -> str:
    if role.position > user.top_role.position:
        return f"Vous ne pouvez pas ping le rôle {role.name} car il est supérieur à votre propre rôle."

    for role_type, allowed_roles in ROLES_AUTORISESPING.items():
        if user.guild_permissions.administrator or any(r.id in roles_autorises_cm if role_type == "cm" else roles_autorises_anim for r in user.roles):
            if role.id in allowed_roles or user.guild_permissions.administrator:
                return role.mention
            return f"Vous ne pouvez pas ping le rôle {role.name}."

    return "Vous n'avez pas les permissions nécessaires pour utiliser cette commande."

@bot.command()
async def ping(ctx, role_input: str):
    """Permet de ping un rôle via ID ou mention."""
    role = None

    if role_input.startswith("<@&") and role_input.endswith(">"):
        role_id = role_input[3:-1]
    else:
        role_id = role_input

    try:
        role = ctx.guild.get_role(int(role_id))
        if role is None:
            return await ctx.send("Le rôle fourni n'existe pas.")
    except ValueError:
        return await ctx.send("L'entrée fournie n'est ni un ID valide ni une mention de rôle correcte.")

    message = await get_ping_permission(ctx.author, role)
    await ctx.send(message)

@tree.command(name="ping", description="Mentionne un rôle précis.")
@app_commands.describe(role="Rôle à mentionner (ID)")
async def ping_slash(interaction: discord.Interaction, role: discord.Role):
    message = await get_ping_permission(interaction.user, role)
    await interaction.response.send_message(message, ephemeral=False)

@bot.command()
async def config(ctx, action: str = None, categorie: str = None, role: discord.Role = None):
    config = load_config()

    if ctx.author.id not in config["allowed_ids"]:
        await ctx.send("Vous n'avez pas la permission d'utiliser cette commande.")
        return
    
    if action == "afficher":
        embed = discord.Embed(title="Configuration des Rôles", color=discord.Color.blue())
        for key, roles in data.items():
            role_mentions = [f"<@&{r}>" for r in roles]
            embed.add_field(name=key, value=", ".join(role_mentions) if role_mentions else "Aucun rôle", inline=False)
        await ctx.send(embed=embed)
    
    elif action in ["add", "remove"] and categorie and role:
        if categorie in data:
            if action == "add":
                if role.id not in data[categorie]:
                    data[categorie].append(role.id)
                    await ctx.send(f"Le rôle {role.mention} a été ajouté à {categorie}.")
                else:
                    await ctx.send("Ce rôle est déjà dans cette catégorie.")
            elif action == "remove":
                if role.id in data[categorie]:
                    data[categorie].remove(role.id)
                    await ctx.send(f"Le rôle {role.mention} a été retiré de {categorie}.")
                else:
                    await ctx.send("Ce rôle n'est pas dans cette catégorie.")
            with open(ROLES_FILE, "w") as f:
                json.dump(data, f, indent=4)
        else:
            await ctx.send("Catégorie invalide.")
    
    elif action in ["ajouter_id", "retirer_id","ids"]:
        if ctx.author.id == 579041797918162975:
            if action == "ajouter_id" and len(ctx.message.mentions) > 0:
                new_id = ctx.message.mentions[0].id
                if new_id not in config["allowed_ids"]:
                    config["allowed_ids"].append(new_id)
                    save_config(config) 
                    await ctx.send(f"L'ID {new_id} a été ajouté aux utilisateurs autorisés.")
                else:
                    await ctx.send("Cet utilisateur est déjà autorisé à utiliser cette commande.")
            
            
            elif action == "retirer_id" and len(ctx.message.mentions) > 0:
                remove_id = ctx.message.mentions[0].id
                if remove_id in config["allowed_ids"]:
                    config["allowed_ids"].remove(remove_id)
                    save_config(config)
                    await ctx.send(f"L'ID {remove_id} a été retiré des utilisateurs autorisés.")
                else:
                    await ctx.send("Cet utilisateur n'est pas dans la liste des autorisés.")

            elif action == "ids":
                embed = discord.Embed(title="🔹 Liste des Admins Autorisés", color=discord.Color.blue())
                members_mentions = [f"<@{str(member_id)}>" for member_id in config["allowed_ids"]]
                embed.description = ", ".join(members_mentions) if members_mentions else "Aucun membre autorisé."
                await ctx.send(embed=embed)
        else:
            await ctx.send("🚫 Vous n'avez pas la permission de voir ou modifier les IDs.")
            return
        
    else:
        await ctx.send("**Utilisation :**\n"
                       "`+config afficher` 📜 Voir la config\n"
                       "`+config add <categorie> @role` ➕ Ajouter un rôle\n"
                       "`+config remove <categorie> @role` ➖ Retirer un rôle\n")

#Gestion des erreurs

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure) and ctx.author.id in idscantuse:
        await ctx.send("Non Non Non la schizo pas de commandes pour toi.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Argument manquant. Veuillez fournir tous les arguments requis.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Argument invalide. Veuillez vérifier les arguments fournis.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"❌ Une erreur est survenue : {error.original}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
    else:
        await ctx.send("❌ Une erreur inconnue est survenue.")

@bot.command()
@commands.has_permissions(administrator=True)
async def gosier(ctx, *args):
    if len(args) < 2:
        await ctx.send("❗ Utilisation : `+gosier @membre1 [@membre2 ...] durée_en_secondes`")
        return

    try:
        duration = int(args[-1])
        members = [await commands.MemberConverter().convert(ctx, arg) for arg in args[:-1]]
    except Exception:
        await ctx.send("❗ Veuillez mentionner correctement les membres et donner une durée en secondes à la fin.")
        return

    original_channels = {}
    for member in members:
        if not member.voice or not member.voice.channel:
            await ctx.send(f"🚫 {member.display_name} n'est pas dans un salon vocal.")
            return
        original_channels[member] = member.voice.channel

    voice_channels = [
        ch for ch in ctx.guild.voice_channels
        if ch.permissions_for(ctx.guild.me).move_members
    ]
    random.shuffle(voice_channels)

    if not voice_channels:
        await ctx.send("❌ Aucun salon vocal disponible pour déplacer les membres.")
        return

    await ctx.send(f"🔁 Secouage du gosier de {len(members)} chenapan pendant {duration}s.")

    delay = duration / len(voice_channels)

    for channel in voice_channels:
        for member in members:
            try:
                await member.move_to(channel)
            except Exception as e:
                await ctx.send(f"⚠️ Erreur lors du déplacement de {member.display_name} : {e}")
        await asyncio.sleep(delay)

    for member in members:
        try:
            await member.move_to(original_channels[member])
        except Exception as e:
            await ctx.send(f"❌ Impossible de remettre {member.display_name} dans son salon d'origine : {e}")

    await ctx.send("✅ Gosiers secoués avec succès.")
    
@gosier.error
async def randommove_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Tu dois être administrateur pour utiliser cette commande.")
    else:
        await ctx.send(f"⚠️ Erreur : {error}")

#Commandes de démarrage

async def startup():
    await check_rate_limit()
    await main()

if __name__ == "__main__":
    asyncio.run(startup())