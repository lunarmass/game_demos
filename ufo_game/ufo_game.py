import arcade
import random
import math
import os
import time
import pyglet
import asyncio
import subprocess

# Local Game Controller Module Import
import digitalweight_controller

# set directory to current directory of this file
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Game Setup Constants
USE_DIGITAL_WEIGHT_CONTROLLER = False
TOTAL_GAME_TIME = 60

if USE_DIGITAL_WEIGHT_CONTROLLER:
    # process = subprocess.Popen(["python", "digitalweight_socket.py"])
    controller = digitalweight_controller.DigitalWeightController(api_url="http://127.0.0.1:8000")

# Ensure the subprocess is killed when the program exits
def cleanup():
    print("Exiting UFO game...")
    if USE_DIGITAL_WEIGHT_CONTROLLER:
        controller.cleanup()  # Add this line to cleanup the controller
        # process.terminate()
        # process.wait()
    print("UFO game exited successfully")

# Game Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
COW_SCALING = 0.075
RACCOON_SCALING = 0.017
CRAFT_SCALING = 0.2
CRAFT_MAX_SPEED_X = 12
CRAFT_MAX_SPEED_Y = 6
CRAFT_ACCELERATION_X = 0.2
CRAFT_ACCELERATION_Y = 0.3
CRAFT_MAX_ANGLE = 25
CRAFT_GRAVITY = 0.05
COW_SPEED = 1
COW_GRAVITY = 0.09
TRACTOR_BEAM_STRENGTH = 0.2
WHITE = arcade.color.WHITE
BLACK = arcade.color.BLACK
PULSE_FREQUENCY = 80
PULSE_WIDTH = .5
TRACTOR_BEAM_WIDTH_START = 8
TRACTOR_BEAM_WIDTH_END = 35
EXPLOSION_VELOCITY_THRESHOLD = 4
VIRTUAL_VELOCITY_THRESHOLD = 15
GROUND_LEVEL = 15


game_start_chime = "sfx/start_bender.mp3"
intro_music = "sfx/music_intro.wav"
game_music = "sfx/music_game.wav"
game_end_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("end")]
game_loss_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("loss")]
game_score_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("score")]
game_intro_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("intro")]
game_ouch_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("ouch")]
game_heckle_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("heckle")]
# game_heavy_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("heavy")]
game_animal_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("animal")]

game_crash_sounds = [f"sfx/{file}" for file in os.listdir("sfx") if file.startswith("crash")]
abducted_sound = "sfx/captured.wav"
beam_sound = "sfx/beam3.wav"
explosion_sound = "sfx/splat_nasty.wav"
landing_sound = "sfx/splat_gentle.wav"

class Explosion(arcade.Sprite):
    def __init__(self, sprite_sheet_path, rows, columns, total_frames, frame_rate, center_x, center_y):
        super().__init__()
        self.sprite_sheet_path = sprite_sheet_path
        self.rows = rows
        self.columns = columns
        self.total_frames = total_frames
        self.frame_rate = frame_rate
        self.index = 0
        self.last_update = time.time()
        self.sprite_sheet = arcade.load_texture(sprite_sheet_path)
        self.frame_width = self.sprite_sheet.width // columns
        self.frame_height = self.sprite_sheet.height // rows
        self.center_x = center_x
        self.center_y = center_y
        self.alpha = 255
        self.update_image()

    def get_image(self, index):
        if index >= self.total_frames:
            index = self.total_frames - 1
        row = index // self.columns
        col = index % self.columns
        x = col * self.frame_width
        y = row * self.frame_height
        image = arcade.load_texture(self.sprite_sheet_path, x, y, self.frame_width, self.frame_height)
        return image

    def update_image(self):
        self.texture = self.get_image(self.index)

    def update(self):
        now = time.time()
        if now - self.last_update > self.frame_rate / 1000:
            self.last_update = now
            self.index += 1
            if self.index < self.total_frames:
                self.update_image()
            else:
                self.alpha = max(0, self.alpha - 25)  # Ensure alpha does not go below 0
                if self.alpha <= 0:
                    self.kill()
                else:
                    pil_image = self.texture.image.convert("RGBA")
                    alpha_layer = pil_image.split()[3]
                    alpha_layer = alpha_layer.point(lambda p: p * self.alpha / 255)
                    pil_image.putalpha(alpha_layer)
                    self.texture.image = pil_image

