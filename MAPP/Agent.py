import tensorflow as tf
import numpy as np
from DQN import DQN
import ModifiedTensorBoard
import time

class Agent(tf.keras.layers.Layer):
    def __init__(self, num_actions, num_environments, model_name):
        super().__init__()

        self.network = DQN(num_actions) 
        self.delay_target_network = DQN(num_actions) 

        self.metrics_list = [tf.keras.metrics.Mean(name="loss")]

        self.num_environments = num_environments
        self.num_actions = num_actions

        self.tensorboard = ModifiedTensorBoard.ModifiedTensorBoard(log_dir="logs/{}-{}".format(model_name, int(time.time())))

    def call(self, x, training = False):
        """
        Calls Deep Q-Network to get Q-values. 

        Parameters: 
            x (ndarray): observation
        Returns: 
            x (ndarray): Q-value for every action 
        """
        x = self.network(x) 
        return x
    
    def epsilon_greedy_sampling(self, observation, epsilon = 0.05):
        """
        Epsilon-greedy sampling to balance exploration and exploitation. 

        Parameters: 
            observation (ndarray): observation
            epsilon (float): probability for exploration

        Returns:
            action (int): either action with highest Q-value (exploitation) or random action (exploration)
        """
        q_values = self(observation)
        action = [np.argmax(q_values[i]) if np.random.rand() > epsilon else np.random.randint(self.num_actions) for i in range(self.num_environments)]
        return action
    
    def fill(self, environments, timesteps, ERP, epsilon):
        """
        Fill up the Experience Replay Buffer with samples from the environment. The whole one in the first episode, afterward replace #timesteps samples.

        Parameters: 
            environment (gymnasium): the environment to get observations, take actions and get reward 
            timesteps (int): amount of new samples 
            ERP (Experience_Replay_Buffer): store the samples of size num_environments filled with 
                            [observation_t, action, reward, observation]

        Returns: 
            reward_of_epsiode (list): reward of this episode in each environment 
        """
        if ERP.experience_replay_buffer == [0] * ERP.size:
            timesteps = ERP.size
        observation = [environment.reset()[0] for environment in environments]# state = observation, do we need this every time?????????????????????????????????????

        reward_of_episode = [0] * len(environments)
        for _ in range(timesteps):
            action =  self.epsilon_greedy_sampling(observation = observation, epsilon = epsilon)

            batch = []
            for i in range(len(environments)):
                next_observation, reward, terminated, truncated, info = environments[i].step(action[i])
                reward_of_episode[i] += reward
                batch.append([observation[i], action, reward, next_observation])
                observation[i] = next_observation
            ERP.experience_replay_buffer[ERP.index] = batch
            ERP.index += 1
            if ERP.index == ERP.size:
                ERP.index = 0
            if truncated == True or terminated == True and timesteps != ERP.size:
                break

        return reward_of_episode

    
    
    
    def q_target(self, sample, discount_factor = 0.95):
        """
        Calculates Q-target (expected reward) with Delay-Target-Network.

        Parameters: 
            sample (list): list of lists each filled with [observation_t, action, reward, observation] 
            discount_factor (float): to set the influence of future rewards 

        Returns: 
            q_target (float): expected reward from "optimal" action 
        """
        observation = [sample[3] for sample in sample]
        reward = [sample[2] for sample in sample]

        q_values = self.delay_target_network(observation)
        max_q_value = [tf.math.top_k(q_values[i], k=1, sorted=True) for i in range(len(sample))]
        q_target = [reward[i] + discount_factor * max_q_value[i].values.numpy() for i in range(len(sample))]
        return q_target
    
    def update_delay_target_network(self):
        """
        Sets the weights of Delay-Target-Network.
        """
        self.delay_target_network.set_weights(self.network.get_weights())
    


 