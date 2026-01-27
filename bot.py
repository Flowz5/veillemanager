import discord
from discord.ext import commands
import json
import os
import asyncio
import random
from datetime import timedelta
from dotenv import load_dotenv
import re
import mysql.connector
import csv
import subprocess

# Charge les variables d'environnement
load_dotenv()

# ==========================================
# ⚙️ CONFIGURATION & CONSTANTES
# ==========================================

# --- Sécurité ---
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERREUR : Token introuvable dans le .env")
    exit()
TOKEN = TOKEN.strip()

# --- IDs des Salons ---
CHANNEL_VEILLE_ID    = 1463268390436343808
CHANNEL_GENERAL_ID   = 1463268249738154119
CHANNEL_WELCOME_ID   = 1465122841753026560

# --- Gameplay & Rôles ---
ROLE_READER_NAME = "Reader"
EMOJI_VALIDATION = "✅"
XP_PER_CLICK     = 10
XP_PER_LEVEL     = 100

# --- Fichiers de données ---
DATA_FILE  = "xp_data.json"
WARNS_FILE = "warns.json"

# --- Liste des mots interdits ---
BAD_WORDS = [
    "merde", "putain", "con", "connard", "connasse", "salope", "pute", 
    "enculé", "encule", "bâtard", "batard", "salaud", "bouffon", "boloss",
    "abruti", "débile", "triso", "mongol", "gogol", "idiot",
    "tg", "ftg", "fdp", "ntm", "vtff", "ptn",
    "bite", "couille", "chatte", "nique", "niquer", "suce", "sucer", 
    "branleur", "branlette", "trou du cul", "foutre",
    "negro", "nègre", "negre", "bougnoule", "crouille", "youpin", "raton",
    "pd", "pédé", "pede", "tarlouze", "fiotte", "gouine", "travelo",
    "chinetoque", "bamboula", "sale noir", "sale arabe", "sale juif"
]

# ==========================================
# 🔧 INITIALISATION
# ==========================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

user_xp = {}

# ==========================================
# 💾 GESTION DES DONNÉES (JSON)
# ==========================================

def load_xp():
    """Charge l'XP depuis le JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_xp():
    """Sauvegarde l'XP."""
    with open(DATA_FILE, "w") as f:
        json.dump(user_xp, f)

def load_warns():
    """Charge les avertissements."""
    if os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_warns(warns):
    """Sauvegarde les avertissements."""
    with open(WARNS_FILE, "w") as f:
        json.dump(warns, f)

# ==========================================
# 🤖 ÉVÉNEMENTS
# ==========================================

@bot.event
async def on_ready():
    global user_xp
    user_xp = load_xp()
    print(f'✅ Bot connecté : {bot.user}')
    print(f'📊 XP chargée pour {len(user_xp)} utilisateurs.')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="du Lofi ☕"))

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name=ROLE_READER_NAME)
    if role:
        await member.add_roles(role)
    
    channel = bot.get_channel(CHANNEL_WELCOME_ID)
    if channel:
        await channel.send(f"Bienvenue {member.mention} ! 🎓\nTu as reçu le rôle **{ROLE_READER_NAME}**.")

@bot.event
async def on_message(message):
    # --- Auto-Modération (Regex & Censure) ---
    censored_content = message.content
    censored = False
    cartoon_symbols = "@#$!&%*+?"

    def generate_censure(match):
        nonlocal censored
        censored = True
        found_word = match.group()
        return "".join(random.choice(cartoon_symbols) for _ in range(len(found_word)))

    for word in BAD_WORDS:
        pattern = fr'\b{re.escape(word)}(?:e|s|es|x)?\b'
        censored_content = re.sub(pattern, generate_censure, censored_content, flags=re.IGNORECASE)

    if censored:
        await message.delete()
        await message.channel.send(f"📣 **{message.author.display_name}** a dit :\n>>> {censored_content}")
        warning = await message.channel.send(f"⚠️ {message.author.mention}, surveille ton langage !")
        await asyncio.sleep(5)
        await warning.delete()
        return

    await bot.process_commands(message)

    # --- Auto-Réaction Veille ---
    if message.channel.id == CHANNEL_VEILLE_ID and message.author.id != bot.user.id:
        try:
            await message.add_reaction(EMOJI_VALIDATION)
        except Exception:
            pass

