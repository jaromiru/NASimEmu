import gym
from .env import NASimEmuEnv

gym.envs.registration.register(id='NASimEmu-v0', entry_point='nasimemu.env:NASimEmuEnv')