class Cow(arcade.Sprite):
    def __init__(self, filename, scale, game_width, explosions_list, game):
        super().__init__(filename, scale)
        self.in_beam = False
        self.abducted = False
        self.was_off_ground = False
        self.center_y = SCREEN_HEIGHT/3
        self.center_x = random.randint(50, game_width - 50)
        self.speed_x = random.choice([-1, 1]) * COW_SPEED
        self.speed_y = 0
        self.last_direction_change = time.time()
        self.direction_change_interval = random.randint(2, 5)
        self.max_height_reached = 0
        self.game_width = game_width
        self.explosions_list = explosions_list
        self.game = game  # Add a reference to the game

        # Load textures for both directions
        self.texture_right = arcade.load_texture(filename)
        self.texture_left = arcade.load_texture(filename, mirrored=True)
        self.update_texture()

    def update_texture(self):
        if self.speed_x > 0:
            self.texture = self.texture_right
        else:
            self.texture = self.texture_left

    def apply_gravity(self):
        if not self.in_beam and not self.abducted:
            self.speed_y -= COW_GRAVITY

    def change_direction_randomly(self):
        now = time.time()
        if now - self.last_direction_change > self.direction_change_interval:
            self.last_direction_change = now
            self.direction_change_interval = random.randint(2, 5)
            self.speed_x = random.randint(-5, 5) * COW_SPEED / 5
            self.update_texture()  # Update texture based on direction

    def update_position(self):
        self.center_x += self.speed_x
        self.center_y += self.speed_y

        if self.left < 0 or self.right > self.game_width:
            self.speed_x *= -1
            self.update_texture()  # Update texture based on direction

        if self.bottom <= GROUND_LEVEL:
            kill_cow_chance = random.randint(0, 1)
            if abs(self.speed_y) > EXPLOSION_VELOCITY_THRESHOLD and self.was_off_ground and kill_cow_chance == 0:
                self.bottom = GROUND_LEVEL
                self.speed_y = 0
                self.create_explosion()
                self.kill()

            else:
                self.bottom = GROUND_LEVEL
                self.speed_y = 0
                self.was_off_ground = True

    
    def create_explosion(self):
        explosion = Explosion("assets/explosion/explosion_sprite_sheet2.png", 5, 10, 50, 20, self.center_x, self.top) # 5 rows, 10 columns, 50 frames, 20ms per frame
        self.explosions_list.append(explosion)
        arcade.play_sound(arcade.load_sound(explosion_sound))
        
        if game_loss_sounds and random.randint(0, 1) == 0:
            arcade.play_sound(arcade.load_sound(random.choice(game_loss_sounds)))
            
        self.game.cows_left -= 1  # Update cows left count
        self.game.fatalities += 1  # Update fatalities count


    def update_in_beam(self, craft_center_x):
        if USE_DIGITAL_WEIGHT_CONTROLLER:
            beam_strength = self.game.controller_data.get("virtual_velocity", 0)/25 * TRACTOR_BEAM_STRENGTH
        else:
            beam_strength = TRACTOR_BEAM_STRENGTH
        self.speed_y += beam_strength
        self.speed_x = (craft_center_x - self.center_x) * 0.01
        self.update_texture()  # Update texture based on direction
        if game_animal_sounds and random.randint(0, 3) == 0 and not self.in_beam:
            arcade.play_sound(arcade.load_sound(random.choice(game_animal_sounds)))

    def update_out_beam(self):
        self.apply_gravity()

    def update(self):
        self.apply_gravity()
        self.change_direction_randomly()
        self.max_height_reached = max(self.max_height_reached, self.center_y)
        self.update_position()

class Craft(arcade.Sprite):
    def __init__(self, filename, scale, game_width, game):
        super().__init__(filename, scale)
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT // 2
        self.change_x = 0
        self.change_y = 0
        self.angle_speed = 0
        self.angle = 0
        self.game_width = game_width
        self.beam_width_start = TRACTOR_BEAM_WIDTH_START
        self.beam_width_end = TRACTOR_BEAM_WIDTH_END
        self.brake_boost_factor = 1
        self.angle_y = 0
        self.target_angle = 0
        self.target_angle_y = 0
        self.smoothing_factor_angle = 0.1  # Define a smoothing factor for angle
        self.last_crash_time = time.time()
        self.game = game  # Add a reference to the game instance

    def apply_physics(self, keys):
        if not USE_DIGITAL_WEIGHT_CONTROLLER:
            if arcade.key.UP in keys:
                self.change_y += CRAFT_ACCELERATION_Y
            if arcade.key.DOWN in keys:
                self.change_y -= CRAFT_ACCELERATION_Y 
            if arcade.key.LEFT in keys:
                self.angle += 1
            if arcade.key.RIGHT in keys:
                self.angle -= 1
                
            # apply gravity for craft
            self.change_y -= CRAFT_GRAVITY
            
            #  if speed is opposite of angle then boost CRATF_ACCELERATION_X
            if self.angle > 0 and self.change_x < 0:
                self.brake_boost_factor = 2
            self.change_x -= CRAFT_ACCELERATION_X * self.angle / CRAFT_MAX_ANGLE * self.brake_boost_factor

            # Clamp the speed
            soft_max_speed_x = abs(CRAFT_MAX_SPEED_X * self.angle / CRAFT_MAX_ANGLE) * 0.4 + 0.6
            self.change_x = max(min(self.change_x, soft_max_speed_x), -soft_max_speed_x)
            self.change_y = max(min(self.change_y, CRAFT_MAX_SPEED_Y), -CRAFT_MAX_SPEED_Y)
        
        else:
            # Apply smoothing to the controller data
            self.angle += (self.target_angle - self.angle) * self.smoothing_factor_angle
            self.angle_y += (self.target_angle_y - self.angle_y) * self.smoothing_factor_angle

            self.change_x = -CRAFT_MAX_SPEED_X * self.angle / CRAFT_MAX_ANGLE
            self.change_y = -CRAFT_MAX_SPEED_Y * self.angle_y / CRAFT_MAX_ANGLE


    def update(self, keys):
        self.apply_physics(keys)
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Clamp the angle
        self.angle = max(min(self.angle, CRAFT_MAX_ANGLE), -CRAFT_MAX_ANGLE)

        if self.left < 0:
            self.left = 0
            self.change_x = 0
        if self.right > self.game_width:
            self.right = self.game_width
            self.change_x = 0
        if self.bottom < GROUND_LEVEL:
            self.bottom = GROUND_LEVEL
            self.change_y = 0
            time_since_crash = time.time() - self.last_crash_time
            # print("bottom crash")
            if game_ouch_sounds and time_since_crash > 1:
                self.last_crash_time = time.time()
                # print("bottom crash sound")
                arcade.play_sound(arcade.load_sound(random.choice(game_crash_sounds)))
                arcade.play_sound(arcade.load_sound(random.choice(game_crash_sounds)))
                arcade.play_sound(arcade.load_sound(random.choice(game_ouch_sounds)), volume=0.5)
                penalty = 5
                self.game.game_time -= penalty  # Deduct 5 seconds from the game time
                self.show_crash_popup(penalty)
        if self.top > SCREEN_HEIGHT:
            self.top = SCREEN_HEIGHT
            self.change_y = 0
            time_since_crash = time.time() - self.last_crash_time
            # print("top crash")
            if game_ouch_sounds and time_since_crash > 1:
                self.last_crash_time = time.time()
                # print("top crash sound")
                arcade.play_sound(arcade.load_sound(random.choice(game_crash_sounds)))
                arcade.play_sound(arcade.load_sound(random.choice(game_crash_sounds)))
                arcade.play_sound(arcade.load_sound(random.choice(game_ouch_sounds)), volume=0.5)
                penalty = 5
                self.game.game_time -= penalty  # Deduct 5 seconds from the game time
                self.show_crash_popup(penalty)
    
    def show_crash_popup(self, penalty):
        self.game.crash_popups.clear()
        popup_text = f"Crash Penalty: -{penalty}s"
        popup_position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.game.crash_popups.append(CrashPopup(popup_text))

    def draw_tractor_beam(self):
        inner_color = (255, 0 , 255, 180)
        outer_color = (5, 45, 198, 50)

        pulsate_factor = (math.sin(time.time() * PULSE_FREQUENCY) + 1) / 2 * PULSE_WIDTH + 1
        height_factor_start = 1 + 8 * ((SCREEN_HEIGHT-self.top)/SCREEN_HEIGHT)
        height_factor_end = 1 + 20 * ((SCREEN_HEIGHT-self.top)/SCREEN_HEIGHT)
        width_start = TRACTOR_BEAM_WIDTH_START * height_factor_start
        width_end = TRACTOR_BEAM_WIDTH_END * height_factor_end
        self.beam_width_start = width_start
        self.beam_width_end = width_end

        angle_rad = math.radians(self.angle)
        beam_length = SCREEN_HEIGHT + 2 * abs(self.angle)
        # beam should start just above bottom of craft.. due to rotation of craft we need to adjust the start point by calculating x, y of true craft bottom
        craft_bottom_x = self.center_x + int(self.height/3 * math.sin(math.radians(self.angle)))
        craft_bottom_y = self.center_y - int(self.height/3 * math.cos(math.radians(self.angle)))
        beam_start_x = craft_bottom_x
        beam_start_y = craft_bottom_y

        beam_end_x = beam_start_x + int(beam_length * math.sin(angle_rad))
        beam_end_y = beam_start_y - int(beam_length * math.cos(angle_rad))

        outer_points = [
            (beam_start_x - int(width_start * pulsate_factor), beam_start_y),
            (beam_start_x + int(width_start * pulsate_factor), beam_start_y),
            (beam_end_x + int(width_end * pulsate_factor), beam_end_y),
            (beam_end_x - int(width_end * pulsate_factor), beam_end_y)
        ]
        arcade.draw_polygon_filled(outer_points, outer_color)

        inner_points = [
            (beam_start_x - int(width_start * pulsate_factor * 0.5), beam_start_y),
            (beam_start_x + int(width_start * pulsate_factor * 0.5), beam_start_y),
            (beam_end_x + int(width_end * pulsate_factor * 0.5), beam_end_y),
            (beam_end_x - int(width_end * pulsate_factor * 0.5), beam_end_y)
        ]
        arcade.draw_polygon_filled(inner_points, inner_color)

        return beam_start_x, beam_start_y, beam_end_x, beam_end_y, angle_rad