@bot.event
async def on_raw_reaction_add(payload):
    # --- Système d'XP ---
    if payload.channel_id == CHANNEL_VEILLE_ID and str(payload.emoji) == EMOJI_VALIDATION:
        if payload.user_id == bot.user.id: return

        user_id = str(payload.user_id)
        current_xp = user_xp.get(user_id, 0)
        current_level = current_xp // XP_PER_LEVEL
        
        new_xp = current_xp + XP_PER_CLICK
        new_level = new_xp // XP_PER_LEVEL
        
        user_xp[user_id] = new_xp
        save_xp()
        
        if new_level > current_level:
            channel = bot.get_channel(CHANNEL_GENERAL_ID)
            if channel:
                member = bot.get_guild(payload.guild_id).get_member(payload.user_id)
                if member:
                     await channel.send(f"🎉 **LEVEL UP !** {member.mention} passe **Niveau {new_level}** ! 🧠")

# ==========================================
# ℹ️ COMMANDES : INFO & ADMIN
# ==========================================

@bot.command(name="help")
async def help_cmd(ctx):
    """Affiche le menu d'aide détaillé."""
    embed = discord.Embed(
        title="🛡️ Centre de Contrôle - Parabot",
        description="Liste des commandes disponibles.",
        color=0x2c3e50
    )
    
    # --- SECTION COMMUNICATION & ADMIN ---
    embed.add_field(
        name="📢 Communication & Admin",
        value=(
            "**`!announce <#salon> <Titre|Message>`** : Faire une annonce.\n"
            "**`!pull`** : 🔄 Lancer le scraper (Veille).\n"
            "**`!export`** : 💾 Télécharger la BDD (CSV).\n"
            "**`!regles`** : Affiche le règlement."
        ),
        inline=False
    )
    
    # --- SECTION MODÉRATION ---
    embed.add_field(
        name="⚖️ Modération & Sécurité",
        value=(
            "**`🛡️ Auto-Mod`** : Actif (Anti-Insultes).\n"
            "`!kick`, `!ban`, `!unban` : Sanctions.\n"
            "`!mute`, `!unmute` : Gérer le silence.\n"
            "`!lock`, `!unlock`, `!clear` : Gérer les salons.\n"
            "`!warn`, `!warns`, `!unwarn` : Avertissements."
        ),
        inline=False
    )

    # --- SECTION INFOS ---
    embed.add_field(
        name="🕵️‍♂️ Infos & Veille",
        value=(
            "`!userinfo @membre` : Fiche profil.\n"
            "`!serverinfo` : Stats du serveur.\n"
            "`!search <mot>` : 🔎 Chercher un article.\n"
            "`!news` : 📰 Les 5 derniers articles."
        ),
        inline=False
    )
    
    # --- SECTION FUN ---
    embed.add_field(
        name="🎭 Fun & XP",
        value=(
            "`!level`, `!top` : Voir son XP.\n"
            "`!poll <question>` : Sondage.\n"
            "`!8ball` : Jeux."
        ),
        inline=False
    )
    
    embed.set_footer(text=f"Version 2.2 • {ctx.guild.name}")
    
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"ℹ️ Infos : {guild.name}", color=0xf1c40f)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Membres", value=f"{guild.member_count}", inline=True)
    embed.add_field(name="Salons", value=f"{len(guild.channels)}", inline=True)
    embed.set_footer(text=f"ID: {guild.id}")
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed = discord.Embed(title=f"👤 {member.name}", color=member.color)
    if member.avatar: embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="Créé le", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Rôles", value=" ".join(roles) if roles else "Aucun", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="regles")
@commands.has_permissions(administrator=True)
async def regles(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="📜 RÈGLEMENT", description="1. Respect\n2. Pas de Spam\n3. Veille Tech uniquement ici", color=0xe74c3c)
    await ctx.send(embed=embed)

