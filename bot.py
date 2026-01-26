import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import asyncio
from datetime import timedelta # <--- AJOUTE ÇA TOUT EN HAUT AVEC LES AUTRES IMPORTS

load_dotenv()

# ==========================================
# ⚙️ CONFIGURATION (À MODIFIER)
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN") 
if TOKEN is None:
    print("ERREUR : Le token n'a pas été trouvé !")
else:
    TOKEN = TOKEN.strip()  # <--- C'est ça qui sauve la vie ! Enlève les espaces et sauts de ligne
CHANNEL_VEILLE_ID = 1463268390436343808  # ID du salon #veille-techno
CHANNEL_GENERAL_ID = 1463268249738154119 # ID du salon #général (pour bienvenue et level up)
CHANNEL_WELCOME_ID = 1465122841753026560
ROLE_READER_NAME = "Reader"             # Nom exact du rôle
EMOJI_VALIDATION = "✅"                 # L'emoji à cliquer
XP_PER_CLICK = 10                       # XP gagnée par article
XP_PER_LEVEL = 100                      # XP pour passer un niveau

# Fichier de sauvegarde (créé automatiquement)
DATA_FILE = "xp_data.json"

# ==========================================
# 🔧 SETUP DU BOT & PERMISSIONS
# ==========================================
intents = discord.Intents.default()
intents.members = True          # Nécessaire pour l'auto-rôle
intents.message_content = True  # Nécessaire pour lire les messages et réagir
intents.reactions = True        # Nécessaire pour le système d'XP

bot = commands.Bot(command_prefix="!", intents=intents)

# Variable globale pour l'XP
user_xp = {}

# ==========================================
# 💾 FONCTIONS DE SAUVEGARDE (PERSISTENCE)
# ==========================================
def load_xp():
    """Charge l'XP de façon sécurisée"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Fichier XP vide ou corrompu. Réinitialisation...")
            return {} # Retourne un dictionnaire vide au lieu de planter
    return {}

def save_xp():
    """Sauvegarde l'XP dans le fichier JSON"""
    with open(DATA_FILE, "w") as f:
        json.dump(user_xp, f)

# ==========================================
# 🤖 ÉVÉNEMENTS DU BOT
# ==========================================

@bot.event
async def on_ready():
    global user_xp
    user_xp = load_xp() # On charge les anciens scores
    print(f'✅ Bot connecté en tant que {bot.user}')
    print(f'📊 Données XP chargées pour {len(user_xp)} utilisateurs.')
    await bot.change_presence(activity=discord.Game(name="surveiller la veille 🕵️"))

# --- 1. ACCUEIL & AUTO-ROLE ---
@bot.event
async def on_member_join(member):
    print(f"Nouvel arrivant : {member.name}")
    
    # 1. Attribution du rôle
    role = discord.utils.get(member.guild.roles, name=ROLE_READER_NAME)
    if role:
        await member.add_roles(role)
        print(f"Role {ROLE_READER_NAME} donné à {member.name}.")
    
    # 2. Message de bienvenue dans le salon #nouveaux
    # On récupère le salon grâce à son ID précis
    channel = bot.get_channel(CHANNEL_WELCOME_ID)
    
    if channel:
        await channel.send(f"Bienvenue {member.mention} ! 🎓\nTu as reçu le rôle **{ROLE_READER_NAME}**.\nVa vite voir <#{CHANNEL_VEILLE_ID}> pour commencer ta veille !")
    else:
        print(f"❌ Erreur : Impossible de trouver le salon d'accueil (ID: {CHANNEL_WELCOME_ID})")

# --- 2. AUTO-REACTION (Le bot prépare le terrain) ---
@bot.event
async def on_message(message):
    # Important : laisse passer les commandes (!level, !clear)
    await bot.process_commands(message)

    # Vérifie si le message est dans le salon veille
    if message.channel.id == CHANNEL_VEILLE_ID:
        # On évite que le bot réagisse à ses propres messages (optionnel)
        if message.author.id != bot.user.id: 
            try:
                await message.add_reaction(EMOJI_VALIDATION)
                print(f"✅ Auto-réaction ajoutée sur un nouvel article.")
            except Exception as e:
                print(f"Erreur réaction : {e}")

# --- 3. SYSTÈME DE LEVELING (Le coeur du jeu) ---
@bot.event
async def on_raw_reaction_add(payload):
    # On ne traite que le bon salon et le bon emoji
    if payload.channel_id == CHANNEL_VEILLE_ID and str(payload.emoji) == EMOJI_VALIDATION:
        
        # Le bot ne gagne pas d'XP
        if payload.user_id == bot.user.id:
            return

        # Conversion de l'ID utilisateur en string pour le JSON
        user_id_str = str(payload.user_id)
        
        # Récupération de l'XP actuelle
        current_xp = user_xp.get(user_id_str, 0)
        current_level = current_xp // XP_PER_LEVEL
        
        # Ajout des points
        new_xp = current_xp + XP_PER_CLICK
        new_level = new_xp // XP_PER_LEVEL
        
        # Mise à jour et sauvegarde
        user_xp[user_id_str] = new_xp
        save_xp()
        
        print(f"📈 User {payload.user_id} : {current_xp} -> {new_xp} XP")

        # Notification de LEVEL UP
        if new_level > current_level:
            channel = bot.get_channel(CHANNEL_GENERAL_ID)
            if channel:
                # Récupérer l'objet Member pour le mentionner proprement
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                if member:
                     await channel.send(f"🎉 **LEVEL UP !** Bravo {member.mention}, tu passes **Niveau {new_level}** en Veille Techno ! 🧠")

