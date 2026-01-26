import discord
from discord.ext import commands
import json
import os
import asyncio
import random
from datetime import timedelta
from dotenv import load_dotenv

# Charge les variables d'environnement (.env)
load_dotenv()

# ==========================================
# ⚙️ CONFIGURATION & CONSTANTES
# ==========================================

# --- Sécurité & Token ---
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    TOKEN = TOKEN.strip() # Nettoyage préventif des espaces
else:
    print("❌ ERREUR CRITIQUE : Le token n'a pas été trouvé dans le fichier .env !")
    exit()

# --- Configuration des Salons (IDs) ---
# ⚠️ Vérifie bien que ces IDs correspondent à TON serveur
CHANNEL_VEILLE_ID    = 1463268390436343808  # Salon #veille-techno
CHANNEL_GENERAL_ID   = 1463268249738154119  # Salon #général (Level up)
CHANNEL_WELCOME_ID   = 1465122841753026560  # Salon #bienvenue

# --- Configuration du Gameplay (XP) ---
ROLE_READER_NAME = "Reader"    # Rôle donné à l'arrivée
EMOJI_VALIDATION = "✅"        # Emoji pour valider la veille
XP_PER_CLICK     = 10          # XP gagnée par réaction
XP_PER_LEVEL     = 100         # XP nécessaire par niveau
DATA_FILE        = "xp_data.json" # Fichier de sauvegarde
# --- Configuration Auto-Modération ---
BAD_WORDS = ["con", "connard", "merde", "tg", "fdp", "salope", "putain", "abruti", "negro"]

# ==========================================
# 🔧 INITIALISATION DU BOT
# ==========================================

intents = discord.Intents.default()
intents.members = True          # Pour voir les nouveaux arrivants
intents.message_content = True  # Pour lire les commandes
intents.reactions = True        # Pour le système d'XP

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")      # On désactive l'aide par défaut pour mettre la nôtre

# Variable globale pour stocker l'XP en mémoire
user_xp = {}

# ==========================================
# 💾 GESTION DES DONNÉES (JSON)
# ==========================================

def load_xp():
    """Charge l'XP depuis le fichier JSON de façon sécurisée."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Fichier XP corrompu. Réinitialisation...")
            return {}
    return {}

def save_xp():
    """Sauvegarde l'XP actuelle dans le fichier JSON."""
    with open(DATA_FILE, "w") as f:
        json.dump(user_xp, f)

# ==========================================
# 🤖 ÉVÉNEMENTS (EVENTS)
# ==========================================

@bot.event
async def on_ready():
    """Se déclenche au démarrage du bot."""
    global user_xp
    user_xp = load_xp()
    print(f'✅ Bot connecté en tant que {bot.user}')
    print(f'📊 Données XP chargées pour {len(user_xp)} utilisateurs.')
    await bot.change_presence(activity=discord.Game(name="surveiller la veille 🕵️"))

@bot.event
async def on_member_join(member):
    """Gère l'arrivée d'un nouveau membre (Rôle + Message)."""
    print(f"Nouvel arrivant : {member.name}")
    
    # 1. Auto-Rôle
    role = discord.utils.get(member.guild.roles, name=ROLE_READER_NAME)
    if role:
        await member.add_roles(role)
    
    # 2. Message de bienvenue
    channel = bot.get_channel(CHANNEL_WELCOME_ID)
    if channel:
        await channel.send(f"Bienvenue {member.mention} ! 🎓\nTu as reçu le rôle **{ROLE_READER_NAME}**.\nVa vite voir <#{CHANNEL_VEILLE_ID}> pour commencer ta veille !")

@bot.event
async def on_message(message):
    """Gère chaque message posté."""
    # IMPORTANT : Permet aux commandes (!help, !ping) de fonctionner
    await bot.process_commands(message)

    # Auto-Réaction dans le salon de veille
    if message.channel.id == CHANNEL_VEILLE_ID and message.author.id != bot.user.id:
        try:
            await message.add_reaction(EMOJI_VALIDATION)
        except Exception as e:
            print(f"Erreur d'auto-réaction : {e}")

