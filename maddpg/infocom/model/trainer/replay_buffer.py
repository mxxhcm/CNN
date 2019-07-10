"""Code from https://github.com/tambetm/simple_dqn/blob/master/src/replay_memory.py"""

import random
import numpy as np


class ReplayBuffer:
	def __init__(self, config, obs_shape, act_space):
		self.cnn_format = config.cnn_format
		self.buffer_size = config.buffer_size
		self.dims = obs_shape
		self.history_length = config.history_length
		self.batch_size = config.batch_size
		
		self.observations = np.empty((self.buffer_size,) + obs_shape, dtype=np.float16)
		self.actions = np.empty((self.buffer_size, act_space,), dtype=np.float16)
		self.rewards = np.empty(self.buffer_size, dtype=np.float16)
		self.next_observations = np.empty((self.buffer_size,) + obs_shape, dtype=np.float16)
		self.done = np.empty(self.buffer_size, dtype=np.bool)
		
		# pre-allocate prestates and poststates for minibatch
		self.states = np.empty((self.batch_size, self.history_length) + self.dims, dtype=np.float16)
		self.next_states = np.empty((self.batch_size, self.history_length) + self.dims, dtype=np.float16)
	
		self.count = 0
		self.current = 0
	
	def __len__(self):
		return self.count
	
	def add(self, obs, action, reward, next_obs, done, terminal):
		assert obs.shape == self.dims
		# NB! screen is post-state, after action and reward
		self.observations[self.current, ...] = obs
		self.actions[self.current] = action
		self.rewards[self.current] = reward
		self.next_observations[self.current, ...] = next_obs
		self.done[self.current] = done
		
		self.count = max(self.count, self.current + 1)
		self.current = (self.current + 1) % self.buffer_size
	
	def get_obs(self, index):
		assert self.count > 0, "replay memory is empy, use at least --random_steps 1"
		# normalize index to expected range, allows negative indexes
		index = index % self.count
		# if is not in the beginning of matrix
		if index >= self.history_length - 1:
			return self.observations[(index - (self.history_length - 1)):(index + 1), ...]
		else:
			indexes = [(index - i) % self.count for i in reversed(range(self.history_length))]
			return self.observations[indexes, ...]

	def get_next_obs(self, index):
		assert self.count > 0, "replay memory is empy, use at least --random_steps 1"
		# normalize index to expected range, allows negative indexes
		index = index % self.count
		# if is not in the beginning of matrix
		if index >= self.history_length - 1:
			return self.next_observations[(index - (self.history_length - 1)):(index + 1), ...]
		else:
			indexes = [(index - i) % self.count for i in reversed(range(self.history_length))]
			return self.next_observations[indexes, ...]

	
	def sample(self):
		# memory must include poststate, prestate and history
		assert self.count > self.history_length
		# sample random indexes
		indexes = []
		while len(indexes) < self.batch_size:
			# find random index
			while True:
				index = random.randint(self.history_length, self.count - 1)					# sample one index (ignore states wraping over
				# if wraps over current pointer, then get new one
				if index >= self.current and index - self.history_length < self.current:
					continue
				# if wraps over episode end, then get new one NB! poststate (last screen) can be terminal state!
				if self.done[(index - self.history_length):index].any():
					continue
				break
			
			# NB! having index first is fastest in C-order matrices
			self.states[len(indexes), ...] = self.get_obs(index)
			self.next_states[len(indexes), ...] = self.get_next_obs(index)
			# self.next_states[len(indexes), ...] = self.getState(index+1)
			indexes.append(index)
		
		actions = self.actions[indexes]
		rewards = self.rewards[indexes]
		done = self.done[indexes]
		if self.cnn_format == 'NHWC':
			return np.transpose(self.states, (0, 2, 1)), actions, rewards, np.transpose(self.next_states, (0, 2, 1)), done
		else:
			return self.states, actions, rewards, self.next_states, done
