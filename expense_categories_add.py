# This script is for the user to add new categories to the expense category tree.
from anytree import Node, RenderTree
from expense_functions import valid_input, add_note
from anytree.exporter import JsonExporter
from anytree.importer import JsonImporter


try:  # Load the expense category tree.
    importer = JsonImporter()
    with open("expense_categories.json", "r") as f:
        expense_type = importer.read(f)
except FileNotFoundError:
    print("Please run initialize_data.py first.")
else:
    print(RenderTree(expense_type).by_attr())

    # Start the while loop for adding new categories.
    current_category = expense_type
    category_index = ""
    while category_index != "exit":
        message = ""
        i = 0
        for child_category in current_category.children:
            i += 1
            message += str(i) + ". " + child_category.name + " "

        message += "0. Add New Category (Please enter a number): "

        print('Enter "exit" to end.')
        valid_list = [str(x) for x in range(0, i + 1)]
        valid_list.append("exit")
        category_index = valid_input(message, valid_list)

        if category_index == "0":
            name = input("Please enter the name of the new category: ")
            new_category = Node(name, parent=current_category, notes=["note"])
            print("A note is already created by default.")
            add_note(new_category)
            print(f"Category: {new_category.name} has been added!")
        elif category_index != "exit":
            enter_index = int(category_index) - 1
            current_category = current_category.children[enter_index]

    print(RenderTree(expense_type).by_attr())

    # Save the new expense category tree.
    exporter = JsonExporter(indent=2)
    all_category_json_string = exporter.export(expense_type)

    with open("expense_categories.json", "w") as f:
        f.write(all_category_json_string)