class CrashPopup:
    def __init__(self, text):
        self.text = text
        self.creation_time = time.time()
        self.duration = 2  # Popup duration in seconds
    
    def draw(self, viewport_center_x, viewport_center_y):
        elapsed_time = time.time() - self.creation_time
        if elapsed_time > self.duration:
            return

        # Calculate pulsating scale
        pulse_scale = 1 + 0.15 * math.sin(elapsed_time * 5 * math.pi)
        
        # Draw the dark red, slightly transparent background with pulsating effect
        background_width = 300 * pulse_scale
        background_height = 50 * pulse_scale
        arcade.draw_rectangle_filled(viewport_center_x, viewport_center_y, background_width, background_height, (255, 0, 0, 150))
        
        # Draw the text on top of the background
        arcade.draw_text(self.text, viewport_center_x, viewport_center_y, arcade.color.WHITE, 24 * pulse_scale, anchor_x="center", anchor_y="center")

class ScorePopup:
    def __init__(self, text, position):
        self.text = text

        # Randomize offsets so we don't get overlapping popups
        random_offset_x = (random.randint(0, 1) * 2 - 1) * ((random.randint(0, 2)) * 30 + 40)
        random_offset_y = -(random.randint(0, 2)) * 30 - 20
        self.position = (position[0] + random_offset_x, position[1] + random_offset_y)

        self.creation_time = time.time()

    def draw(self):
        # Draw the dark, slightly transparent background
        background_width = 60
        background_height = 30
        arcade.draw_rectangle_filled(self.position[0], self.position[1], background_width, background_height, (0, 0, 0, 150))
        # Draw the text on top of the background
        arcade.draw_text(self.text, self.position[0], self.position[1], arcade.color.WHITE, 18, anchor_x="center", anchor_y="center")

class VelocityDisplay:
    def __init__(self):
        self.creation_time = time.time()

    def draw(self, velocity, viewport_center_x, viewport_top_y):
        elapsed_time = time.time() - self.creation_time

        # Determine background color and pulsating scale based on velocity
        if velocity < VIRTUAL_VELOCITY_THRESHOLD:
            background_color = (255, 0, 0, 200)  # Red color
            pulse_scale = 1 + 0.15 * math.sin(elapsed_time * 5 * math.pi)
        else:
            # background_color = (0, 0, 0, 150)  # Default color
            # use color purple for high velocity
            background_color = (255, 0, 255, 200)
            pulse_scale = 1 + 0.05 * math.sin(elapsed_time * 1 * math.pi)
        
        # Draw the circle background with pulsating effect
        background_radius = 50 * pulse_scale
        arcade.draw_circle_filled(viewport_center_x, viewport_top_y - 30, background_radius, background_color)
        
        # Draw the velocity text on top of the background
        text_size = 24 * pulse_scale
        arcade.draw_text(f"SPEED: {velocity:.2f}", viewport_center_x, viewport_top_y - 30, arcade.color.WHITE, text_size, anchor_x="center", anchor_y="center")

