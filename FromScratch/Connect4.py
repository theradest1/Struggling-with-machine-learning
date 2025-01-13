import numpy as np
import pygame
import tkinter as tk
import time

from SimpleModel import *
from ModelVisualizer import *
from MathThings import *

class Game:
	def __init__(self, screen):
		#create the board
		self.WIDTH = 700
		self.HEIGHT = 600
		self.peiceRadius = 45
		self.peiceColors = [(200, 50, 50), (50, 200, 50)]
		self.backgroundColor = (0, 0, 0)
		self.screen = screen

		self.restart()

	def restart(self):
		self.turn = np.random.choice([-1, 1])
		self.board = np.zeros((7, 6))

	def draw(self):
		# Clear the screen
		self.screen.fill(self.backgroundColor)

		for x in range(self.board.shape[0]):
			for y in range(self.board.shape[1]):
				#get peice color
				peice = self.board[x, y]
				if peice == 0:
					color = (100, 100, 100)
				else:
					colorIndex = int((peice + 1)/2)
					color = self.peiceColors[colorIndex]

				#draw the peice
				pygame.draw.circle(self.screen, color, (x * 100 + 50, y * 100 + 50), self.peiceRadius)

	def update(self):
		#draw things
		self.draw()

		#show drawings
		pygame.display.flip()

	def place(self, x):
		#get column
		column = self.board[x]

		#get new peice position
		if np.any(column != 0):
			y = np.argmax(column != 0)
		else:
			y = len(column)
		if y == 0:
			return -self.turn #punish for placing in a non-valid place
		y -= 1

		#place peice
		self.board[x, y] = self.turn

		#check if there was a win
		state = self.checkState(x, y)

		#switch turn
		self.turn = -self.turn

		return state

	#checks if the game is over
	#modCol and modRow is the last modified peice position
	def checkState(self, modCol, modRow):
		target = self.board[modCol, modRow]
		
		#horizontal
		if self.stepPeices(modCol, modRow, 1, 0, target) + self.stepPeices(modCol, modRow, -1, 0, target) + 1 >= 4:
			return target
		
		#vertical
		if self.stepPeices(modCol, modRow, 0, 1, target) + self.stepPeices(modCol, modRow, 0, -1, target) + 1 >= 4:
			return target
		
		#negative diagonal
		if self.stepPeices(modCol, modRow, 1, 1, target) + self.stepPeices(modCol, modRow, -1, -1, target) + 1 >= 4:
			return target
		
		#positive diagonal
		if self.stepPeices(modCol, modRow, -1, 1, target) + self.stepPeices(modCol, modRow, 1, -1, target) + 1 >= 4:
			return target
		
		#draw
		if not np.any(self.board == 0):
			return -2
		
		return 0

	def stepPeices(self, x, y, xStep, yStep, target):
		#step
		x += xStep
		y += yStep

		#check bounds
		if x >= self.board.shape[0] or x < 0 or y >= self.board.shape[1] or y < 0:
			return 0
		
		#keep going if it's the same
		if self.board[x, y] == target:
			return self.stepPeices(x, y, xStep, yStep, target) + 1
		
		return 0
	
def playGame(game, model_1, model_2, slow = False):
	game.restart()
	winState = 0
	while winState == 0:
		#get the model's placement
		boardState = game.board.flatten()
		if game.turn == 1:
			outputs = model_1.calculate(boardState)
		elif game.turn == -1:
			outputs = model_2.calculate(boardState)

		outputs = softmax(outputs) #converts to percentages

		#place and update
		position = np.argmax(outputs) #gets the index of the max value
		outputs[position] = -1
		winState = game.place(position)

		if slow:
			game.update()
			time.sleep(.5)

	if winState == -2:
		return
	
	model_1.fitness += winState
	model_2.fitness += -winState