@bot.event
async def on_raw_reaction_add(payload):
    """Système d'XP au clic sur une réaction."""
    # Filtre : Bon salon et bon emoji uniquement
    if payload.channel_id == CHANNEL_VEILLE_ID and str(payload.emoji) == EMOJI_VALIDATION:
        
        if payload.user_id == bot.user.id: return # Le bot ne gagne pas d'XP

        user_id = str(payload.user_id)
        
        # Calcul de l'XP
        current_xp = user_xp.get(user_id, 0)
        current_level = current_xp // XP_PER_LEVEL
        
        new_xp = current_xp + XP_PER_CLICK
        new_level = new_xp // XP_PER_LEVEL
        
        # Sauvegarde
        user_xp[user_id] = new_xp
        save_xp()
        
        # Annonce du Level Up
        if new_level > current_level:
            channel = bot.get_channel(CHANNEL_GENERAL_ID)
            if channel:
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                if member:
                     await channel.send(f"🎉 **LEVEL UP !** Bravo {member.mention}, tu passes **Niveau {new_level}** ! 🧠")

# ==========================================
# ℹ️ COMMANDES : INFORMATIONS & AIDE
# ==========================================

@bot.command(name="help")
async def help_cmd(ctx):
    """Affiche le menu d'aide mis à jour."""
    
    embed = discord.Embed(
        title="🛡️ Centre de Contrôle - Parabot",
        description="Liste des commandes disponibles.",
        color=0x2c3e50
    )
    
    # --- NOUVEAU : SECTION COMMUNICATION ---
    embed.add_field(
        name="📢 Communication & Admin",
        value=(
            "**`!announce <#salon> <Titre|Message>`** : Faire une annonce officielle.\n"
            "**`!regles`** : Affiche le règlement."
        ),
        inline=False
    )
    
    # --- SECTION MODÉRATION ---
    embed.add_field(
        name="⚖️ Modération & Sécurité",
        value=(
            "**`🛡️ Auto-Mod`** : Actif (Filtre les insultes).\n"
            "`!kick`, `!ban`, `!unban` : Sanctions.\n"
            "`!mute`, `!unmute` : Gérer le silence.\n"
            "`!lock`, `!unlock`, `!clear` : Gérer les salons."
        ),
        inline=False
    )

    # --- SECTION INFOS ---
    embed.add_field(
        name="🕵️‍♂️ Infos & Utile",
        value=(
            "`!userinfo @membre` : Fiche profil.\n"
            "`!serverinfo` : Stats du serveur.\n"
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
    
    embed.set_footer(text=f"Version 2.0 • {ctx.guild.name}")
    
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    """Affiche les statistiques du serveur."""
    guild = ctx.guild
    embed = discord.Embed(title=f"ℹ️ Infos : {guild.name}", color=0xf1c40f)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="👑 Propriétaire", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Membres", value=f"{guild.member_count}", inline=True)
    embed.add_field(name="💬 Salons", value=f"{len(guild.channels)}", inline=True)
    embed.add_field(name="📅 Création", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.set_footer(text=f"ID Serveur : {guild.id}")
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    """Affiche la fiche d'un membre."""
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    
    embed = discord.Embed(title=f"👤 Fiche de {member.name}", color=member.color)
    if member.avatar: embed.set_thumbnail(url=member.avatar.url)
    
    embed.add_field(name="📅 Créé le", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="📥 Rejoint le", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="🎭 Rôles", value=" ".join(roles) if roles else "Aucun", inline=False)
    embed.set_footer(text=f"ID: {member.id} • {'BOT' if member.bot else 'HUMAIN'}")
    await ctx.send(embed=embed)

@bot.command(name="regles")
@commands.has_permissions(administrator=True)
async def regles(ctx):
    """Affiche le règlement (Admin uniquement)."""
    await ctx.message.delete()
    embed = discord.Embed(title="📜 RÈGLEMENT DU SERVEUR", description="Respectez ces règles pour une bonne ambiance.", color=0xe74c3c)
    embed.add_field(name="1️⃣ • Respect", value="Courtoisie obligatoire. Pas de haine.", inline=False)
    embed.add_field(name="2️⃣ • Spam", value="Pas de flood ni de pub sans autorisation.", inline=False)
    embed.add_field(name="3️⃣ • Veille", value="Le salon veille est réservé à la Tech.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="announce")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel, *, content: str):
    """Envoie une annonce officielle (Ex: !announce #general Titre | Message)."""
    # On sépare le titre du message avec le caractère "|"
    if "|" in content:
        title, text = content.split("|", 1)
    else:
        title = "📢 Annonce Officielle"
        text = content

    embed = discord.Embed(title=title.strip(), description=text.strip(), color=0xe74c3c)
    embed.set_footer(text=f"Par l'équipe de modération • {ctx.guild.name}")
    
    # Ajoute le logo du serveur si disponible
    if ctx.guild.icon: 
        embed.set_thumbnail(url=ctx.guild.icon.url)

    await channel.send(embed=embed)
    await ctx.send(f"✅ Annonce envoyée dans {channel.mention} !")

# ==========================================
# 🏆 COMMANDES : COMMUNAUTÉ & XP
# ==========================================

@bot.command()
async def level(ctx):
    """Affiche son niveau actuel."""
    xp = user_xp.get(str(ctx.author.id), 0)
    lvl = xp // XP_PER_LEVEL
    next_lvl = (lvl + 1) * XP_PER_LEVEL
    
    embed = discord.Embed(title="📊 Ton niveau", color=0x3498db)
    embed.add_field(name="Niveau", value=str(lvl), inline=True)
    embed.add_field(name="XP", value=f"{xp} / {next_lvl}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    """Affiche le Top 10."""
    sorted_xp = sorted(user_xp.items(), key=lambda item: item[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Classement Veille", color=0xf1c40f)
    desc = ""
    for i, (uid, xp) in enumerate(sorted_xp, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else "Ancien membre"
        desc += f"**#{i} {name}** : Niveau {xp // XP_PER_LEVEL} ({xp} XP)\n"
    embed.description = desc or "Le classement est vide."
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    """Crée un sondage Oui/Non."""
    await ctx.message.delete()
    embed = discord.Embed(title="📊 Sondage", description=question, color=0x9b59b6)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

# ==========================================
# 🎭 COMMANDES : FUN
# ==========================================

@bot.command(name="8ball")
async def eight_ball(ctx, *, question):
    """La boule magique."""
    responses = ["C'est certain.", "Oui, absolument.", "Peut-être...", "Ne compte pas dessus.", "Ma réponse est non."]
    embed = discord.Embed(title="🎱 Boule Magique", color=0x9b59b6)
    embed.add_field(name="❓ Question", value=question, inline=False)
    embed.add_field(name="💬 Réponse", value=random.choice(responses), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, text):
    """Fait parler le bot (Staff)."""
    await ctx.message.delete()
    await ctx.send(text)

# ==========================================
# ⚖️ COMMANDES : MODÉRATION
# ==========================================

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Supprime X messages."""
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 {amount} messages supprimés.")
    await asyncio.sleep(3)
    await msg.delete()

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Permission refusée.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune"):
    """Expulse un membre."""
    await member.kick(reason=reason)
    await ctx.send(embed=discord.Embed(description=f"👢 **{member.name}** expulsé. Raison: {reason}", color=0xe67e22))

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Aucune"):
    """Bannit un membre."""
    await member.ban(reason=reason)
    await ctx.send(embed=discord.Embed(description=f"🔨 **{member.name}** banni. Raison: {reason}", color=0xff0000))

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_input):
    """Débannit un membre (Pseudo#0000 ou ID)."""
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name + "#" + user.discriminator == user_input) or (str(user.id) == user_input):
            await ctx.guild.unban(user)
            await ctx.send(f"✅ **{user.name}** débanni.")
            return
    await ctx.send(f"❌ Utilisateur non trouvé dans les bannis.")

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int, *, reason="Comportement"):
    """Mute temporaire (Timeout)."""
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"🤐 **{member.name}** muet pour {minutes} min.")

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    """Rend la parole."""
    await member.timeout(None)
    await ctx.send(f"🔊 **{member.name}** peut reparler.")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Verrouille le salon."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Déverrouille le salon."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon ouvert.")

# === 🛡️ AUTO-MODÉRATION (Code à insérer au début de on_message) ===
    message_content_lower = message.content.lower()
    
    # On vérifie si un mot de la liste est présent
    if any(word in message_content_lower.split() for word in BAD_WORDS):
        await message.delete() # On supprime le message
        warning = await message.channel.send(f"⚠️ {message.author.mention}, surveille ton langage !")
        await asyncio.sleep(5)
        await warning.delete() # On supprime l'avertissement après 5s
        return # IMPORTANT : On arrête tout ici (pas d'XP, pas de commande)

# ==========================================
# 🚀 LANCEMENT
# ==========================================
bot.run(TOKEN)