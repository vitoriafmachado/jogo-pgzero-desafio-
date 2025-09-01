# game.py — Pygame Zero com sons, score, inimigos que se movem e vitória por pontuação
import random
from pgzero.loaders import images
from pygame import Rect

WIDTH, HEIGHT = 960, 540

# ---------------- CONFIG ----------------
GRAVITY = 900
PLAYER_SPEED = 240
JUMP_SPEED = -420
COYOTE_TIME = 0.15
JUMP_BUFFER = 0.15
SHOT_SPEED = 560
MAX_ENEMIES = 3
KILLS_TO_WIN = 10  # objetivo de pontuação

# ---------------- PLAYER ----------------
player = Actor("player")
player.vy = 0
player.on_ground = False
player.facing_left = False
player.frame = 0
player.anim_timer = 0.0
player.life = 5
player.hurt_cd = 0.0
player.coyote = 0.0
player.jump_buf = 0.0

# animações do player
_player_right = [
    images.load("player"),
    images.load("player02"),
    images.load("player03")
]
_player_left = [
    images.load("playeresquerdacorrendo"),
    images.load("playerparadoesquerda"),
    images.load("playeresquerdacorrendo")
]

# tiros
SHOT_RIGHT = ["tiro01", "tiro02", "tiro03"]
SHOT_LEFT = ["tiro02", "tiro02", "tiro02"]  # usando tiro02.png para esquerda

# ---------------- GAME STATE ----------------
state = "menu"
sound_on = True
score = 0
menu_items = ["Começar", "Som: ON", "Sair"]
menu_index = 0

# ---------------- PLATFORMS ----------------
platforms = [
    Rect((60, 480), (220, 18)),
    Rect((340, 420), (230, 18)),
    Rect((650, 360), (210, 18)),
    Rect((210, 300), (220, 18)),
    Rect((520, 230), (220, 18)),
]

# ---------------- ENEMIES / BULLETS ----------------
enemies = []
bullets = []

# ==========================================================
# Helpers
def put_player_on_start():
    ground = platforms[0]
    player.midbottom = (ground.left + 80, ground.top)
    player.vy = 0
    player.on_ground = True
    player.facing_left = False
    player.frame = 0
    player.anim_timer = 0
    player.hurt_cd = 0
    player.coyote = 0
    player.jump_buf = 0

def safe_spawn_on_platform(avoid_rect: Rect):
    for _ in range(30):
        plat = random.choice(platforms[1:])
        x = random.randint(plat.left + 28, plat.right - 28)
        y = plat.top
        r = Rect((x - 24, y - 40), (48, 40))
        if not r.colliderect(avoid_rect):
            same = sum(1 for e in enemies if e["plat"] == plat)
            if same < 1:
                return plat, x, y
    plat = platforms[1]
    x = (plat.left + plat.right) // 2
    y = plat.top
    return plat, x, y

def schedule_spawn():
    if state == "playing" and score < KILLS_TO_WIN:
        clock.schedule(spawn_enemy, random.uniform(2.0, 3.4))

def spawn_enemy():
    if state != "playing":
        return
    if len(enemies) < MAX_ENEMIES:
        kind = random.choice(["slime", "slime_flip", "orange"])
        plat, x, y = safe_spawn_on_platform(Rect(player.left, player.top, player.width, player.height))
        if "slime" in kind:
            a = Actor("slime1")
        else:
            a = Actor("inimigolaranja1")
        a.midbottom = (x, y)
        a.anchor = ("center", "bottom")
        speed = random.choice([-95, 95])
        enemies.append({
            "actor": a, "vx": speed, "vy": 0.0, "plat": plat,
            "kind": kind, "frame": 0, "timer": 0.0,
            "mirror": (kind == "slime_flip"), "jump_cd": random.uniform(0.6, 1.4)
        })
    schedule_spawn()

def reset_game():
    global score, enemies, bullets, state
    score = 0
    enemies.clear()
    bullets.clear()
    player.life = 5
    put_player_on_start()
    state = "playing"
    schedule_spawn()