@bot.command(name="announce")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel, *, content: str):
    if "|" in content:
        title, text = content.split("|", 1)
    else:
        title, text = "📢 Annonce", content
    
    embed = discord.Embed(title=title.strip(), description=text.strip(), color=0xe74c3c)
    if ctx.guild.icon: embed.set_thumbnail(url=ctx.guild.icon.url)
    await channel.send(embed=embed)
    await ctx.send(f"✅ Annonce envoyée dans {channel.mention}.")

# ==========================================
# 🕵️‍♂️ COMMANDES : VEILLE & BDD
# ==========================================

@bot.command(name="pull")
@commands.has_permissions(administrator=True)
async def pull(ctx):
    """Lance le script de scraping externe."""
    status_msg = await ctx.send("🕵️‍♂️ **Lancement du Scraper...**")
    try:
        script_path = "/app/external_scraper/scraper.py"
        result = subprocess.run(["python", script_path], capture_output=True, text=True, check=True)
        await status_msg.edit(content=f"✅ **Terminé !**")
        if result.stdout:
            await ctx.send(f"📄 **Logs :**\n```{result.stdout[:1900]}```")
    except subprocess.CalledProcessError as e:
        await status_msg.edit(content=f"❌ **Crash du script !**")
        await ctx.send(f"⚠️ Erreur :\n```{e.stderr}```")
    except FileNotFoundError:
        await status_msg.edit(content="❌ Fichier `scraper.py` introuvable.")

@bot.command(name="search")
async def search_article(ctx, *, query: str):
    await ctx.send(f"🔎 Recherche de **'{query}'**...")
    try:
        conn = mysql.connector.connect(host="localhost", user="parabot", password="moncode123", database="veille_tech")
        cursor = conn.cursor()
        
        sql = "SELECT titre, lien FROM articles WHERE titre LIKE %s ORDER BY id DESC LIMIT 5"
        cursor.execute(sql, (f"%{query}%",))
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            await ctx.send("❌ Aucun résultat.")
            return
            
        embed = discord.Embed(title=f"🗃️ Résultats : {query}", color=0x3498db)
        for titre, lien in results:
            embed.add_field(name="📄 Article", value=f"[{titre}]({lien})", inline=False)
        await ctx.send(embed=embed)
    except mysql.connector.Error as err:
        await ctx.send(f"❌ Erreur SQL : `{err}`")

@bot.command(name="news")
async def latest_news(ctx):
    try:
        conn = mysql.connector.connect(host="localhost", user="parabot", password="moncode123", database="veille_tech")
        cursor = conn.cursor()
        cursor.execute("SELECT titre, lien, date FROM articles ORDER BY id DESC LIMIT 5")
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            await ctx.send("❌ Base vide.")
            return

        embed = discord.Embed(title="📰 Dernières News", color=0x2ecc71)
        for titre, lien, date in results:
            embed.add_field(name=f"📅 {date}", value=f"[{titre}]({lien})", inline=False)
        await ctx.send(embed=embed)
    except mysql.connector.Error as err:
        await ctx.send(f"❌ Erreur SQL : `{err}`")

@bot.command(name="export")
@commands.has_permissions(administrator=True)
async def export_db(ctx):
    await ctx.send("⏳ Génération du CSV...")
    filename = "export_veille.csv"
    try:
        conn = mysql.connector.connect(host="localhost", user="parabot", password="moncode123", database="veille_tech")
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, titre, lien, source FROM articles")
        rows = cursor.fetchall()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Date', 'Titre', 'Lien', 'Source']) 
            writer.writerows(rows)
        conn.close()
        
        await ctx.send(f"✅ Export de {len(rows)} articles :", file=discord.File(filename))
        os.remove(filename)
    except Exception as e:
        await ctx.send(f"❌ Erreur : `{e}`")

