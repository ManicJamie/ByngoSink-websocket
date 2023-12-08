import generators
import random
import logging, json

logging.basicConfig(level=logging.INFO, format="", handlers=[logging.StreamHandler(), logging.FileHandler(filename="testout.log", mode="w")])

dicttest = {"a": "b", "c": "d"}

choice_key = random.choice(list(dicttest.keys()))
choice = dicttest[choice_key]
print(choice)

gen = generators.get_generator("Hollow Knight", "Item Randomizer")

for i in range(25):
    logging.info([g.name for g in gen.get(i, 25)])