# This script has all the functions defined for this project.
import datetime
from anytree import Node
from expense_module import ExpenseEntry, IncomeEntry


def valid_input(message: str, valid_list: list[str]) -> str:
    """Use a while loop to keep asking input until it matchs an listed element.
    Args:
        message: The message displayed to user when asking input.
        valid_list: List of valid input from the user.

    Returns:
        The input from the user, should match one of the elements in valid_list.
    """
    valid = False
    while not valid:
        input_string = input(message)
        if input_string in valid_list:
            valid = True
        else:
            print("Invalid input.")
    return input_string


def ask_category(category_tree: Node) -> Node | str:
    """Let user select a expense category.
    Args:
        category_tree: The category tree storing the expense categories.

    Returns:
        One of the categories, or string "exit", "go back".
    """
    current_category = category_tree
    while current_category.children:
        message = ""
        i = 0
        for child_category in current_category.children:
            i += 1
            message += str(i) + ". " + child_category.name + " "

        message += "(Please enter a number): "

        valid_list = [str(i) for i in range(1, i + 1)]
        valid_list.append("exit")
        valid_list.append("go back")
        category_index = valid_input(message, valid_list)
        if category_index == "exit":
            return "exit"
        elif category_index == "go back":
            return "go back"
        else:
            enter_index = int(category_index) - 1
            current_category = current_category.children[enter_index]

    return current_category


def what_income(all_income_type: Node) -> str:
    """Let user select an income category.
    Args:
        all_income_type: The category tree storing the income categories.

    Returns:
        The name of the selected income categories.
    """
    current_category = all_income_type

    while current_category.children:
        message = ""
        i = 0
        for child_category in current_category.children:
            i += 1
            message += str(i) + ". " + child_category.name + " "

        message += "(Please enter a number): "

        category_index = input(message)

        enter_index = int(category_index) - 1
        current_category = current_category.children[enter_index]

    category = current_category.name

    return category


def expense_string(entry: ExpenseEntry) -> str:
    """Convert an expense into readable string.

    Some details such as regular, trip are omitted if none.

    Args:
        entry: The entry of expense to convert.

    Returns:
        A single line string listing the data recorded in the expense entry.
    """
    date = datetime.date.fromisoformat(entry.date)
    message = (
        f"{date.strftime("%m/%d/%Y")} {entry.category} ${entry.cost} {entry.notes} "
    )
    if not entry.regular:
        message += "Irregular"
    if entry.trip != "":
        message += f" Trip: {entry.trip}"
    return message


def income_string(entry: IncomeEntry) -> str:
    """Convert an income into readable string.
    Args:
        entry: The entry of income to convert.

    Returns:
        A single line string listing the data recorded in the income entry.
    """
    date = datetime.date.fromisoformat(entry.date)
    message = (
        f"{date.strftime("%m/%d/%Y")} {entry.category} {entry.note} ${entry.amount}"
    )
    return message


def add_note(category: Node) -> None:
    """Let user add notes to a expense cateogry with recursion.
    Args:
        category: The expense category to add notes to.
    """
    choice = valid_input("Do you want to add another note? 1. Yes, 2. No: ", ["1", "2"])
    if choice == "1":
        new_note = input("Please enter the name of the note: ")
        category.notes.append(new_note)
        add_note(category)


def select_trip(expense_list: list[ExpenseEntry]) -> str:
    """Let the user select a trip from existing ones or create a new one
    Args:
        expense_list: The existing expenses
    """
    # Create the list of trips for the user to select.
    trip_list = []
    for entry in expense_list:
        if entry.trip != "":
            trip_list.append(entry.trip)

    trip_list = list(set(trip_list))
    trip_list.sort()

    if trip_list == []:
        trip = input("Please enter the name of the trip: ")
    else:
        # Ask which trip to summarize.
        message = "Please select a trip. "

        i = 0
        for trip in trip_list:
            i += 1
            message += "\n" + str(i) + ". " + trip + ". "
        message += "\n0. Create a new trip. "
        message += "(Please enter a number): "
        trip_selected = valid_input(
            message, [str(i) for i in range(0, len(trip_list) + 1)]
        )

        if trip_selected == "0":
            trip = input("Please enter the name of the trip: ")
        else:
            trip = trip_list[int(trip_selected) - 1]

    return trip


def expense_to_Qstring(expense_list: list[ExpenseEntry]) -> list[str]:
    """Convert the ExpenseEntry item into a list readable by QListWidget, note that we reverse the order
    Args:
        expense_list: The existing expenses
    """
    q_list = []
    for entry in expense_list:
        date = datetime.date.fromisoformat(entry.date)
        q_string = date.strftime("%m/%d/%Y") + "\n$"
        q_string += f"{entry.cost:.2f}" + " " + entry.category
        q_list.insert(0, q_string)

    return q_list


def income_to_Qstring(income_list: list[IncomeEntry]) -> list[str]:
    """Convert the IncomeEntry item into a list readable by QListWidget, note that we reverse the order
    Args:
        income_list: The existing expenses
    """
    q_list = []
    for entry in income_list:
        date = datetime.date.fromisoformat(entry.date)
        q_string = date.strftime("%m/%d/%Y") + "\n$"
        q_string += f"{entry.amount:.2f}" + " " + entry.category
        q_list.insert(0, q_string)

    return q_list