# ==========================================================
# Physics helpers
def land_actor_on_platform(actor, vy):
    on_ground = False
    for plat in platforms:
        if actor.colliderect(plat) and vy >= 0 and actor.bottom <= plat.top + 40:
            actor.bottom = plat.top
            vy = 0
            on_ground = True
    return vy, on_ground

# ==========================================================
# Update
def update(dt):
    global state, score
    if state in ("menu", "gameover", "victory"):
        return

    # ---------- player ----------
    if player.hurt_cd > 0:
        player.hurt_cd = max(0, player.hurt_cd - dt)
    player.coyote = max(0, player.coyote - dt)
    player.jump_buf = max(0, player.jump_buf - dt)

    player.vy += GRAVITY * dt
    player.y += player.vy * dt
    player.vy, player.on_ground = land_actor_on_platform(player, player.vy)
    if player.on_ground:
        player.coyote = COYOTE_TIME

    if player.jump_buf > 0 and (player.on_ground or player.coyote > 0):
        player.vy = JUMP_SPEED
        player.on_ground = False
        player.coyote = 0
        player.jump_buf = 0
        if sound_on:
            sounds.jump.play()

    if keyboard.left:
        player.x -= PLAYER_SPEED * dt
        player.facing_left = True
    if keyboard.right:
        player.x += PLAYER_SPEED * dt
        player.facing_left = False
    player.x = max(16, min(WIDTH - 16, player.x))

    moving = keyboard.left or keyboard.right
    player.anim_timer += dt
    if moving and player.anim_timer > 0.12:
        player.frame = (player.frame + 1) % 3
        player.anim_timer = 0
    if not moving:
        player.frame = 0
        player.anim_timer = 0

    if player.top > HEIGHT + 40 or player.life <= 0:
        state = "gameover"

    # ---------- inimigos ----------
    for enemy in enemies:
        a = enemy["actor"]

        # gravidade
        enemy["vy"] += GRAVITY * dt
        a.y += enemy["vy"] * dt
        enemy["vy"], on_ground = land_actor_on_platform(a, enemy["vy"])

        # movimento horizontal
        a.x += enemy["vx"] * dt

        # virar se bater na borda da plataforma
        if a.left < enemy["plat"].left or a.right > enemy["plat"].right:
            enemy["vx"] *= -1

        # pulo ocasional
        enemy["jump_cd"] -= dt
        if on_ground and enemy["jump_cd"] <= 0:
            enemy["vy"] = JUMP_SPEED
            enemy["jump_cd"] = random.uniform(1.2, 2.4)

        # chance de cair da plataforma (descer)
        if on_ground and random.random() < 0.003:
            enemy["vy"] = 50

    # ---------- bullets ----------
    for bullet in list(bullets):
        ba = bullet["actor"]
        ba.x += bullet["vx"] * dt
        bullet["timer"] += dt
        frames = SHOT_LEFT if bullet["vx"] < 0 else SHOT_RIGHT
        if bullet["timer"] > 0.08:
            bullet["timer"] = 0
            bullet["frame"] = (bullet["frame"] + 1) % len(frames)
        ba.image = frames[bullet["frame"]]
        if ba.right < 0 or ba.left > WIDTH:
            bullets.remove(bullet)

    # ---------- colisões ----------
    for bullet in list(bullets):
        for enemy in list(enemies):
            if bullet["actor"].colliderect(enemy["actor"]):
                bullets.remove(bullet)
                enemies.remove(enemy)
                score += 1
                if sound_on:
                    sounds.pickup.play()
                if score >= KILLS_TO_WIN:
                    state = "victory"
                break