class ControllerState:
    def __init__(self):
        self.set_force_data = {
            "type": "off", # off, constant, linear
            "strength": int(0),
            "start_strength": int(0),
            "start_position": float(0),
            "saturation_position": float(1),
        }
        self.set_row_data = {
            "type": "off", # off, on
            "damping": int(20),
            "gear_ratio": int(5),
            "inertia": int(0),
        }
        self.set_pulse_data = {
            "type": "off", # off, on
            "duration": int(0),
            "strength": int(50),
            "frequency": int(16),
        }

    def update_set_force(self, type, strength, start_strength, start_position, saturation_position):
        self.set_force_data["type"] = type
        self.set_force_data["strength"] = int(strength)
        self.set_force_data["start_strength"] = int(start_strength)
        self.set_force_data["start_position"] = float(start_position)
        self.set_force_data["saturation_position"] = float(saturation_position)

    def update_set_row(self, type, damping, gear_ratio, inertia):
        self.set_row_data["type"] = type
        self.set_row_data["damping"] = int(damping)
        self.set_row_data["gear_ratio"] = int(gear_ratio)
        self.set_row_data["inertia"] = int(inertia)

    def update_set_pulse(self, type, duration, strength, frequency):
        self.set_pulse_data["type"] = type
        self.set_pulse_data["duration"] = int(duration)
        self.set_pulse_data["strength"] = int(strength)
        self.set_pulse_data["frequency"] = int(frequency)

