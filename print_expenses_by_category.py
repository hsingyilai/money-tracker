# This script print out all the expenses in the selected category.
import json
from anytree.importer import JsonImporter
from expense_module import ExpenseEntry
from expense_functions import expense_string


try:  # Load the expense list and category tree.
    with open("my_expenses.json", "r") as f:
        expense_list_data = json.load(f)
    expense_list = [ExpenseEntry(**entry) for entry in expense_list_data]
    importer = JsonImporter()
    with open("expense_categories.json", "r") as f:
        expense_type = importer.read(f)
except FileNotFoundError:
    print("Please run initialize_data.py first.")
else:
    # Ask for which category to print.
    current_category = expense_type
    next_layer = True
    while next_layer:
        message = "Which category of expenses do you want to print?: "
        i = 0
        for child_category in current_category.children:
            i += 1
            message += str(i) + ". " + child_category.name + " "

        message += "(Please enter a number): "

        category_index = input(message)

        enter_index = int(category_index) - 1

        choice = current_category.children[enter_index]

        valid_input = False
        while not valid_input:
            decided = input(
                f"Do you want to: 1. Print Expenses in {choice.name}, "
                f"2. Choose from the subcateogries of {choice.name}? (Please enter a number): "
            )

            if decided == "1":
                valid_input = True
                next_layer = False
                category_to_print = choice.name
            elif decided == "2":
                if not choice.children:
                    print("There is no more subcategory.")
                else:
                    current_category = choice
                    valid_input = True
            else:
                print("Not a valid option.")

    # Print the expenses in the selected category.
    print(category_to_print + " expenses:")

    for node in expense_type.descendants:
        if node.name == category_to_print:
            root_of_print = node

    list_of_category_to_print = []
    for node in root_of_print.descendants:
        list_of_category_to_print.append(node.name)

    list_of_category_to_print.append(root_of_print.name)

    i = 0
    for item in expense_list:
        if item.category in list_of_category_to_print:
            i += 1
            print(f"{i}. " + expense_string(item))