# ==========================================================
# Input
def on_key_down(key):
    global state, sound_on, menu_index, menu_items

    # --- MENU PRINCIPAL ---
    if state == "menu":
        if key == keys.UP:
            menu_index = (menu_index - 1) % len(menu_items)
        elif key == keys.DOWN:
            menu_index = (menu_index + 1) % len(menu_items)
        elif key == keys.RETURN:
            choice = menu_items[menu_index]
            if choice.startswith("Começar"):
                reset_game()
            elif choice.startswith("Som"):
                sound_on = not sound_on
                menu_items[1] = f"Som: {'ON' if sound_on else 'OFF'}"
            elif choice.startswith("Sair"):
                raise SystemExit
        elif key == keys.M:  # toggle som no menu
            sound_on = not sound_on
            menu_items[1] = f"Som: {'ON' if sound_on else 'OFF'}"
        elif key == keys.X:  # sair rápido no menu
            raise SystemExit
        return

    # --- GAMEOVER ou VITÓRIA ---
    if state in ("gameover", "victory"):
        if key == keys.R:       # reinicia
            reset_game()
        elif key == keys.X:     # sair
            raise SystemExit
        elif key == keys.M:     # toggle som
            sound_on = not sound_on
            menu_items[1] = f"Som: {'ON' if sound_on else 'OFF'}"
        return

    # --- JOGO RODANDO ---
    if key == keys.SPACE:  # pulo
        player.jump_buf = JUMP_BUFFER
        if sound_on:
            sounds.jump.play()

    if key == keys.Z:  # tiro
        bx = player.x + (26 if not player.facing_left else -26)
        by = player.y - 10
        b = Actor("tiro01", (bx, by))
        dir_sign = -1 if player.facing_left else 1
        bullets.append({
            "actor": b,
            "vx": SHOT_SPEED * dir_sign,
            "frame": 0,
            "timer": 0.0
        })
        if sound_on:
            sounds.laser.play()

    if key == keys.M:  # toggle som durante o jogo
        sound_on = not sound_on
        menu_items[1] = f"Som: {'ON' if sound_on else 'OFF'}"

    if key == keys.X:  # sair rápido durante o jogo
        raise SystemExit

# ==========================================================
# Draw
def draw_menu():
    screen.fill((12, 14, 30))
    screen.draw.text("PLATFORMER GAME", center=(WIDTH//2, 120), fontsize=68, color="white")
    y0 = 240
    for i, text in enumerate(menu_items):
        sel = (i == menu_index)
        col = "yellow" if sel else "white"
        screen.draw.text(("> " if sel else " ") + text, center=(WIDTH//2, y0 + i*54), fontsize=42, color=col)
    # instruções no menu
    screen.draw.text("Controles: ← → anda | SPACE pula | Z atira", center=(WIDTH//2, HEIGHT-100), fontsize=32, color="white")
    screen.draw.text("M som ON/OFF | X sair", center=(WIDTH//2, HEIGHT-60), fontsize=28, color="gray")

def draw():
    if state == "menu":
        draw_menu()
        return

    screen.fill((6, 7, 26))

    for p in platforms:
        screen.draw.filled_rect(p, (80, 82, 90))

    # player
    surf = _player_left[player.frame] if player.facing_left else _player_right[player.frame]
    screen.blit(surf, (player.x - surf.get_width() // 2, player.y - surf.get_height() // 2))

    # inimigos
    for e in enemies:
        e["actor"].draw()

    # tiros
    for b in bullets:
        b["actor"].draw()

    # HUD
    screen.draw.text(f"Vidas: {player.life}", topleft=(20, 12), fontsize=36, color="white")
    screen.draw.text(f"Pontos: {score}/{KILLS_TO_WIN}", topright=(WIDTH-20, 12), fontsize=36, color="yellow")

    if state == "gameover":
        screen.draw.text("GAME OVER", center=(WIDTH//2, HEIGHT//2), fontsize=72, color="red")
        screen.draw.text("Pressione R para Reiniciar | X para Sair", center=(WIDTH//2, HEIGHT//2+60), fontsize=40, color="white")
    elif state == "victory":
        screen.draw.text("VOCÊ VENCEU!", center=(WIDTH//2, HEIGHT//2), fontsize=72, color="lime")
        screen.draw.text("Pressione R para Jogar Novamente | X para Sair", center=(WIDTH//2, HEIGHT//2+60), fontsize=40, color="white")
