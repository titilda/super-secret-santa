from random import shuffle


def secret_santa_algo(lst: list[tuple]) -> list:
    """Build a list of pairs of Secret Santa assignments."""
    if len(lst) < 2:
        raise ValueError("List must have at least 2 elements")

    people = lst[:]
    shuffled_list = lst[:]
    shuffle(people)
    shuffle(shuffled_list)
    result = []

    i = 0
    while i < len(lst) - 2:
        giver = people.pop()
        receiver = shuffled_list.pop()

        if giver == receiver:
            people.insert(0, giver)
            giver = people.pop()

        result.append((giver, receiver))
        i += 1

    # Handling the last two pairs
    if people[0] != shuffled_list[0] and people[1] != shuffled_list[1]:
        result.append((people[0], shuffled_list[0]))
        result.append((people[1], shuffled_list[1]))
    else:
        result.append((people[0], shuffled_list[1]))
        result.append((people[1], shuffled_list[0]))
    return result