class CowAbductionGame(arcade.Window):
    def __init__(self, monitor_index=2):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Cow Abduction Game", fullscreen=True)
        arcade.set_background_color(arcade.color.BLACK)
        self.cleanup = cleanup
        self.monitor_index = monitor_index  # Store the desired monitor index
        self.is_fullscreen = False
        self.state = "start_screen"
        self.score = 0
        self.cows_left = 30
        self.fatalities = 0
        self.start_screen_image = arcade.load_texture("intro/start_screen.png")
        self.start_screen_image_reveal = arcade.load_texture("intro/start_screen_reveal.png")
        self.newspaper_images = [
            arcade.load_texture("intro/news1.webp"),
            arcade.load_texture("intro/news2.webp"),
            arcade.load_texture("intro/author.png")
        ]
        self.transition_image_index = 0
        self.transition_start_time = None
        self.transition_image_duration = [0.9, 0.7, 0.7]
        self.game_time = TOTAL_GAME_TIME
        self.keys = set()
        self.score_popups = []
        self.crash_popups = []
        self.velocity_display = VelocityDisplay()

        self.background = arcade.load_texture(random.choice([f"bkg/{file}" for file in os.listdir("bkg") if file.endswith(".png")]))
        self.background_width = self.background.width
        self.background_height = self.background.height
        self.game_width = self.background_width
        self.game_height = SCREEN_HEIGHT

        self.craft = Craft("assets/craft2b.png", CRAFT_SCALING, self.game_width, self)
        self.cows_list = arcade.SpriteList()
        self.explosions_list = arcade.SpriteList()


        # Load tractor beam sound with pyglet
        self.tractor_beam_sound = pyglet.media.load(beam_sound, streaming=False)
        self.tractor_beam_player = pyglet.media.Player()
        self.tractor_beam_player.queue(self.tractor_beam_sound)
        self.tractor_beam_player.loop = True

        self.view_left = 0
        self.view_bottom = 0
        self.update_counter = 0

        self.last_beam_sound_update = time.time()
        self.highest_score_set = False
        self.record_high_score = 0
        self.load_high_score()
        self.game_run_index = 0
        self.load_game_run_index()
        self.loop_count = 0
        self.last_play_time = time.time()
        self.controller_state = ControllerState()

        self.controller_data = {
            "lean_angle_up": None,
            "lean_angle_left": None,
            "angular_velocity": None,
            "force": None,
            "position": None,
            "velocity": None,
            "virtual_velocity": None,
            "status": None,
        }

        self.game_mode = "normal"
        self.set_game_mode()
        self.set_controller_to_start()

    def generate_animal(self, image, scale, instances):
        # clear existing animals
        self.cows_list = arcade.SpriteList()
        for _ in range(instances):
            cow = Cow(image, scale, self.game_width, self.explosions_list, self)
            self.cows_list.append(cow)
    
    def set_game_mode(self, enable_intro=True):
        # Sound constants
        global game_start_chime, intro_music, game_end_sounds, game_loss_sounds, game_score_sounds, game_intro_sounds, game_ouch_sounds, game_heckle_sounds, game_animal_sounds
        global abducted_sound, beam_sound, explosion_sound, landing_sound, game_music

        if self.game_mode == "normal":
            # set sounds
            game_start_chime = "sfx/start_bender.mp3"
            game_music = "sfx/music_game.wav"
            game_end_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("end")]
            game_loss_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("loss")]
            game_score_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("score")]
            game_intro_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("intro")]
            game_ouch_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("ouch")]
            game_heckle_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("heckle")]
            # game_heavy_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("heavy")]
            game_animal_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("animal")]

            abducted_sound = "sfx/captured.wav"
            beam_sound = "sfx/beam3.wav"
            explosion_sound = "sfx/splat_nasty.wav"
            landing_sound = "sfx/splat_gentle.wav"

            # set game images (craft, animals, background)
            self.craft = Craft("assets/craft2b.png", CRAFT_SCALING, self.game_width, self)
            self.generate_animal("assets/cow.png", COW_SCALING, 30)
            
            
            self.newspaper_images = [
                arcade.load_texture("intro/news1.webp"),
                arcade.load_texture("intro/news2.webp"),
                arcade.load_texture("intro/author.png")
            ]
            
            self.background = arcade.load_texture(random.choice([f"bkg/{file}" for file in os.listdir("bkg") if file.endswith(".png")]))
        
        
        elif self.game_mode == "raccoon":
            # set sounds
            game_start_chime = "sfx/william/balls.wav"
            game_music = "sfx/william/music_game.wav"
            game_end_sounds = [f"sfx/william/{file}" for file in os.listdir("sfx/william") if file.startswith("end")]
            game_loss_sounds = [f"sfx/william/{file}" for file in os.listdir("sfx/william") if file.startswith("loss")]
            game_score_sounds = [f"sfx/william/{file}" for file in os.listdir("sfx/william") if file.startswith("score")]
            game_intro_sounds = [f"sfx/william/{file}" for file in os.listdir("sfx/william") if file.startswith("intro")]
            game_ouch_sounds = [f"sfx/william/{file}" for file in os.listdir("sfx/william") if file.startswith("ouch")]
            game_heckle_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("heckle")]
            # game_heavy_sounds = [f"sfx/bender/{file}" for file in os.listdir("sfx/bender") if file.startswith("heavy")]
            game_animal_sounds = [f"sfx/william/{file}" for file in os.listdir("sfx/william") if file.startswith("animal")]

            abducted_sound = "sfx/captured.wav"
            beam_sound = "sfx/beam3.wav"
            explosion_sound = "sfx/splat_nasty.wav"
            landing_sound = "sfx/splat_gentle.wav"

            # set game images (craft, animals, background)
            self.craft = Craft("assets/craft5w.png", CRAFT_SCALING*2, self.game_width, self)
            self.generate_animal("william/raccoon0.png", RACCOON_SCALING, 30)
            
            
            self.newspaper_images = [
                arcade.load_texture("intro/coon_news0.webp"),
                arcade.load_texture("intro/coon_news1.webp"),
                arcade.load_texture("intro/author.png")
            ]
            
            self.background = arcade.load_texture(random.choice([f"bkg/{file}" for file in os.listdir("bkg") if file.endswith(".png")]))
        

        if enable_intro:
            self.background_music_player = arcade.play_sound(arcade.load_sound(intro_music), volume=0, looping=True)
        
        self.game_time = TOTAL_GAME_TIME

    
    def load_game_run_index(self):
        try:
            with open("game_run_index.txt", "r") as file:
                self.game_run_index = int(file.read())
        except FileNotFoundError:
            pass

    def load_high_score(self):
        try:
            with open("high_score.txt", "r") as file:
                self.record_high_score = int(file.read())
        except FileNotFoundError:
            pass
    
    def save_high_score(self):
        with open("high_score.txt", "w") as file:
            file.write(str(self.record_high_score))

    def on_close(self):
        self.cleanup()
        super().on_close()


    def on_draw(self):
        arcade.start_render()
        if self.state == "start_screen":
            self.draw_start_screen()
        elif self.state == "transition":
            self.draw_transition_screen()
        elif self.state == "game":
            self.draw_background()
            if USE_DIGITAL_WEIGHT_CONTROLLER:
                if self.controller_data["virtual_velocity"] is not None and self.controller_data["virtual_velocity"] > VIRTUAL_VELOCITY_THRESHOLD:
                    self.craft.draw_tractor_beam()
                    # only update every 0.2 seconds to prevent sound lag
                    if time.time() - self.last_beam_sound_update > 0.2:
                        self.update_tractor_beam_pitch((self.controller_data["virtual_velocity"]-VIRTUAL_VELOCITY_THRESHOLD/3)/(VIRTUAL_VELOCITY_THRESHOLD))  # Update pitch based on height
                        self.last_beam_sound_update = time.time()
                    if not self.tractor_beam_player.playing:
                        self.tractor_beam_player.play()
                else:
                    if self.tractor_beam_player.playing:
                        self.tractor_beam_player.pause()
            else:
                if arcade.key.SPACE in self.keys:
                    self.craft.draw_tractor_beam()
                    # only update every 0.2 seconds to prevent sound lag
                    if time.time() - self.last_beam_sound_update > 0.2:
                        self.update_tractor_beam_pitch()  # Update pitch based on height
                        self.last_beam_sound_update = time.time()
                    if not self.tractor_beam_player.playing:
                        self.tractor_beam_player.play()
                else:
                    if self.tractor_beam_player.playing:
                        self.tractor_beam_player.pause()
            self.cows_list.draw()
            self.explosions_list.draw()
            self.draw_score()
            self.draw_timer()
            self.craft.draw()
            for popup in self.score_popups:
                popup.draw()
            for popup in self.crash_popups:
                popup.draw(SCREEN_WIDTH / 2 + self.view_left, SCREEN_HEIGHT / 2 + self.view_bottom)
                
            # Draw the velocity display
            if self.controller_data["virtual_velocity"] is not None:
                self.velocity_display.draw(self.controller_data["virtual_velocity"], SCREEN_WIDTH / 2 + self.view_left, SCREEN_HEIGHT + self.view_bottom)

        elif self.state == "end_screen":
            self.show_end_screen()

    def update_tractor_beam_pitch(self, pitch=None):
        if pitch is None:
            pitch = 1.5 - (self.craft.center_y / SCREEN_HEIGHT)
        self.tractor_beam_player.pitch = max(0.2, min(2, pitch))  # Limit pitch range to avoid distortion
        # set volume to avoid distortion
        self.tractor_beam_player.volume = max(0.4, min(1, pitch))

    def draw_background(self):
        # Draw the background image, tiling if necessary
        arcade.draw_lrwh_rectangle_textured(0, 0, self.game_width, self.game_height, self.background)

    def draw_start_screen(self):
        left, right, bottom, top = arcade.get_viewport()
        width, height = right - left, top - bottom

        # Calculate fade-in and fade-out alpha value
        time_elapsed = time.time() % 2  # Cycle every 2 seconds
        alpha = int(((math.sin(time_elapsed * math.pi) + 1) * 0.25 + 0.5) * 255)

        # Dynamic text size based on viewport height
        text_size = int(height * 0.1)  # 10% of viewport height
        if USE_DIGITAL_WEIGHT_CONTROLLER:
            text = "LIFT to START"
        else:
            text = "PRESS SPACE to START"
        text_x = width / 2 + left
        text_y = height / 2.5 + bottom
        text_osman = "RACCOON MODE!"

        # Calculate text width and height for the background
        text_width = text_size * len(text) * 0.75  # Estimate text width
        text_height = text_size * 1.5
        background_color = (0, 0, 0, alpha)  # Slightly transparent black


        rev_image_width, rev_image_height = self.start_screen_image_reveal.width, self.start_screen_image_reveal.height
        rev_aspect_ratio = rev_image_width / rev_image_height
        rev_scaled_width = height*.5 * rev_aspect_ratio

        image_width, image_height = self.start_screen_image.width, self.start_screen_image.height
        aspect_ratio = image_width / image_height
        scaled_width = height * aspect_ratio

        if USE_DIGITAL_WEIGHT_CONTROLLER and self.controller_data["position"]:
            ypos_offset = max((self.controller_data["position"] * 250) - 50, 0) * 0.5
        else:
            ypos_offset = 0

        # ensure ypos_offset is not NaN
        if math.isnan(ypos_offset):
            ypos_offset = 0

        play_timout = time.time() - self.last_play_time
        if ypos_offset > 0 and self.controller_data["velocity"] and self.controller_data["velocity"] < 1 and random.randint(0, 100) == 0 and play_timout > 3:
            self.last_play_time = time.time()
            arcade.play_sound(arcade.load_sound(random.choice(game_heckle_sounds)))

        arcade.draw_lrwh_rectangle_textured((width - rev_scaled_width) / 2, bottom + ypos_offset, rev_scaled_width, height*.5, self.start_screen_image_reveal)

        # Draw the text background for raccoon mode
        arcade.draw_text(text_osman, text_x, bottom + ypos_offset - 50, (255, 255, 255, alpha), text_size, anchor_x="center", anchor_y="center")

        arcade.draw_lrwh_rectangle_textured((width - scaled_width) / 2, bottom - 2*ypos_offset, scaled_width, height, self.start_screen_image)

        # Draw the text background
        arcade.draw_rectangle_filled(text_x, text_y - ypos_offset, text_width, text_height, background_color)

        # Draw the text with fade-in and fade-out effect
        arcade.draw_text(text, text_x, text_y- ypos_offset, (255, 255, 255, alpha), text_size, anchor_x="center", anchor_y="center")


    def draw_transition_screen(self):
        if self.transition_image_index < len(self.newspaper_images):
            left, right, bottom, top = arcade.get_viewport()
            width, height = right - left, top - bottom
            image = self.newspaper_images[self.transition_image_index]
            image_width, image_height = image.width, image.height

            # Calculate the aspect ratio of the image
            aspect_ratio = image_width / image_height
            scaled_width = height * aspect_ratio
            arcade.draw_lrwh_rectangle_textured((width - scaled_width) / 2, 0, scaled_width, height, image)
            now = time.time()
            if now - self.transition_start_time > self.transition_image_duration[self.transition_image_index]:
                self.transition_image_index += 1
                self.transition_start_time = now
        else:
            self.state = "game"
            self.start_time = time.time()
            arcade.stop_sound(self.background_music_player)
            arcade.play_sound(arcade.load_sound(random.choice(game_intro_sounds)))
            self.background_music_player = arcade.play_sound(arcade.load_sound(game_music), volume=1, looping=True)


    def draw_score(self):
        offset = 30
        start_x = 20 + self.view_left
        # Draw slightly transparent background for the scores
        arcade.draw_rectangle_filled(start_x + 125 - 20, SCREEN_HEIGHT - offset*2, 250, offset*4.5, (0, 0, 0, 200))
        arcade.draw_text(f"High Score: {self.record_high_score}", start_x, SCREEN_HEIGHT - offset*0.8 + self.view_bottom, WHITE, 18, bold=True)
        arcade.draw_text(f"Score: {self.score}", start_x, SCREEN_HEIGHT - offset*2 + self.view_bottom, WHITE, 22, bold=True)
        arcade.draw_text(f"Cows Left: {self.cows_left}", start_x, SCREEN_HEIGHT - offset*3 + self.view_bottom, WHITE, 22, bold=True)
        arcade.draw_text(f"Fatalities: {self.fatalities}", start_x, SCREEN_HEIGHT - offset*4 + self.view_bottom, WHITE, 22, bold=True)
        
    def draw_timer(self):
        time_left = int(self.game_time - (time.time() - self.start_time))
        # Draw slightly transparent background for the time
        arcade.draw_rectangle_filled(SCREEN_WIDTH - 100 + self.view_left, SCREEN_HEIGHT - 35 + self.view_bottom, 200, 100, (0, 0, 0, 200))
        arcade.draw_text(f"Time Left:", SCREEN_WIDTH - 270 + self.view_left, SCREEN_HEIGHT - 40 + self.view_bottom, WHITE, 22, align="right", width=250, bold=True)
        arcade.draw_text(f"{time_left}s", SCREEN_WIDTH - 270 + self.view_left, SCREEN_HEIGHT - 70 + self.view_bottom, WHITE, 22, align="right", width=250, bold=True)

    def on_update(self, delta_time):
        if USE_DIGITAL_WEIGHT_CONTROLLER and self.state == "start_screen":
            if self.controller_data["position"] and self.controller_data["position"] > 2.5 and self.controller_data["velocity"] and self.controller_data["velocity"] > 1:
                self.game_mode = "normal"
                self.set_game_mode(False)
                self.start_game()
            elif self.controller_data["position"] and self.controller_data["position"] > 3.5:
                self.game_mode = "raccoon"
                self.set_game_mode(False)
                self.start_game()

        # get controller data every 6th frame
        self.update_counter += 1
        if USE_DIGITAL_WEIGHT_CONTROLLER and self.update_counter % 2 == 0:
            self.get_controller_data()
            # print(self.controller_data)
            if self.controller_data["position"] and self.controller_data["position"] > 1.5:
                self.keys.add(arcade.key.SPACE)
            else:
                if arcade.key.SPACE in self.keys:
                    self.keys.remove(arcade.key.SPACE)

            # set the craft angle based on the controller data
            if self.controller_data["lean_angle_up"]:
                self.craft.target_angle_y = -1.5 * self.controller_data["lean_angle_up"]
            if self.controller_data["lean_angle_left"]:
                self.craft.target_angle = -2 * self.controller_data["lean_angle_left"]
        
        # if USE_DIGITAL_WEIGHT_CONTROLLER and self.update_counter % 5 == 0:
        #     controller.set_force(self.controller_state.set_force_data["type"], self.controller_state.set_force_data["strength"], self.controller_state.set_force_data["start_strength"], self.controller_state.set_force_data["start_position"], self.controller_state.set_force_data["saturation_position"])
        # if USE_DIGITAL_WEIGHT_CONTROLLER and self.update_counter % 7 == 0:
        #     controller.set_row(self.controller_state.set_row_data["type"], self.controller_state.set_row_data["damping"], self.controller_state.set_row_data["gear_ratio"], self.controller_state.set_row_data["inertia"])
        # if USE_DIGITAL_WEIGHT_CONTROLLER and self.update_counter % 11 == 0:
        #     controller.set_pulse(self.controller_state.set_pulse_data["type"], self.controller_state.set_pulse_data["duration"], self.controller_state.set_pulse_data["strength"], self.controller_state.set_pulse_data["frequency"])
        
            
        if self.state == "start_screen":
            return

        if self.state == "game":
            self.cows_list.update()
            self.explosions_list.update()
            self.craft.update(self.keys)
            self.update_cows()
            self.scroll_viewport()

            self.crash_popups = [popup for popup in self.crash_popups if time.time() - popup.creation_time < 2]
            self.score_popups = [popup for popup in self.score_popups if time.time() - popup.creation_time < 1]

            if time.time() - self.start_time > self.game_time or self.cows_left <= 0:
                self.state = "end_screen"
                arcade.stop_sound(self.background_music_player)
                # stop tractor beam sound
                self.tractor_beam_player.pause()
                arcade.play_sound(arcade.load_sound(random.choice(game_end_sounds)))

    def start_game(self):
        self.highest_score_set = False
        if USE_DIGITAL_WEIGHT_CONTROLLER:
            self.controller_state.update_set_pulse("off", 3, 100, 20)
            self.controller_state.update_set_row("on", 20, 3, 0)
            self.controller_state.update_set_force("constant", 100, 0, 0.5, 2.5)
        self.state = "transition"
        self.transition_start_time = time.time()
        arcade.stop_sound(self.background_music_player)
        arcade.play_sound(arcade.load_sound(game_start_chime))
        

    def on_key_press(self, key, modifiers):
        if self.state == "start_screen" and key == arcade.key.SPACE:
            self.game_mode = "normal"
            self.set_game_mode(False)
            self.start_game()
        elif self.state == "start_screen" and key == arcade.key.W:
            self.game_mode = "raccoon"
            self.set_game_mode(False)
            self.start_game()
        elif (self.state == "start_screen" or self.state == "end_screen") and key == arcade.key.ESCAPE:
            self.toggle_fullscreen(self.monitor_index)

            
        elif self.state == "end_screen":
            if key == arcade.key.ENTER:
                self.highest_score_set = False
                self.restart_game()
            elif key == arcade.key.X:
                self.last_play_time = time.time()
                self.highest_score_set = False
                self.state = "start_screen"
                self.score = 0
                self.cows_left = 30
                self.fatalities = 0
                self.transition_image_index = 0
                self.transition_start_time = None
                self.game_mode = "normal"
                self.set_game_mode()
                self.set_controller_to_start()
        elif key == arcade.key.ESCAPE:
            self.toggle_fullscreen(self.monitor_index)
        else:
            self.keys.add(key)
            if key == arcade.key.SPACE and not self.tractor_beam_player.playing:
                self.tractor_beam_player.play()

    def on_key_release(self, key, modifiers):
        if key in self.keys:
            self.keys.remove(key)
            if key == arcade.key.SPACE and self.tractor_beam_player.playing:
                self.tractor_beam_player.pause()

    def get_controller_data(self):
        controller.enqueue_task(controller.get_controller_data())  # Enqueue the task in the controller
        while not controller.data_queue.empty():
            controller_data = asyncio.run(controller.data_queue.get())
            self.controller_data = controller_data

    def set_controller_to_start(self):
        self.controller_state.update_set_pulse("off", 3, 100, 10)
        self.controller_state.update_set_row("on", 20, 3, 0)
        self.controller_state.update_set_force("constant", 100, 0, 0.5, 2.5)

    def toggle_fullscreen(self, monitor_index=2):
        self.is_fullscreen = not self.is_fullscreen
        display = pyglet.canvas.get_display()
        screens = display.get_screens()
        screen = screens[monitor_index]
        self.set_fullscreen(self.is_fullscreen, screen)

        if self.is_fullscreen:
            # Adjust the viewport for fullscreen mode
            screen_width, screen_height = screen.width, screen.height
            self.set_viewport(0, screen_width, 0, screen_height)
        else:
            # Adjust the viewport for windowed mode
            self.set_viewport(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT)

    def update_cows(self):
        beam_start_x, beam_start_y, beam_end_x, beam_end_y, angle_rad = self.craft.draw_tractor_beam()
        outer_points = [
            (beam_start_x - self.craft.beam_width_start // 2, beam_start_y),
            (beam_start_x + self.craft.beam_width_start // 2, beam_start_y),
            (beam_end_x + self.craft.beam_width_end // 2, beam_end_y),
            (beam_end_x - self.craft.beam_width_end // 2, beam_end_y)
        ]

        for cow in self.cows_list:
            if USE_DIGITAL_WEIGHT_CONTROLLER and self.controller_data["virtual_velocity"] and self.controller_data["virtual_velocity"] > VIRTUAL_VELOCITY_THRESHOLD:
                beam_active = True
            elif arcade.key.SPACE in self.keys:
                beam_active = True
            else:
                beam_active = False

            is_in_beam = beam_active and arcade.is_point_in_polygon(cow.center_x, cow.center_y, outer_points)
            if is_in_beam:
                cow.update_in_beam(self.craft.center_x)
                cow.in_beam = True
            elif cow.in_beam:
                cow.update_out_beam()
                cow.in_beam = False

            if arcade.key.SPACE in self.keys and cow.center_y <= (self.craft.top) and cow.center_y >= self.craft.center_y and cow.center_x >= self.craft.left and cow.center_x <= self.craft.right:
                cow.abducted = True
                score = 1 + int((10 * (cow.center_y / SCREEN_HEIGHT)) ** 2)
                self.score += score
                self.cows_left -= 1
                cow.kill()
                self.score_popups.append(ScorePopup(f"+{score}", (self.craft.center_x, self.craft.center_y)))
                arcade.play_sound(arcade.load_sound(abducted_sound))
                if random.random() < 0.5:
                    arcade.play_sound(arcade.load_sound(random.choice(game_score_sounds)))
                break
            
            cow.update()

    def scroll_viewport(self):
        left_boundary = self.view_left + SCREEN_WIDTH * 0.4
        right_boundary = self.view_left + SCREEN_WIDTH * 0.6

        if self.craft.center_x < left_boundary:
            self.view_left -= left_boundary - self.craft.center_x
        elif self.craft.center_x > right_boundary:
            self.view_left += self.craft.center_x - right_boundary

        self.view_left = max(0, self.view_left)
        self.view_left = min(self.background_width - SCREEN_WIDTH, self.view_left)

        arcade.set_viewport(self.view_left, self.view_left + SCREEN_WIDTH, self.view_bottom, self.view_bottom + SCREEN_HEIGHT)

    def show_end_screen(self):
        self.set_viewport(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT)  # Reset viewport
        self.clear()
        arcade.set_background_color(arcade.color.BLACK)
        arcade.start_render()
        if self.game_mode == "raccoon":
            # draw self.start_screen_image_reveal but flipped upside down and shrunk to 30%
            left, right, bottom, top = arcade.get_viewport()
            width, height = right - left, top - bottom
            rev_image_width, rev_image_height = self.start_screen_image_reveal.width, self.start_screen_image_reveal.height
            rev_aspect_ratio = rev_image_width / rev_image_height
            rev_scaled_width = height * 0.3 * rev_aspect_ratio
            # Draw the image flipped upside down
            arcade.draw_lrwh_rectangle_textured((width - rev_scaled_width) / 2, top - height * 0.3, rev_scaled_width, height * 0.3, self.start_screen_image_reveal, angle=180)
        
        if self.score >= self.record_high_score and self.loop_count == 0:
            self.highest_score_set = True
            self.record_high_score = self.score
            self.save_high_score()
            self.loop_count += 1
        elif self.score < self.record_high_score and self.loop_count == 0:
            self.loop_count += 1
            self.highest_score_set = False
        if self.tractor_beam_player.playing:
            self.tractor_beam_player.pause()
        arcade.draw_text("Game Over", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.7, WHITE, 70, anchor_x="center")
        if self.highest_score_set:
            arcade.draw_text(f"Congrats! New High Score!", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.55, WHITE, 60, anchor_x="center")
            arcade.draw_text(f"Your Final Score: {self.score}", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.45, WHITE, 36, anchor_x="center")
        else:
            arcade.draw_text(f"Your Final Score: {self.score}", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.55, WHITE, 36, anchor_x="center")
            arcade.draw_text(f"High Score: {self.record_high_score}", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.45, WHITE, 24, anchor_x="center")
        arcade.draw_text(f"Cows Left: {self.cows_left}", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.35, WHITE, 24, anchor_x="center")
        arcade.draw_text(f"Fatalities: {self.fatalities}", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.3, WHITE, 24, anchor_x="center")
        arcade.draw_text("Press ENTER to Restart or X to return to Start Screen", SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.2, WHITE, 24, anchor_x="center")

    def restart_game(self):
        self.loop_count = 0
        self.highest_score = False
        self.state = "game"
        self.score = 0
        self.cows_left = 30
        self.fatalities = 0
        self.start_time = time.time()
        # self.craft = Craft("craft2b.png", CRAFT_SCALING, self.game_width)
        # self.cows_list = arcade.SpriteList()
        self.explosions_list = arcade.SpriteList()
        self.set_game_mode()
        # stop all sounds
        self.tractor_beam_player.pause()
        arcade.stop_sound(self.background_music_player)
        self.background_music_player = arcade.play_sound(arcade.load_sound(game_music), volume=1, looping=True)


def main():
    game = CowAbductionGame(monitor_index=2)  # Set the desired monitor index here
    arcade.run()

if __name__ == "__main__":
    main()
