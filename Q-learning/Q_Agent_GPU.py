#this will probably be out of date compared to the CPU version since it is much easier to debug with CPU
import numpy as np
import random
import matplotlib.pyplot as plt
import time
import tensorflow as tf #lots of setup
from Game_Library import TicTacToe as Environment

if tf.test.gpu_device_name():
    print('GPU found')
else:
    print("No GPU found. Please ensure TensorFlow is configured correctly.")
    exit()

episodes = 10000
graphStep = 100

rewards_draw = 0
rewards_win = 1
rewards_lose = -1

class RealTimePlotter:
    def __init__(self, title="Change Over Time", xlabel="Time", ylabel="Value"):
        self.fig, self.ax = plt.subplots()
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.values = []
        self.line, = self.ax.plot([], [], marker='o', linestyle='-', color='b')
        
        plt.title(self.title)
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        plt.grid(True)
        plt.ion()  # Turn on interactive mode
        
    def add_value(self, value):
        self.values.append(value)
        self.update()

    def update(self):
        self.line.set_data(range(len(self.values)), self.values)
        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def show(self):
        plt.show()

# Define the Q-learning agent
class QLearningAgent:
    def __init__(self, learning_rate=0.1, discount_factor=0.9, exploration_rate=1.0, exploration_decay=0.995):
        self.q_table = {}
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay

    def get_state(self, board):
        return tuple(board.flatten())  # Use a tuple of the flattened board as the state

    def get_q_values(self, state):
        if state not in self.q_table:
            self.q_table[state] = tf.Variable(tf.zeros([9]), dtype=tf.float32)  # Initialize Q-values for the state
        return self.q_table[state]

    def choose_action(self, state, available_moves):
        if random.random() < self.exploration_rate:
            return random.choice(available_moves)
        q_values = self.get_q_values(state).numpy()  # Convert Tensor to NumPy array for action selection
        return available_moves[np.argmax([q_values[i*3 + j] for i, j in available_moves])]

    def update_q_table(self, state, action, reward, next_state):
        with tf.device('/GPU:0'):  # Execute on GPU
            q_values = self.get_q_values(state)
            max_future_q = tf.reduce_max(self.get_q_values(next_state))
            action_index = action[0] * 3 + action[1]
            q_values[action_index].assign(
                q_values[action_index] + self.learning_rate * (reward + self.discount_factor * max_future_q - q_values[action_index]))

    def decay_exploration(self):
        self.exploration_rate *= self.exploration_decay


def test_agent(agent, games, game):
    winsCount = 0
    
    for i in range(games):
        game.reset()
        state = agent.get_state(game.board)
        while True:
            # Agent's turn
            available_moves = game.available_moves()
            action = agent.choose_action(state, available_moves)
            game.make_move(*action)
            next_state = agent.get_state(game.board)

            #check for win
            winner = game.check_winner()
            if winner is not None:
                if winner == 1:
                    winsCount += 1
                break
            
            #update state
            agent.update_q_table(state, action, 0, next_state)
            state = next_state
            
            # Random opponent's turn
            available_moves = game.available_moves()
            action = random.choice(available_moves)
            game.make_move(*action)
            next_state = agent.get_state(game.board)

            #check for win
            winner = game.check_winner()
            if winner is not None:
                if winner == 2:
                    winsCount += 1
                break
            
            #update state
            agent.update_q_table(state, action, 0, next_state)
            state = next_state
            
    return winsCount/games * 100

# Train the agent
def train_agent(episodes, graphStep, game):
    agent = QLearningAgent()
    
    #initialize plot
    #plotter = RealTimePlotter(title="Winrate vs Games played", xlabel=f"Games played (x{graphStep})", ylabel="Winrate (%)")
    #plotter.show()

    for episode in range(episodes):
        if episode%graphStep == 0:
            #plot win percent
            winPercent = test_agent(agent, graphStep, game)
            print(winPercent)
            #plotter.add_value(winPercent)
            #plotter.update()
        
        #start game
        game.reset()
        state = agent.get_state(game.board)
        while True:
            # Agent's turn
            available_moves = game.available_moves()
            action = agent.choose_action(state, available_moves)
            game.make_move(*action)
            next_state = agent.get_state(game.board)
            winner = game.check_winner()

            if winner is not None:
                if winner == 1:
                    reward = rewards_win
                elif winner == 2:
                    reward = rewards_lose
                else:
                    reward = rewards_draw
                agent.update_q_table(state, action, reward, next_state)
                break
            else:
                agent.update_q_table(state, action, 0, next_state)
                state = next_state

        agent.decay_exploration()
    return agent

# Play a game against the trained agent
def play_game(agent, game):
    #agent vs human:
    playAgain = True
    while playAgain:
        print("Welcome to Tic-Tac-Toe against the Q-learning Agent!")
        print("You are playing as 'O'. Enter your moves in the format 'row,col'. For example, '1,2' for the second row and third column.")

        game.reset()
        state = agent.get_state(game.board)
        while True:
            # Print the current board state
            print(game.board,"\n")

            # Human player's turn
            if game.current_player == 2:
                while True:
                    try:
                        move = input("Enter your move (row,col): ")
                        row, col = map(int, move.split(','))
                        if (row, col) in game.available_moves():
                            break
                        else:
                            print("Invalid move. Try again.")
                    except ValueError:
                        print("Invalid input format. Please enter row,col (e.g., '1,2').")

                game.make_move(row, col)
                state = agent.get_state(game.board)
            else:
                # Agent's turn
                available_moves = game.available_moves()
                action = agent.choose_action(state, available_moves)
                game.make_move(*action)
                state = agent.get_state(game.board)

            winner = game.check_winner()
            if winner is not None:
                print(game.board)
                if winner == 1:
                    print("Agent wins!")
                elif winner == 2:
                    print("Human wins!")
                else:
                    print("It's a draw!")
                break

        print("Game Over!")
        playAgain = input("y to play again") == "y"

# Main script
startTime = time.time()
trained_agent = train_agent(episodes, graphStep, Environment())
winrate = test_agent(trained_agent, 100, Environment())
print(f"{round(time.time() - startTime)} seconds for {episodes} episodes with {winrate} winrate")

#let human play:
play_game(trained_agent, Environment())
