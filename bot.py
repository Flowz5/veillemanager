import discord
from discord.ext import commands
import json
import os

load_dotenv()

# ==========================================
# ⚙️ CONFIGURATION (À MODIFIER)
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN") 
CHANNEL_VEILLE_ID = 1463268390436343808  # ID du salon #veille-techno
CHANNEL_GENERAL_ID = 1463268249738154119 # ID du salon #général (pour bienvenue et level up)
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
    
    # Attribution du rôle
    role = discord.utils.get(member.guild.roles, name=ROLE_READER_NAME)
    if role:
        await member.add_roles(role)
        print(f"Role {ROLE_READER_NAME} donné à {member.name}.")
    
    # Message de bienvenue
    channel = bot.get_channel(CHANNEL_GENERAL_ID)
    if channel:
        await channel.send(f"Bienvenue {member.mention} ! 🎓\nTu as reçu le rôle **{ROLE_READER_NAME}**. Va vite voir <#{CHANNEL_VEILLE_ID}> pour commencer ta veille !")

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
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=5):
    """Nettoie les messages du salon"""
    await ctx.channel.purge(limit=amount + 1) # +1 pour effacer la commande elle-même

# Lancement du bot
bot.run(TOKEN)