# ==========================================
# 🛠️ COMMANDES ADMIN & UTILISATEUR
# ==========================================

@bot.command()
async def level(ctx):
    """Affiche son niveau et son XP"""
    user_id_str = str(ctx.author.id)
    xp = user_xp.get(user_id_str, 0)
    lvl = xp // XP_PER_LEVEL
    next_lvl = (lvl + 1) * XP_PER_LEVEL
    
    embed = discord.Embed(title="📊 Ton niveau de Veille", color=0x3498db)
    embed.add_field(name="Niveau", value=str(lvl), inline=True)
    embed.add_field(name="XP Totale", value=f"{xp} XP", inline=True)
    embed.add_field(name="Prochain niveau", value=f"Encore {next_lvl - xp} XP", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    """Affiche le Top 10 des veilleurs"""
    # Trie les utilisateurs par XP décroissant
    sorted_xp = sorted(user_xp.items(), key=lambda item: item[1], reverse=True)
    top_10 = sorted_xp[:10]
    
    embed = discord.Embed(title="🏆 Classement Veille Techno", color=0xf1c40f)
    desc = ""
    
    for i, (uid, xp) in enumerate(top_10, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else "Fantôme"
        lvl = xp // XP_PER_LEVEL
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        desc += f"**{medal} {name}** : Niveau {lvl} ({xp} XP)\n"
    
    embed.description = desc if desc else "Personne n'a encore d'XP !"
    await ctx.send(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    """Crée un sondage simple oui/non"""
    await ctx.message.delete() # Supprime la commande de l'utilisateur
    embed = discord.Embed(title="📊 Sondage", description=question, color=0x9b59b6)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")


bot.remove_command("help")

# ==========================================
# ℹ️ MENU D'AIDE (MIS À JOUR)
# ==========================================

@bot.command(name="help")
async def help_cmd(ctx):
    """Affiche le menu d'aide complet."""
    
    embed = discord.Embed(
        title="🛡️ Centre de Contrôle - Parabot",
        description="Liste des commandes disponibles pour la gestion du serveur.",
        color=0x2c3e50 # Bleu nuit "Admin"
    )
    
    # --- SECTION MODÉRATION ---
    embed.add_field(
        name="⚖️ Modération & Sécurité",
        value=(
            "**`!kick @membre <raison>`** : Expulse un membre.\n"
            "**`!ban @membre <raison>`** : Bannit un membre.\n"
            "**`!unban <Pseudo#0000>`** : Débannit un utilisateur.\n"
            "**`!mute @membre <min> <raison>`** : Rend muet (Timeout).\n"
            "**`!unmute @membre`** : Rend la parole.\n"
            "**`!lock` / `!unlock`** : Verrouille/Ouvre le salon actuel.\n"
            "**`!clear <nombre>`** : Supprime les messages récents."
        ),
        inline=False
    )

    # --- SECTION INFOS & UTILITAIRES ---
    embed.add_field(
        name="🕵️‍♂️ Infos & Analyse",
        value=(
            "**`!userinfo @membre`** : Affiche la fiche complète (Dates, Rôles...).\n"
            "**`!regles`** : Affiche le règlement (Admin seulement)."
        ),
        inline=False
    )
    
    # --- SECTION XP & COMMUNAUTÉ ---
    embed.add_field(
        name="🏆 Vie du Serveur",
        value=(
            "**`!level`** : Voir ton niveau et ton XP.\n"
            "**`!top`** : Voir le classement des meilleurs lecteurs.\n"
            "**`!poll <question>`** : Lancer un sondage."
        ),
        inline=False
    )
    
    embed.set_footer(text="Parabot System • Déployé sur Fedora Linux")
    
    await ctx.send(embed=embed)

# ==========================================
# 📜 COMMANDE RÈGLEMENT
# ==========================================
@bot.command(name="regles")
@commands.has_permissions(administrator=True) # Sécurité : Seul un admin peut lancer ça
async def regles(ctx):
    """Poste le règlement dans le salon actuel."""
    
    # 1. On supprime le message de la commande "!regles" pour laisser le chat propre
    await ctx.message.delete()

    # 2. Création de l'Embed (le joli encadré)
    embed = discord.Embed(
        title="📜 RÈGLEMENT DU SERVEUR",
        description="Bienvenue ! Pour que la communauté reste agréable, merci de respecter ces quelques règles.",
        color=0xe74c3c # Rouge
    )

    # 3. Ajout des règles (Tu peux modifier le texte ici !)
    embed.add_field(
        name="1️⃣ • Respect & Courtoisie",
        value="Soyez respectueux envers les autres membres. Aucune insulte, propos raciste, homophobe ou haineux ne sera toléré.",
        inline=False
    )
    
    embed.add_field(
        name="2️⃣ • Pas de Spam / Pub",
        value="Évitez le flood inutile. La publicité pour d'autres serveurs ou services est interdite sans accord du staff.",
        inline=False
    )
    
    embed.add_field(
        name="3️⃣ • Contenu approprié",
        value="Pas de contenu NSFW, gore ou choquant. Ce serveur est ouvert à tous.",
        inline=False
    )
    
    embed.add_field(
        name="4️⃣ • Veille Techno",
        value="Le salon veille est réservé aux articles tech. Utilisez les réactions pour gagner de l'XP !",
        inline=False
    )

    embed.set_footer(text="L'équipe de modération • Tout manquement sera sanctionné.")
    
    # 4. Envoi du message
    await ctx.send(embed=embed)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Supprime un nombre donné de messages."""
    await ctx.channel.purge(limit=amount + 1) # +1 pour supprimer aussi la commande !clear
    
    # Petit message de confirmation qui s'efface tout seul après 3 secondes
    msg = await ctx.send(f"🧹 J'ai supprimé {amount} messages.")
    await asyncio.sleep(3)
    await msg.delete()

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Tu n'as pas la permission de gérer les messages.")


# ==========================================
# 🛡️ COMMANDES DE MODÉRATION (KICK / BAN)
# ==========================================

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune raison fournie"):
    """Expulse un membre du serveur."""
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(description=f"👢 **{member.name}** a été expulsé.\n**Raison :** {reason}", color=0xe67e22)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Je ne peux pas expulser ce membre. (Vérifie mes droits et ma position dans les rôles).")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Aucune raison fournie"):
    """Bannit un membre définitivement."""
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(description=f"🔨 **{member.name}** a été BANNIS.\n**Raison :** {reason}", color=0xff0000)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Impossible de bannir ce membre.")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_input):
    """Débannit un utilisateur (Pseudo#Tag ou ID)."""
    banned_users = await ctx.guild.bans()
    
    # On cherche dans la liste des bannis
    for ban_entry in banned_users:
        user = ban_entry.user
        
        # On compare le nom ou l'ID (en string)
        if (user.name + "#" + user.discriminator == user_input) or (str(user.id) == user_input):
            await ctx.guild.unban(user)
            await ctx.send(f"✅ **{user.name}** a été débanni.")
            return
            
    await ctx.send(f"❌ Utilisateur '{user_input}' introuvable dans la liste des bannis.")

# ==========================================
# 🤐 MUTE / TIMEOUT
# ==========================================

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int, *, reason="Comportement"):
    """Rend un membre muet pour X minutes."""
    
    # On applique le Timeout via l'API Discord
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    
    embed = discord.Embed(description=f"🤐 **{member.name}** a été rendu muet pour **{minutes} minutes**.\n**Raison :** {reason}", color=0x95a5a6)
    await ctx.send(embed=embed)

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    """Rend la parole à un membre."""
    # Pour enlever le timeout, on met la durée à None
    await member.timeout(None)
    await ctx.send(f"🔊 **{member.name}** peut parler à nouveau.")

# ==========================================
# 🔒 GESTION DES SALONS (LOCKDOWN)
# ==========================================

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Verrouille le salon actuel (Plus personne ne peut écrire)."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 **Ce salon a été verrouillé par la modération.**")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Déverrouille le salon."""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 **Le salon est réouvert.**")

# ==========================================
# 🕵️‍♂️ INFO UTILISATEUR (Userinfo)
# ==========================================

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    """Affiche les informations détaillées d'un membre."""
    # Si aucun membre n'est précisé, on prend l'auteur de la commande
    member = member or ctx.author
    
    # Mise en forme des dates (Jour/Mois/Année Heure:Minute)
    created_at = member.created_at.strftime("%d/%m/%Y à %H:%M")
    joined_at = member.joined_at.strftime("%d/%m/%Y à %H:%M")
    
    # Liste des rôles (on retire le @everyone qui ne sert à rien)
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    roles_str = " ".join(roles) if roles else "Aucun rôle"
    
    # On crée l'encadré (Embed)
    embed = discord.Embed(title=f"👤 Fiche de {member.name}", color=member.color)
    
    # L'image de profil en haut à droite
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="🏷️ Surnom", value=member.display_name, inline=True)
    
    # C'est ici que tu repères les raiders 👇
    embed.add_field(name="📅 Compte créé le", value=created_at, inline=False)
    embed.add_field(name="📥 A rejoint le", value=joined_at, inline=False)
    
    embed.add_field(name="🎭 Rôles", value=roles_str, inline=False)
    
    # Petit footer pour savoir si c'est un bot ou un humain
    bot_status = "🤖 C'est un Bot" if member.bot else "👤 C'est un Humain"
    embed.set_footer(text=f"{bot_status} • Demandé par {ctx.author.name}")
    
    await ctx.send(embed=embed)

# Lancement du bot
bot.run(TOKEN)