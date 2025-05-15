import random
from string import ascii_uppercase

#~~~ Global in-memory store for rooms ~~~#
rooms = {}


#~~~ Helper functions ~~~#

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code