# ==========================================
# ⚖️ COMMANDES : MODÉRATION & WARNS
# ==========================================

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 {amount} messages supprimés.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 **{member.name}** expulsé.")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Aucune"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 **{member.name}** banni.")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_input):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if str(user.id) == user_input or f"{user.name}#{user.discriminator}" == user_input:
            await ctx.guild.unban(user)
            await ctx.send(f"✅ **{user.name}** débanni.")
            return
    await ctx.send("❌ Utilisateur introuvable.")

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int, *, reason="Comportement"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"🤐 **{member.name}** muet pour {minutes} min.")

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 **{member.name}** libéré.")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon ouvert.")

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="Aucune raison"):
    warns = load_warns()
    uid = str(member.id)
    if uid not in warns: warns[uid] = []
    
    timestamp = ctx.message.created_at.strftime("%d/%m/%Y %H:%M")
    warns[uid].append({"reason": reason, "date": timestamp, "mod": ctx.author.name})
    save_warns(warns)
    
    embed = discord.Embed(title="⚠️ Avertissement", description=f"{member.mention} a reçu un warn.", color=0xe67e22)
    embed.add_field(name="Raison", value=reason)
    embed.add_field(name="Total", value=f"{len(warns[uid])} avertissements")
    await ctx.send(embed=embed)

@bot.command(name="warns")
@commands.has_permissions(manage_messages=True)
async def list_warns(ctx, member: discord.Member):
    warns = load_warns()
    uid = str(member.id)
    if uid not in warns or not warns[uid]:
        await ctx.send(f"✅ **{member.display_name}** est clean.")
        return
        
    embed = discord.Embed(title=f"📂 Casier de {member.display_name}", color=0xe74c3c)
    for i, w in enumerate(warns[uid], 1):
        embed.add_field(name=f"Warn #{i}", value=f"**Motif:** {w['reason']}\n**Le:** {w['date']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="unwarn")
@commands.has_permissions(manage_messages=True)
async def unwarn(ctx, member: discord.Member, index: int):
    warns = load_warns()
    uid = str(member.id)
    if uid not in warns or not warns[uid]: return await ctx.send("❌ Aucun warn.")

    real_index = index - 1
    if 0 <= real_index < len(warns[uid]):
        warns[uid].pop(real_index)
        save_warns(warns)
        await ctx.send(f"✅ Warn n°{index} retiré.")
    else:
        await ctx.send("❌ Numéro invalide.")

@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    warns = load_warns()
    uid = str(member.id)
    if uid in warns:
        del warns[uid]
        save_warns(warns)
        await ctx.send(f"♻️ Casier de {member.mention} nettoyé.")
    else:
        await ctx.send("Déjà clean.")

# ==========================================
# 🎭 COMMANDES : FUN & COMMUNAUTÉ
# ==========================================

@bot.command(name="level")
async def level(ctx):
    xp = user_xp.get(str(ctx.author.id), 0)
    lvl = xp // XP_PER_LEVEL
    await ctx.send(embed=discord.Embed(title="📊 Niveau", description=f"Niveau **{lvl}** ({xp} XP)", color=0x3498db))

@bot.command(name="top")
async def top(ctx):
    sorted_xp = sorted(user_xp.items(), key=lambda i: i[1], reverse=True)[:10]
    desc = "\n".join([f"**#{i}** <@{uid}> : Niv {xp // XP_PER_LEVEL}" for i, (uid, xp) in enumerate(sorted_xp, 1)])
    await ctx.send(embed=discord.Embed(title="🏆 Classement", description=desc or "Vide", color=0xf1c40f))

@bot.command(name="poll")
async def poll(ctx, *, question):
    await ctx.message.delete()
    msg = await ctx.send(embed=discord.Embed(title="📊 Sondage", description=question, color=0x9b59b6))
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

@bot.command(name="8ball")
async def eight_ball(ctx, *, question):
    responses = ["Oui.", "Non.", "Peut-être.", "Jamais.", "C'est sûr."]
    await ctx.send(embed=discord.Embed(title="🎱 8Ball", description=f"Q: {question}\nR: {random.choice(responses)}", color=0x9b59b6))

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, text):
    await ctx.message.delete()
    await ctx.send(text)

# ==========================================
# 🚀 LANCEMENT
# ==========================================
bot.run(TOKEN)