def offsetArray(initialArray, offsetAmount, percentToOffset = 1):
	# Number of elements to modify (10% of the total number of elements)
	num_elements_to_modify = int(initialArray.size * percentToOffset)

	# Get indices of the array's elements
	indices = np.unravel_index(np.random.choice(initialArray.size, num_elements_to_modify, replace=False), initialArray.shape)

	# Set the selected elements to random values
	initialArray[indices] += np.random.uniform(-offsetAmount, offsetAmount, num_elements_to_modify)

def makeChildren(parent, children):
	weights, biases = parent.getValues()
	for childIndex, child in enumerate(children):
		childVariation = variation * childIndex / len(children) #some children have very little variation, and some have a lot
		
		newWeights = weights.copy()
		newBiases = biases.copy()
		
		offsetArray(newWeights, childVariation, offsetPercent)
		offsetArray(newBiases, childVariation, offsetPercent)
		
		child.setValues(newWeights, newBiases)
	
watchNextGame = False
def watchGame():
	global watchNextGame
	watchNextGame = True

dimentions = [42, 128, 64, 7]
variation = .1
populationSize = 100
rounds = populationSize * 2
offsetPercent = .03 #how many weights/biases are offset
childrenPerParent = 11
parents = 6

#create model
population = np.empty(populationSize, dtype=Model)
for i in range(populationSize):
	newModel = Model(dimentions, costFunction, reluFunction, sigmoidFunction)
	population[i] = newModel

#create visualizer
pygame.init()
visualizer = ModelVisualizer(population[0], windowHeight=800, windowWidth=1700, nodeRadius=6, connectionWidth=2, outlines=False)

#controls window
root = tk.Tk()
root.title("Controls and info")
button1 = tk.Button(root, text="Watch Game", command=watchGame)
button1.pack(pady=20)
gamesDone = tk.Label(root, text="Games done: 0/0")
gamesDone.pack(pady=10)		
roundsLabel = tk.Label(root, text="Rounds: 0")
roundsLabel.pack(pady=10)		
timeLabel = tk.Label(root, text="Time: 0")
timeLabel.pack(pady=10)		
gamesPerSecondLabel = tk.Label(root, text="Games Per Second: 0/0")
gamesPerSecondLabel.pack(pady=10)

game = Game(visualizer.screen)
trainingStartTime = time.time()
gamesPerSecond = 0
totalRounds = 0
while True:
	startTime = time.time()

	#check events
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			exit()

	#reset fitness
	for model in population:
		model.fitness = 0

	#play rounds
	guiUpdateIncrement = int(rounds/10)
	for i in range(rounds):
		#get players
		players = np.random.choice(population, 2, replace=False)

		#play game
		playGame(game, players[0], players[1])

		#update GUI
		if i % guiUpdateIncrement == 0:
			gamesDone.config(text=f"Games Done: {i}/{rounds}")
			root.update()
	totalRounds += 1

	#adaptive rounds lets it train fast at the beginning
	rounds = min(rounds + 1, populationSize**2)

	#sort by fitness
	population = np.array(sorted(population, key=lambda model: model.fitness, reverse=True))

	#create children
	for modelIndex in range(parents):
		parent = population[modelIndex]
		startIndex = (modelIndex) * childrenPerParent + parents #start after the parents
		children = population[startIndex:startIndex + childrenPerParent] #8 children per top model in the top 10
		makeChildren(parent, children)
	
	#create new
	for modelIndex in range(parents * (childrenPerParent + 1), populationSize):
		population[modelIndex].randomizeValues()

	visualizer.update(population[0])

	gamesPerSecond = (gamesPerSecond + rounds/(time.time() - startTime))/2
	gamesPerSecondLabel.config(text=f"Games Per Second: {int(gamesPerSecond)}")
	roundsLabel.config(text=f"Rounds: {totalRounds}")
	timeLabel.config(text=f"Time (seconds): {int(time.time() - trainingStartTime)}")

	if watchNextGame:
		watchNextGame = False
		playGame(game, population[0], population[1], True) #top two play