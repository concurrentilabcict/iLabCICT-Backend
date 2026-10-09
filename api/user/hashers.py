from django.contrib.auth.hashers import Argon2PasswordHasher

class TunedArgon2PasswordHasher(Argon2PasswordHasher):
    time_cost = 2
    memory_cost = 65536
    parallelism = 4